"""
Orchestrator Node

Synthesises findings from all three agents into a final verdict using the LLM.
LangSmith tracing is automatic when LANGSMITH_TRACING_V2=true.
"""

import asyncio
import json
import time
from dataclasses import asdict
from typing import Any

from datetime import datetime, timezone
from langsmith import traceable


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]

from agents.nodes.context_analyser import format_key_flags
from agents.state import AgentState
from api.job_store import update_progress
from config.settings import settings
from ml.disaster_classifier import classify_disaster
from ml.sos_engine import get_sos_region

ORCHESTRATOR_PROMPT = """
You are the Vigilens Orchestrator. Four AI agents have analysed a disaster video.
Your job is to synthesise their findings into a final public verdict.

AGENT RESULTS:
{agent_results_json}

CURRENT DATE: {current_date}

INSTRUCTIONS:
1. Compare the findings from all agents.
2. IMPORTANT: The current year is {current_year}. Any dates in {current_year} are CURRENT, not "future" or "impossible".
3. If Deepfake score is low (< 25%) and Context is consistent, verdict MUST be "real" even if Geolocation or Source failed.
4. Only use "unverified" as a last resort if findings are truly contradictory or all major agents failed.
5. If the video looks real but has a high AI score, look at the findings. If the findings say "looks natural/consistent", trust the findings over the raw score.
6. Geolocation mismatches should be flagged as "misleading".
7. Only flag "WAR/CONFLICT CONTENT" if the context analyst confirmed extreme violence (killing, bombing, shooting). Minor arguments or shouting are EXEMPTED.
8. Provide a clear, authoritative summary for the public. If the verdict is "real", be reassuring and state clearly that no evidence of AI manipulation was found.

Produce a verdict. Respond ONLY with valid JSON (no markdown):
{{
  "verdict": "real" | "misleading" | "ai-generated" | "unverified",
  "credibility_score": <0-100>,
  "panic_index": <0-10>,
  "summary": "<2-3 sentence plain English verdict for the public>",
  "source_origin": "<earliest known source URL if found, or null>",
  "original_date": "<date if found YYYY-MM-DD, or null>",
  "claimed_location": "<claimed location or null>",
  "actual_location": "<confirmed location if different, or null>",
  "key_flags": ["<flag1>", "<flag2>"]
}}
"""


@traceable(name="orchestrator")
async def orchestrator_node(state: AgentState) -> dict:
    """Compile final verdict from all agent findings."""
    job_id = state.get("job_id", "unknown")
    update_progress(job_id, 0.85, "orchestrator_starting")

    if state.get("error") == "Video not found":
        print(f"[{_ts()}] [ORCHESTRATOR] [JOB:{job_id[:8]}] Handling Video not found error", flush=True)
        return {
            **state,
            "verdict": "unverified",
            "credibility_score": 0,
            "panic_index": 0,
            "summary": "🚨 **VIDEO NOT FOUND**\n\nThe source URL could not be resolved or the video file is inaccessible. Please verify the link and try again.",
            "disaster_type": "unknown",
            "source_origin": None,
            "original_date": None,
            "claimed_location": state.get("claimed_location"),
            "actual_location": None,
            "key_flags": ["Video source unreachable", "Analysis aborted"],
            "sos_region": None,
        }

    if settings.app_mode == "demo":
        return _demo_verdict(state)

    deepfake = state.get("deepfake_result")
    source = state.get("source_result")
    context = state.get("context_result")
    geo = state.get("geolocation_result")

    agent_results = {
        "deepfake_detector": _finding_to_dict(deepfake),
        "source_hunter": _finding_to_dict(source),
        "context_analyser": _finding_to_dict(context),
        "geolocation_hunter": _finding_to_dict(geo),
    }

    current_date = time.strftime("%Y-%m-%d")
    current_year = current_date[:4]
    prompt = ORCHESTRATOR_PROMPT.format(
        agent_results_json=json.dumps(agent_results, indent=2),
        current_date=current_date,
        current_year=current_year,
    )

    try:
        from langchain_google_vertexai import ChatVertexAI

        llm = ChatVertexAI(
            model_name=settings.gemini_model,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            temperature=0.1,
        )

        from langchain_core.messages import HumanMessage

        response = await asyncio.wait_for(llm.ainvoke([HumanMessage(content=prompt)]), timeout=45.0)
        raw = response.content

        # Strip markdown fences if present — note: str.strip(chars) removes a SET
        # of characters, not a substring, so we must use split() instead.
        raw = raw.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        verdict_data = json.loads(raw)
    except Exception as exc:
        verdict_data = {
            "verdict": "unverified",
            "credibility_score": 0,
            "panic_index": 5,
            "summary": f"Analysis could not be completed: {exc}",
            "source_origin": None,
            "original_date": None,
            "claimed_location": None,
            "actual_location": None,
            "key_flags": ["LLM error — manual review required"],
        }

    # Normalise the verdict — LLMs (especially smaller local models) often
    # capitalise it, add punctuation, or include extra words, e.g.:
    #   "Misleading", "Misleading content", "AI Generated", "Real"
    # Map all variations down to the four valid Literal values.
    VALID_VERDICTS = {"real", "misleading", "ai-generated", "unverified"}
    raw_verdict = str(verdict_data.get("verdict", "unverified")).lower().strip().strip(".")
    if raw_verdict not in VALID_VERDICTS:
        if "mislead" in raw_verdict:
            raw_verdict = "misleading"
        elif any(k in raw_verdict for k in ("ai", "generat", "fake", "deepfake", "synthetic")):
            raw_verdict = "ai-generated"
        elif any(k in raw_verdict for k in ("real", "authentic", "genuine", "legit")):
            raw_verdict = "real"
        else:
            raw_verdict = "unverified"

    # ── SOS Region Engine ─────────────────────────────────────────────────────
    # Only for verified real disasters with significant panic.
    disaster_type = classify_disaster(
        transcript=state.get("context_result").findings[0] if state.get("context_result") else None,
        ocr_text=state.get("context_result").detail if state.get("context_result") else None,
        video_url=state.get("video_url"),
    )

    sos_region = None
    location = (
        verdict_data.get("actual_location")
        or verdict_data.get("claimed_location")
        or state.get("claimed_location")
    )

    if raw_verdict == "real" and int(verdict_data.get("panic_index", 5)) >= 5 and location:
        sos_region = await get_sos_region(
            location=location,
            disaster_type=disaster_type,
            panic_index=int(verdict_data.get("panic_index", 5)),
        )

    result = {
        **state,
        "verdict": raw_verdict,
        "credibility_score": max(0, min(100, int(verdict_data.get("credibility_score", 0)))),
        "panic_index": max(0, min(10, int(verdict_data.get("panic_index", 5)))),
        "summary": verdict_data.get("summary", ""),
        "disaster_type": disaster_type,
        "source_origin": verdict_data.get("source_origin"),
        "original_date": verdict_data.get("original_date"),
        "claimed_location": verdict_data.get("claimed_location") or state.get("claimed_location"),
        "actual_location": verdict_data.get("actual_location"),
        "key_flags": format_key_flags(verdict_data.get("key_flags", [])),
        "sos_region": sos_region,
    }
    update_progress(job_id, 0.90, "orchestrator_done")

    # Send Telegram alert for high-risk verdicts (non-blocking)
    try:
        import asyncio as _asyncio

        from services.telegram_alerts import send_verdict_alert

        _asyncio.create_task(
            send_verdict_alert(
                job_id=state.get("job_id", ""),
                verdict=raw_verdict,
                credibility_score=max(0, min(100, int(verdict_data.get("credibility_score", 0)))),
                panic_index=max(0, min(10, int(verdict_data.get("panic_index", 5)))),
                video_url=state.get("video_url", ""),
                summary=verdict_data.get("summary", ""),
                actual_location=verdict_data.get("actual_location"),
                key_flags=verdict_data.get("key_flags", []),
            )
        )
    except Exception as _tg_exc:
        print(f"[Orchestrator] Telegram alert setup failed: {_tg_exc}", flush=True)

    return result


def _finding_to_dict(finding: Any) -> dict:
    if finding is None:
        return {"status": "not_run"}
    if hasattr(finding, "__dataclass_fields__"):
        return asdict(finding)
    return {}


def _demo_verdict(state: AgentState) -> dict:
    return {
        **state,
        "verdict": "unverified",
        "credibility_score": 50,
        "panic_index": 5,
        "summary": "Demo mode: orchestrator verdict simulated.",
        "source_origin": None,
        "original_date": None,
        "claimed_location": None,
        "actual_location": None,
        "key_flags": ["Demo mode active"],
    }

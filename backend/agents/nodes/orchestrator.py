"""
Orchestrator Node

Synthesises findings from all three agents into a final verdict using the LLM.
LangSmith tracing is automatic when LANGSMITH_TRACING_V2=true.
"""

import json
import time
from dataclasses import asdict
from typing import Any, Dict

from langsmith import traceable

from agents.state import AgentFinding, AgentState
from api.job_store import update_progress
from config.settings import get_llm, settings

ORCHESTRATOR_PROMPT = """
You are the Vigilens Orchestrator. Three AI agents have analysed a disaster video.
Your job is to synthesise their findings into a final public verdict.

AGENT RESULTS:
{agent_results_json}

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
async def orchestrator_node(state: AgentState) -> Dict:
    """Compile final verdict from all agent findings."""
    job_id = state.get("job_id", "unknown")
    update_progress(job_id, 0.85, "orchestrator_starting")

    deepfake = state.get("deepfake_result")
    source = state.get("source_result")
    context = state.get("context_result")

    agent_results = {
        "deepfake_detector": _finding_to_dict(deepfake),
        "source_hunter": _finding_to_dict(source),
        "context_analyser": _finding_to_dict(context),
    }

    prompt = ORCHESTRATOR_PROMPT.format(agent_results_json=json.dumps(agent_results, indent=2))

    try:
        llm = get_llm()
        if hasattr(llm, "invoke"):
            response = llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
        else:
            raw = str(llm(prompt))

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

    # Normalise the verdict
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

    result = {
        **state,
        "verdict": raw_verdict,
        "credibility_score": max(0, min(100, int(verdict_data.get("credibility_score", 0)))),
        "panic_index": max(0, min(10, int(verdict_data.get("panic_index", 5)))),
        "summary": verdict_data.get("summary", ""),
        "source_origin": verdict_data.get("source_origin"),
        "original_date": verdict_data.get("original_date"),
        "claimed_location": verdict_data.get("claimed_location"),
        "actual_location": verdict_data.get("actual_location"),
        "key_flags": verdict_data.get("key_flags", []),
    }
    update_progress(job_id, 0.90, "orchestrator_done")
    return result


def _finding_to_dict(finding: Any) -> Dict:
    if finding is None:
        return {"status": "not_run"}
    if hasattr(finding, "__dataclass_fields__"):
        return asdict(finding)
    return {}

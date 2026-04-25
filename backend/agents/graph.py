import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict

from langgraph.graph import END, StateGraph
from langsmith import traceable

from agents.nodes.context_analyser import context_analyser_node
from agents.nodes.deepfake_detector import deepfake_detector_node
from agents.nodes.notification_node import notification_node
from agents.nodes.orchestrator import orchestrator_node
from agents.nodes.source_hunter import source_hunter_node
from agents.state import AgentState
from agents.tools.ffmpeg_tools import extract_audio, extract_keyframes
from api.job_store import update_progress


def _ts() -> str:
    """Return a compact UTC timestamp string for log lines."""
    return datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]


def _summarise_finding(label: str, finding: Any) -> None:
    """Print a one-line summary of an AgentFinding after it returns."""
    if finding is None:
        print(
            f"[{_ts()}] [GRAPH] {label}: returned None — agent may have crashed silently",
            flush=True,
        )
        return
    status = getattr(finding, "status", "?")
    score = getattr(finding, "score", "?")
    findings_list = getattr(finding, "findings", [])
    count = len(findings_list) if findings_list else 0
    first = findings_list[0] if count > 0 else "(no findings)"
    print(
        f"[{_ts()}] [GRAPH] {label}: status={status!r}  score={score}  "
        f"findings={count}  first_finding={first!r}",
        flush=True,
    )


def create_vigilens_graph() -> Any:
    """
    Vigilens LangGraph pipeline.

    Flow:
      [preprocess] -> [parallel_analysis] -> [orchestrator] -> [notification] -> END

    The three detection agents run concurrently using asyncio.gather inside
    a single 'parallel_analysis' node.
    """
    workflow: StateGraph = StateGraph(AgentState)

    workflow.add_node("preprocess", preprocess_node)
    workflow.add_node("parallel_analysis", parallel_analysis_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("notification", notification_node)

    workflow.set_entry_point("preprocess")
    workflow.add_edge("preprocess", "parallel_analysis")
    workflow.add_edge("parallel_analysis", "orchestrator")
    workflow.add_edge("orchestrator", "notification")
    workflow.add_edge("notification", END)

    return workflow.compile()


@traceable(name="preprocess")
async def preprocess_node(state: AgentState) -> Dict:
    """Extract keyframes and audio from the video."""
    source = state.get("video_path") or state.get("video_url") or ""
    job_id = state.get("job_id", "unknown")
    job_id_short = job_id[:8]

    print(
        f"\n[{_ts()}] [GRAPH] [JOB:{job_id_short}] ── NODE: preprocess ─────────────────────",
        flush=True,
    )
    print(
        f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] source={source[:80]!r}",
        flush=True,
    )

    update_progress(job_id, 0.15, "preprocess_starting")
    node_start = time.monotonic()

    # Extract keyframes
    kf_start = time.monotonic()
    print(f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] Starting keyframe extraction...", flush=True)
    frames = await extract_keyframes(source)
    kf_elapsed = time.monotonic() - kf_start
    print(
        f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] Keyframe extraction done in {kf_elapsed:.1f}s — "
        f"{len(frames)} frame(s) extracted",
        flush=True,
    )
    if frames:
        for i, f in enumerate(frames):
            print(f"[{_ts()}] [GRAPH] [JOB:{job_id_short}]   frame[{i}] = {f}", flush=True)
    else:
        print(
            f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] !! No keyframes extracted — "
            f"downstream agents may produce empty results",
            flush=True,
        )

    # Extract audio
    audio_start = time.monotonic()
    print(f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] Starting audio extraction...", flush=True)
    audio = await extract_audio(source)
    audio_elapsed = time.monotonic() - audio_start
    if audio:
        print(
            f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] Audio extraction done in {audio_elapsed:.1f}s — "
            f"file={audio!r}",
            flush=True,
        )
    else:
        print(
            f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] Audio extraction done in {audio_elapsed:.1f}s — "
            f"no audio (transcription will be skipped)",
            flush=True,
        )

    node_elapsed = time.monotonic() - node_start
    print(
        f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] ── preprocess complete in {node_elapsed:.1f}s ──",
        flush=True,
    )
    update_progress(job_id, 0.30, "preprocess_done")

    return {**state, "keyframes": frames, "audio_path": audio}


@traceable(name="parallel_analysis")
async def parallel_analysis_node(state: AgentState) -> Dict:
    """Run all 3 detection agents concurrently and merge results."""
    job_id = state.get("job_id", "unknown")
    job_id_short = job_id[:8]
    keyframe_count = len(state.get("keyframes") or [])
    audio_path = state.get("audio_path")

    print(
        f"\n[{_ts()}] [GRAPH] [JOB:{job_id_short}] ── NODE: parallel_analysis ──────────────",
        flush=True,
    )
    print(
        f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] Launching 3 agents concurrently — "
        f"keyframes={keyframe_count}  audio={'yes' if audio_path else 'no'}",
        flush=True,
    )

    update_progress(job_id, 0.40, "agents_starting")
    node_start = time.monotonic()

    # Individual per-agent timing wrappers — each updates progress when done
    async def timed_deepfake():
        t0 = time.monotonic()
        print(f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [deepfake_detector] → start", flush=True)
        try:
            result = await deepfake_detector_node(state)
            elapsed = time.monotonic() - t0
            print(
                f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [deepfake_detector] ← done in {elapsed:.1f}s",
                flush=True,
            )
            _summarise_finding("deepfake_detector", result)
            update_progress(job_id, 0.55, "deepfake_done")
            return result
        except Exception as exc:
            elapsed = time.monotonic() - t0
            print(
                f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [deepfake_detector] !! RAISED after {elapsed:.1f}s: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            update_progress(job_id, 0.55, "deepfake_error")
            raise

    async def timed_source():
        t0 = time.monotonic()
        print(f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [source_hunter] → start", flush=True)
        try:
            result = await source_hunter_node(state)
            elapsed = time.monotonic() - t0
            print(
                f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [source_hunter] ← done in {elapsed:.1f}s",
                flush=True,
            )
            _summarise_finding("source_hunter", result)
            update_progress(job_id, 0.65, "source_done")
            return result
        except Exception as exc:
            elapsed = time.monotonic() - t0
            print(
                f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [source_hunter] !! RAISED after {elapsed:.1f}s: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            update_progress(job_id, 0.65, "source_error")
            raise

    async def timed_context():
        t0 = time.monotonic()
        print(f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [context_analyser] → start", flush=True)
        try:
            result = await context_analyser_node(state)
            elapsed = time.monotonic() - t0
            print(
                f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [context_analyser] ← done in {elapsed:.1f}s",
                flush=True,
            )
            _summarise_finding("context_analyser", result)
            update_progress(job_id, 0.80, "context_done")
            return result
        except Exception as exc:
            elapsed = time.monotonic() - t0
            print(
                f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [context_analyser] !! RAISED after {elapsed:.1f}s: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            update_progress(job_id, 0.80, "context_error")
            raise

    try:
        deepfake_result, source_result, context_result = await asyncio.gather(
            timed_deepfake(),
            timed_source(),
            timed_context(),
            return_exceptions=False,
        )
    except Exception as exc:
        node_elapsed = time.monotonic() - node_start
        print(
            f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] !! parallel_analysis FAILED after {node_elapsed:.1f}s: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        raise

    node_elapsed = time.monotonic() - node_start
    print(
        f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] ── parallel_analysis complete in {node_elapsed:.1f}s ──",
        flush=True,
    )
    # Progress is already at 0.80 (set by the slowest agent completing last).
    # The never-goes-backward clamp in update_progress handles race conditions
    # where context finishes before deepfake/source.

    return {
        **state,
        "deepfake_result": deepfake_result,
        "source_result": source_result,
        "context_result": context_result,
    }


# Instantiate once at import
graph = create_vigilens_graph()

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, StateGraph
from langsmith import traceable

from agents.nodes import uploader_profiler
from agents.nodes.context_analyser import context_analyser_node
from agents.nodes.deepfake_detector import deepfake_detector_node
from agents.nodes.geolocation_hunter import geolocation_node
from agents.nodes.notification_node import notification_node
from agents.nodes.orchestrator import orchestrator_node
from agents.nodes.source_hunter import source_hunter_node
from agents.state import AgentState
from agents.tools.ffmpeg_tools import extract_audio, extract_keyframes
from api.job_store import update_progress


def _ts() -> str:
    """Return a compact UTC timestamp string for log lines."""
    return datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]


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
async def preprocess_node(state: AgentState) -> dict:
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
async def parallel_analysis_node(state: AgentState) -> dict:
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
        f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] Launching 5 agents concurrently — "
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

    async def timed_uploader_profiler():
        t0 = time.monotonic()
        print(f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [uploader_profiler] → start", flush=True)
        try:
            result = await uploader_profiler.run(state)
            elapsed = time.monotonic() - t0
            print(
                f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [uploader_profiler] ← done in {elapsed:.1f}s",
                flush=True,
            )
            update_progress(job_id, 0.72, "uploader_done")
            return result
        except Exception as exc:
            elapsed = time.monotonic() - t0
            print(
                f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [uploader_profiler] !! RAISED after {elapsed:.1f}s: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            update_progress(job_id, 0.72, "uploader_error")
            return state  # return state unchanged on failure

    async def timed_geolocation():
        t0 = time.monotonic()
        print(
            f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [geolocation_hunter] \u2192 start", flush=True
        )
        try:
            result = await geolocation_node(state)
            elapsed = time.monotonic() - t0
            print(
                f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [geolocation_hunter] \u2190 done in {elapsed:.1f}s",
                flush=True,
            )
            _summarise_finding("geolocation_hunter", result.get("geolocation_result"))
            update_progress(job_id, 0.75, "geolocation_done")
            return result
        except Exception as exc:
            elapsed = time.monotonic() - t0
            print(
                f"[{_ts()}] [GRAPH] [JOB:{job_id_short}] [geolocation_hunter] !! RAISED after {elapsed:.1f}s: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            update_progress(job_id, 0.75, "geolocation_error")
            raise

    try:
        results = await asyncio.gather(
            timed_deepfake(),
            timed_source(),
            timed_context(),
            timed_geolocation(),
            timed_uploader_profiler(),
            return_exceptions=False,
        )
        deepfake_result = results[0]
        source_result = results[1]
        context_result = results[2]
        geo_result_data = results[3]
        uploader_state = results[4]  # returns full state dict
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

    # Extract reverse search from source hunter detail
    reverse_search_data = None
    if source_result and source_result.detail:
        try:
            import json as _json

            src_detail = _json.loads(source_result.detail)
            reverse_search_data = src_detail.get("reverse_search")
        except Exception:
            pass

    return {
        **state,
        "deepfake_result": deepfake_result,
        "source_result": source_result,
        "context_result": context_result,
        "geolocation_result": geo_result_data.get("geolocation_result"),
        "actual_location": geo_result_data.get("actual_location"),
        "latitude": geo_result_data.get("latitude"),
        "longitude": geo_result_data.get("longitude"),
        "key_flags": list(
            set((state.get("key_flags") or []) + (geo_result_data.get("key_flags") or []))
        ),
        # New fields from uploader profiler
        "platform_metadata": uploader_state.get("platform_metadata")
        if isinstance(uploader_state, dict)
        else None,
        "reddit_metadata": uploader_state.get("reddit_metadata")
        if isinstance(uploader_state, dict)
        else None,
        "uploader_intelligence": uploader_state.get("uploader_intelligence")
        if isinstance(uploader_state, dict)
        else None,
        "reverse_search_result": reverse_search_data,
        "comments_raw": uploader_state.get("comments_raw")
        if isinstance(uploader_state, dict)
        else None,
        "comment_intelligence": uploader_state.get("comment_intelligence")
        if isinstance(uploader_state, dict)
        else None,
    }


# Instantiate once at import
graph = create_vigilens_graph()

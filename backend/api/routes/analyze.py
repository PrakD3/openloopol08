"""Video analysis endpoint."""

import time
import traceback
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException

from agents.graph import graph
from agents.state import AgentState
from api.job_store import (
    create_job,
    find_active_job_for_url,
    jobs,
    mark_completed,
    mark_failed,
    update_progress,
)
from api.models import AgentFindingResponse, AnalyzeRequest, AnalyzeResponse
from config.settings import log_runtime_configuration

router = APIRouter()
_RUNTIME_LOGGED = False


def _ts() -> str:
    """Return a compact UTC timestamp string for log lines."""
    return datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]


# ── POST /analyze ─────────────────────────────────────────────────────────────


@router.post("/analyze", response_model=Dict[str, str])
async def analyze_video(
    request: AnalyzeRequest, background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    Start the Vigilens analysis pipeline in the background.

    Returns a job_id immediately so the client can poll /status/{job_id}.

    Deduplication: if the same video_url is already being processed, the
    existing job_id is returned instead of spawning a second concurrent job.
    This prevents the "retry on timeout → two jobs fighting for resources"
    problem.
    """
    if not request.video_url and not request.video_path:
        raise HTTPException(
            status_code=400,
            detail="Either video_url or video_path is required",
        )

    # ── Deduplication check ───────────────────────────────────────────────────
    existing_job_id = find_active_job_for_url(request.video_url)
    if existing_job_id:
        existing_job = jobs[existing_job_id]
        elapsed = time.monotonic() - existing_job.get("started_at", 0)
        stage = existing_job.get("stage", "processing")
        progress = existing_job.get("progress", 0.0)
        print(
            f"[{_ts()}] [ANALYZE] Dedup: returning existing job {existing_job_id[:8]} "
            f"({elapsed:.0f}s elapsed, {progress:.0%}, stage={stage!r})",
            flush=True,
        )
        return {
            "job_id": existing_job_id,
            "status": "processing",
            "reused": "true",
        }

    # ── Create new job ────────────────────────────────────────────────────────
    job_id = str(uuid.uuid4())
    create_job(job_id, video_url=request.video_url)

    background_tasks.add_task(
        run_analysis_task,
        job_id,
        request.video_url,
        request.video_path,
        request.claimed_location,
    )

    print(
        f"[{_ts()}] [ANALYZE] Job {job_id} created. "
        f"URL={request.video_url or request.video_path!r}",
        flush=True,
    )
    return {"job_id": job_id, "status": "processing"}


# ── Background worker ─────────────────────────────────────────────────────────


async def run_analysis_task(
    job_id: str,
    video_url: str,
    video_path: str,
    claimed_location: str,
) -> None:
    """
    Background worker: runs the full LangGraph pipeline and writes the result
    (or error) back to the shared job store.

    Progress milestones (driven from graph.py node wrappers via update_progress):
        0.05  queued / accepted           (set by create_job)
        0.15  preprocess starting
        0.30  preprocess done
        0.40  agents starting
        0.55  deepfake done
        0.65  source done
        0.75  context done
        0.85  orchestrator done
        0.95  notification done
        1.00  completed
    """
    wall_start = time.monotonic()

    print(
        f"\n[{_ts()}] [JOB:{job_id[:8]}] ── START ──────────────────────────────────",
        flush=True,
    )
    print(
        f"[{_ts()}] [JOB:{job_id[:8]}] video_url={video_url!r}  "
        f"video_path={video_path!r}  claimed_location={claimed_location!r}",
        flush=True,
    )

    try:
        update_progress(job_id, 0.10, "pipeline_starting")

        initial_state: AgentState = {
            "video_url": video_url,
            "video_path": video_path,
            "job_id": job_id,
            "keyframes": [],
            "audio_path": None,
            "metadata": {},
            "transcript": None,
            "ocr_text": None,
            "deepfake_result": None,
            "source_result": None,
            "context_result": None,
            "verdict": None,
            "credibility_score": None,
            "panic_index": None,
            "summary": None,
            "source_origin": None,
            "original_date": None,
            "claimed_location": claimed_location,
            "actual_location": None,
            "key_flags": [],
            "error": None,
            "notification_result": None,
            "is_war_or_conflict": None,
        }

        # ── Execute LangGraph pipeline ────────────────────────────────────────
        # Progress updates during the pipeline are emitted from graph.py via
        # update_progress(). The graph reads job_id from AgentState.
        print(
            f"[{_ts()}] [JOB:{job_id[:8]}] Invoking LangGraph pipeline...",
            flush=True,
        )
        graph_start = time.monotonic()
        final_state = await graph.ainvoke(initial_state)
        graph_elapsed = time.monotonic() - graph_start

        print(
            f"[{_ts()}] [JOB:{job_id[:8]}] LangGraph pipeline finished in {graph_elapsed:.1f}s",
            flush=True,
        )

        update_progress(job_id, 0.97, "building_response")

        # ── Log final state ───────────────────────────────────────────────────
        _log_final_state(job_id, final_state)

        # ── Build agent finding responses ─────────────────────────────────────
        agents = []
        for finding_key in ["deepfake_result", "source_result", "context_result"]:
            finding = final_state.get(finding_key)
            print(
                f"[{_ts()}] [JOB:{job_id[:8]}] {finding_key}: "
                f"{'None — agent did not run' if finding is None else _summarise_finding(finding)}",
                flush=True,
            )
            if finding:
                data = asdict(finding) if hasattr(finding, "__dataclass_fields__") else {}
                agents.append(
                    AgentFindingResponse(
                        agent_id=data.get("agent_id", ""),
                        agent_name=data.get("agent_name", ""),
                        status=data.get("status", "done"),
                        score=data.get("score"),
                        findings=data.get("findings", []),
                        detail=data.get("detail"),
                    )
                )

        # ── Build final AnalyzeResponse ───────────────────────────────────────
        verdict = final_state.get("verdict", "unverified")
        credibility_score = final_state.get("credibility_score", 0)
        panic_index = final_state.get("panic_index", 5)
        summary = final_state.get("summary", "")
        key_flags = final_state.get("key_flags", [])

        print(
            f"[{_ts()}] [JOB:{job_id[:8]}] Building AnalyzeResponse — "
            f"verdict={verdict!r}  credibility={credibility_score}  "
            f"panic={panic_index}  flags={key_flags}",
            flush=True,
        )

        result = AnalyzeResponse(
            job_id=job_id,
            verdict=verdict,
            credibility_score=credibility_score,
            panic_index=panic_index,
            summary=summary,
            source_origin=final_state.get("source_origin"),
            original_date=final_state.get("original_date"),
            claimed_location=final_state.get("claimed_location"),
            actual_location=final_state.get("actual_location"),
            key_flags=key_flags,
            agents=agents,
        )

        # ── Warn if pipeline returned empty keyframes ─────────────────────────
        keyframe_count = len(final_state.get("keyframes") or [])
        if keyframe_count == 0:
            print(
                f"[{_ts()}] [JOB:{job_id[:8]}] !! WARNING: 0 keyframes extracted. "
                f"FFmpeg/yt-dlp likely failed to read the video URL. "
                f"All agent results will be based on no visual data.",
                flush=True,
            )

        mark_completed(job_id, result)

        total_elapsed = time.monotonic() - wall_start
        print(
            f"[{_ts()}] [JOB:{job_id[:8]}] ── COMPLETED in {total_elapsed:.1f}s ──────",
            flush=True,
        )

    except Exception as exc:
        total_elapsed = time.monotonic() - wall_start
        error_msg = f"{type(exc).__name__}: {exc}"

        print(
            f"[{_ts()}] [JOB:{job_id[:8]}] ── FAILED after {total_elapsed:.1f}s ───────",
            flush=True,
        )
        print(f"[{_ts()}] [JOB:{job_id[:8]}] Exception type : {type(exc).__name__}", flush=True)
        print(f"[{_ts()}] [JOB:{job_id[:8]}] Exception value: {exc}", flush=True)
        print(f"[{_ts()}] [JOB:{job_id[:8]}] Full traceback:", flush=True)
        traceback.print_exc()

        mark_failed(job_id, error_msg)


# ── GET /status/{job_id} ──────────────────────────────────────────────────────


@router.get("/status/{job_id}")
async def get_status(job_id: str) -> Dict[str, Any]:
    """
    Poll the status of a background analysis job.

    Returns the full job dict including:
      - status:   "processing" | "completed" | "failed"
      - progress: float 0.0–1.0  (real-time pipeline progress)
      - stage:    str             (human-readable current node name)
      - result:   AnalyzeResponse (only when status == "completed")
      - error:    str             (only when status == "failed")
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    status = job.get("status", "unknown")
    progress = job.get("progress", 0.0)
    stage = job.get("stage", "")

    print(
        f"[{_ts()}] [STATUS] {job_id[:8]} → status={status!r}  "
        f"progress={progress:.0%}  stage={stage!r}",
        flush=True,
    )

    if status == "completed":
        result = job.get("result")
        if result is None:
            print(
                f"[{_ts()}] [STATUS] {job_id[:8]} status=completed but result is None — bug!",
                flush=True,
            )
        else:
            verdict = getattr(result, "verdict", "?")
            credibility = getattr(result, "credibility_score", "?")
            print(
                f"[{_ts()}] [STATUS] {job_id[:8]} result ready — "
                f"verdict={verdict!r}  credibility={credibility}",
                flush=True,
            )

    if status == "failed":
        print(
            f"[{_ts()}] [STATUS] {job_id[:8]} error={job.get('error')!r}",
            flush=True,
        )

    return job


# ── Internal helpers ──────────────────────────────────────────────────────────


def _summarise_finding(finding: Any) -> str:
    """Return a one-line summary of an AgentFinding for log output."""
    try:
        status = getattr(finding, "status", "?")
        score = getattr(finding, "score", "?")
        findings_count = len(getattr(finding, "findings", []))
        return f"status={status!r}  score={score}  findings_count={findings_count}"
    except Exception:
        return repr(finding)


def _log_final_state(job_id: str, final_state: Any) -> None:
    """Print a structured summary of the final LangGraph state for debugging."""
    prefix = f"[{_ts()}] [JOB:{job_id[:8]}]"

    populated_keys = [k for k, v in final_state.items() if v is not None and v != [] and v != {}]
    missing_keys = [k for k, v in final_state.items() if v is None]

    print(f"{prefix} ── final_state dump ──────────────────────────────", flush=True)
    print(f"{prefix}  verdict           = {final_state.get('verdict')!r}", flush=True)
    print(f"{prefix}  credibility_score = {final_state.get('credibility_score')}", flush=True)
    print(f"{prefix}  panic_index       = {final_state.get('panic_index')}", flush=True)

    summary = final_state.get("summary") or ""
    print(f"{prefix}  summary (first 120 chars) = {summary[:120]!r}", flush=True)

    print(f"{prefix}  key_flags         = {final_state.get('key_flags')}", flush=True)
    print(f"{prefix}  source_origin     = {final_state.get('source_origin')!r}", flush=True)
    print(f"{prefix}  original_date     = {final_state.get('original_date')!r}", flush=True)
    print(f"{prefix}  claimed_location  = {final_state.get('claimed_location')!r}", flush=True)
    print(f"{prefix}  actual_location   = {final_state.get('actual_location')!r}", flush=True)

    keyframes = final_state.get("keyframes") or []
    audio_path = final_state.get("audio_path")
    print(f"{prefix}  keyframes         = {len(keyframes)} frames", flush=True)
    print(f"{prefix}  audio_path        = {audio_path!r}", flush=True)

    transcript = final_state.get("transcript")
    if transcript:
        print(
            f"{prefix}  transcript (first 100 chars) = {transcript[:100]!r}",
            flush=True,
        )
    else:
        print(
            f"{prefix}  transcript        = None (no audio or transcription failed)",
            flush=True,
        )

    ocr_text = final_state.get("ocr_text")
    print(f"{prefix}  ocr_text (first 80 chars) = {(ocr_text or '')[:80]!r}", flush=True)

    state_error = final_state.get("error")
    if state_error:
        print(
            f"{prefix}  !! state.error = {state_error!r}  (pipeline set an error flag)",
            flush=True,
        )

    print(f"{prefix}  populated keys    = {populated_keys}", flush=True)
    print(f"{prefix}  None keys         = {missing_keys}", flush=True)
    print(f"{prefix} ──────────────────────────────────────────────────────", flush=True)
    global _RUNTIME_LOGGED
    if not _RUNTIME_LOGGED:
        log_runtime_configuration()
        _RUNTIME_LOGGED = True

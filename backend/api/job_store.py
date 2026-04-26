"""
Shared in-memory job store.

Centralises the `jobs` dict so that both the API route layer (analyze.py)
and the agent graph layer (agents/graph.py) can update progress without a
circular import.

In production, replace with Redis + a proper task queue (Celery / ARQ).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

# ── Primary store ─────────────────────────────────────────────────────────────
# job_id (str) → job dict:
#   {
#       "id":           str,
#       "status":       "processing" | "completed" | "failed",
#       "progress":     float   0.0–1.0
#       "stage":        str     human-readable current node name
#       "result":       AnalyzeResponse | None,
#       "error":        str | None,
#       "video_url":    str | None,   # used for dedup index
#       "started_at":   float,        # time.monotonic()
#   }
jobs: dict[str, Any] = {}

# ── URL → job_id deduplication index ─────────────────────────────────────────
# Lets the /analyze endpoint return the *existing* job_id when the same URL
# is submitted again while a job is still processing, instead of spawning a
# second concurrent job that competes for the same CPU/GPU/API quota.
#
# Entries are cleaned up when a job reaches "completed" or "failed".
_url_to_job: dict[str, str] = {}


# ── Public helpers ────────────────────────────────────────────────────────────


def _ts() -> str:
    """Compact UTC timestamp for log lines."""
    return datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]


def create_job(job_id: str, video_url: str | None = None) -> dict[str, Any]:
    """
    Register a new job and return its initial dict.
    Also records the URL → job_id mapping for deduplication.
    """
    job: dict[str, Any] = {
        "id": job_id,
        "status": "processing",
        "progress": 0.05,  # 5% — job accepted, pipeline not started yet
        "stage": "queued",
        "result": None,
        "error": None,
        "video_url": video_url,
        "started_at": time.monotonic(),
    }
    jobs[job_id] = job

    if video_url:
        _url_to_job[video_url] = job_id

    print(
        f"[{_ts()}] [JOB_STORE] Created job {job_id[:8]} for URL={video_url!r}",
        flush=True,
    )
    return job


def find_active_job_for_url(video_url: str | None) -> str | None:
    """
    Return the job_id of an in-progress job for this URL, or None.

    Only returns jobs whose status is still "processing" — completed/failed
    jobs are ignored so the user can re-analyse the same URL later.
    """
    if not video_url:
        return None

    existing_id = _url_to_job.get(video_url)
    if not existing_id:
        return None

    existing_job = jobs.get(existing_id)
    if not existing_job:
        # Stale index entry — clean up
        _url_to_job.pop(video_url, None)
        return None

    if existing_job.get("status") == "processing":
        elapsed = time.monotonic() - existing_job.get("started_at", 0)
        print(
            f"[{_ts()}] [JOB_STORE] Dedup hit: URL already being processed by "
            f"job {existing_id[:8]} ({elapsed:.0f}s elapsed). Reusing.",
            flush=True,
        )
        return existing_id

    # Job finished — remove from dedup index
    _url_to_job.pop(video_url, None)
    return None


def update_progress(job_id: str, progress: float, stage: str = "") -> None:
    """
    Update a job's progress (0.0–1.0) and human-readable stage label.

    Safe to call from any thread or async context — the dict update is
    atomic in CPython. No-op if job_id doesn't exist (handles race conditions
    where the proxy has already given up and the job dict was never created).

    Suggested milestones:
        0.05  queued       (set by create_job)
        0.15  preprocess_start
        0.30  preprocess_done
        0.40  agents_start
        0.55  deepfake_done
        0.65  source_done
        0.75  context_done
        0.85  orchestrator_done
        0.95  notification_done
        1.00  completed    (set by analyze.py on success)
    """
    job = jobs.get(job_id)
    if not job:
        return

    # Clamp to [0, 1] and never go backwards (handles out-of-order calls)
    clamped = max(job.get("progress", 0.0), min(1.0, round(progress, 2)))
    job["progress"] = clamped
    if stage:
        job["stage"] = stage

    print(
        f"[{_ts()}] [PROGRESS] {job_id[:8]} → {clamped:.0%}  stage={stage!r}",
        flush=True,
    )


def mark_completed(job_id: str, result: Any) -> None:
    """Mark a job as successfully completed and store its result."""
    job = jobs.get(job_id)
    if not job:
        return

    job["status"] = "completed"
    job["progress"] = 1.0
    job["stage"] = "completed"
    job["result"] = result

    # Remove from dedup index so the same URL can be re-analysed
    video_url = job.get("video_url")
    if video_url:
        _url_to_job.pop(video_url, None)

    elapsed = time.monotonic() - job.get("started_at", 0)
    print(
        f"[{_ts()}] [JOB_STORE] Job {job_id[:8]} COMPLETED in {elapsed:.1f}s",
        flush=True,
    )


def mark_failed(job_id: str, error: str) -> None:
    """Mark a job as failed and record the error message."""
    job = jobs.get(job_id)
    if not job:
        return

    job["status"] = "failed"
    job["stage"] = "failed"
    job["error"] = error

    # Remove from dedup index so the same URL can be retried
    video_url = job.get("video_url")
    if video_url:
        _url_to_job.pop(video_url, None)

    elapsed = time.monotonic() - job.get("started_at", 0)
    print(
        f"[{_ts()}] [JOB_STORE] Job {job_id[:8]} FAILED after {elapsed:.1f}s: {error}",
        flush=True,
    )

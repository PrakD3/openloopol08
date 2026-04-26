"""Job status endpoint."""

from fastapi import APIRouter, HTTPException

from api.models import JobStatusResponse

router = APIRouter()

# In-memory job store (replace with Redis in production)
_jobs: dict[str, JobStatusResponse] = {}


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get the status of an analysis job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return _jobs[job_id]

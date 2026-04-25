"""Pydantic request/response models for the Vigilens API."""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class VigilensBaseModel(BaseModel):
    """Base model with camelCase aliases."""
    class Config:
        alias_generator = to_camel
        populate_by_name = True
        from_attributes = True


class AnalyzeRequest(VigilensBaseModel):
    video_url: Optional[str] = None
    video_path: Optional[str] = None
    claimed_location: Optional[str] = None


class AgentFindingResponse(VigilensBaseModel):
    agent_id: str
    agent_name: str
    status: Literal["idle", "running", "done", "error"]
    score: Optional[float] = None
    findings: List[str] = []
    detail: Optional[str] = None
    duration_ms: Optional[int] = None


class AnalyzeResponse(VigilensBaseModel):
    job_id: str
    verdict: Literal["real", "misleading", "ai-generated", "unverified"]
    credibility_score: int = Field(ge=0, le=100)
    panic_index: int = Field(ge=0, le=10)
    summary: str
    source_origin: Optional[str] = None
    original_date: Optional[str] = None
    claimed_location: Optional[str] = None
    actual_location: Optional[str] = None
    key_flags: List[str] = []
    agents: List[AgentFindingResponse] = []


class JobStatusResponse(VigilensBaseModel):
    job_id: str
    status: Literal["queued", "processing", "done", "error"]
    progress: int = Field(ge=0, le=100)
    result: Optional[AnalyzeResponse] = None
    error: Optional[str] = None


class HealthResponse(VigilensBaseModel):
    status: str
    mode: str
    app_mode: str
    version: str = "0.1.0"

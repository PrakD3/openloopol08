"""Pydantic request/response models for the Vigilens API."""

from typing import Literal

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
    video_url: str | None = None
    video_path: str | None = None
    claimed_location: str | None = None


class AgentFindingResponse(VigilensBaseModel):
    agent_id: str
    agent_name: str
    status: Literal["idle", "running", "done", "error"]
    score: float | None = None
    findings: list[str] = []
    detail: str | None = None
    duration_ms: int | None = None


class UploaderIntelligence(VigilensBaseModel):
    trust_score: int
    uploader_summary: str
    account_age_signal: str
    red_flags: list[str] = []
    trust_signals: list[str] = []
    temporal_note: str | None = None
    platform_notes: str | None = None


class ReverseSearchResult(VigilensBaseModel):
    status: str
    prior_appearances_count: int = 0
    temporal_displacement_risk: str = "low"
    best_guess_labels: list[str] = []
    matching_pages: list[dict] = []
    earliest_known_page: dict | None = None


class CommentIntelligence(VigilensBaseModel):
    community_verdict: str
    consensus_summary: str
    original_source_claims: list[str] = []
    location_corrections: list[str] = []
    date_corrections: list[str] = []
    debunk_signals: list[str] = []
    confirm_signals: list[str] = []
    notable_comment: str | None = None


class AnalyzeResponse(VigilensBaseModel):
    job_id: str
    verdict: Literal["real", "misleading", "ai-generated", "unverified"]
    credibility_score: int = Field(ge=0, le=100)
    panic_index: int = Field(ge=0, le=10)
    summary: str
    source_origin: str | None = None
    original_date: str | None = None
    claimed_location: str | None = None
    actual_location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    key_flags: list[str] = []
    disaster_type: str | None = "unknown"
    sos_region: dict | None = None
    agents: list[AgentFindingResponse] = []
    uploader_intelligence: UploaderIntelligence | None = None
    reverse_search: ReverseSearchResult | None = None
    comment_intelligence: CommentIntelligence | None = None
    platform_metadata: dict | None = None
    reddit_metadata: dict | None = None


class JobStatusResponse(VigilensBaseModel):
    job_id: str
    status: Literal["queued", "processing", "done", "error"]
    progress: int = Field(ge=0, le=100)
    result: AnalyzeResponse | None = None
    error: str | None = None


class HealthResponse(VigilensBaseModel):
    status: str
    mode: str
    app_mode: str
    version: str = "0.1.0"

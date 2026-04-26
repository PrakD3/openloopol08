from dataclasses import dataclass, field
from typing import Literal

from typing_extensions import TypedDict


@dataclass
class ModelScore:
    """Per-model deepfake detection result."""

    model_name: str
    authentic_pct: float
    fake_pct: float
    confidence: float


@dataclass
class AgentFinding:
    agent_id: str
    agent_name: str = ""
    status: Literal["idle", "running", "done", "error"] = "idle"
    score: float | None = None
    findings: list[str] = field(default_factory=list)
    detail: str | None = None
    duration_ms: int | None = None
    # Custom ML scoring extras
    constraints_satisfied: int | None = None
    total_constraints: int | None = None
    constraint_details: dict[str, bool] = field(default_factory=dict)
    model_scores: list[ModelScore] = field(default_factory=list)  # deepfake agent only


class AgentState(TypedDict):
    # Input
    video_url: str | None
    video_path: str | None
    job_id: str

    # Intermediate — populated by each agent node
    keyframes: list[str]
    audio_path: str | None
    metadata: dict
    transcript: str | None
    transcript_error: str | None  # reason if transcription failed
    ocr_text: str | None
    ocr_error: str | None  # reason if OCR failed

    # Agent results
    deepfake_result: AgentFinding | None
    source_result: AgentFinding | None
    context_result: AgentFinding | None
    geolocation_result: AgentFinding | None

    # Final
    verdict: str | None
    credibility_score: int | None
    panic_index: int | None
    summary: str | None
    source_origin: str | None
    original_date: str | None
    claimed_location: str | None
    actual_location: str | None
    latitude: float | None
    longitude: float | None
    key_flags: list[str]
    error: str | None

    # New fields
    disaster_type: str | None
    sos_region: dict | None  # populated by orchestrator when verdict='real'

    # Notification result
    notification_result: dict | None  # Output from notification_node

    # War/conflict flag (from context analyser)
    is_war_or_conflict: bool | None

    # Extended metadata fields
    platform_metadata: dict | None  # raw yt-dlp output
    reddit_metadata: dict | None  # reddit API output (None for non-reddit)
    uploader_intelligence: dict | None  # Groq-generated uploader credibility report
    reverse_search_result: dict | None  # Google Vision reverse search result
    comments_raw: list | None  # raw top comments
    comment_intelligence: dict | None  # Groq-extracted comment intelligence

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

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
    score: Optional[float] = None
    findings: List[str] = field(default_factory=list)
    detail: Optional[str] = None
    duration_ms: Optional[int] = None
    # Custom ML scoring extras
    constraints_satisfied: Optional[int] = None
    total_constraints: Optional[int] = None
    constraint_details: Dict[str, bool] = field(default_factory=dict)
    model_scores: List[ModelScore] = field(default_factory=list)  # deepfake agent only


class AgentState(TypedDict):
    # Input
    video_url: Optional[str]
    video_path: Optional[str]
    job_id: str

    # Intermediate — populated by each agent node
    keyframes: List[str]
    audio_path: Optional[str]
    metadata: Dict
    transcript: Optional[str]
    transcript_error: Optional[str]  # reason if transcription failed
    ocr_text: Optional[str]
    ocr_error: Optional[str]  # reason if OCR failed

    # Agent results
    deepfake_result: Optional[AgentFinding]
    source_result: Optional[AgentFinding]
    context_result: Optional[AgentFinding]
    geolocation_result: Optional[AgentFinding]

    # Final
    verdict: Optional[str]
    credibility_score: Optional[int]
    panic_index: Optional[int]
    summary: Optional[str]
    source_origin: Optional[str]
    original_date: Optional[str]
    claimed_location: Optional[str]
    actual_location: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    key_flags: List[str]
    error: Optional[str]

    # New fields
    disaster_type: Optional[str]
    sos_region: Optional[Dict]  # populated by orchestrator when verdict='real'

    # Notification result
    notification_result: Optional[dict]  # Output from notification_node

    # War/conflict flag (from context analyser)
    is_war_or_conflict: Optional[bool]

    # Extended metadata fields
    platform_metadata: Optional[dict]  # raw yt-dlp output
    reddit_metadata: Optional[dict]  # reddit API output (None for non-reddit)
    uploader_intelligence: Optional[dict]  # Groq-generated uploader credibility report
    reverse_search_result: Optional[dict]  # Google Vision reverse search result
    comments_raw: Optional[list]  # raw top comments
    comment_intelligence: Optional[dict]  # Groq-extracted comment intelligence

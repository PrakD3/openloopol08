from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

from typing_extensions import TypedDict


@dataclass
class AgentFinding:
    agent_id: str
    agent_name: str
    status: Literal["idle", "running", "done", "error"] = "idle"
    score: Optional[float] = None
    findings: List[str] = field(default_factory=list)
    detail: Optional[str] = None
    duration_ms: Optional[int] = None


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
    ocr_text: Optional[str]

    # Agent results
    deepfake_result: Optional[AgentFinding]
    source_result: Optional[AgentFinding]
    context_result: Optional[AgentFinding]

    # Final
    verdict: Optional[str]
    credibility_score: Optional[int]
    panic_index: Optional[int]
    summary: Optional[str]
    source_origin: Optional[str]
    original_date: Optional[str]
    claimed_location: Optional[str]
    actual_location: Optional[str]
    key_flags: List[str]
    error: Optional[str]

    # Notification result
    notification_result: Optional[dict]  # Output from notification_node

    # War/conflict flag (from context analyser)
    is_war_or_conflict: Optional[bool]

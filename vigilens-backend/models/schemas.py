from pydantic import BaseModel, Field
from uuid import UUID
from typing import List

class DeepfakeDetail(BaseModel):
    label: str
    confidence: float

class SourceDetail(BaseModel):
    credibility: str

class ContextDetail(BaseModel):
    consistency: str

class TemporalDetail(BaseModel):
    score: float
    note: str

class AnalysisDetails(BaseModel):
    deepfake: DeepfakeDetail
    source: SourceDetail
    context: ContextDetail
    temporal: TemporalDetail

class AnalysisResult(BaseModel):
    verdict: str
    confidence: int
    details: AnalysisDetails

class AnalyzeRequest(BaseModel):
    video_url: str = Field(..., description="The URL of the video to analyze")

class AnalyzeResponse(BaseModel):
    job_id: UUID
    status: str
    analysis: AnalysisResult

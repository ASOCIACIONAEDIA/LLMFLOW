from pydantic import BaseModel, Field 
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.domain.types import SourceType, JobStatus, JobSourceStatus

class SourceConfigRequest(BaseModel):
    source_type: SourceType
    brand_name: str
    countries: List[str] = Field(default_factory=list)
    number_of_reviews: int = Field(default=100, ge=1, le=100)
    options: Dict[str, Any] = Field(default_factory=dict)

class JobCreateRequest(BaseModel):
    sources: List[SourceConfigRequest]

class JobSourceResponse(BaseModel):
    id: int
    source: SourceType
    status: JobSourceStatus
    result: Optional[Dict[str, Any]] = None 
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobResponse(BaseModel):
    id: str
    user_id: int
    organization_id: int
    unit_id: Optional[int] = None
    status: JobStatus
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    sources: List[JobSourceResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

class ReviewData(BaseModel):
    """
    TODO: This is a placeholder for the review data.
    """
    external_id: str
    brand_name: str 
    country: str
    rating: int
    review_text: str
    review_date: datetime
    source: SourceType
    raw: Dict[str, Any] = Field(default_factory=dict)

class JobProgressUpdate(BaseModel):
    """
    Websocket message for job progress updates.
    """
    job_id: str
    event_type: str  # "progress", "source_started", "source_completed", "job_completed", "error"
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid

from app.domain.types import WebSocketEventType, ChannelType

class BaseEvent(BaseModel):
    """Base event model for all WebSocket events"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: WebSocketEventType
    source: str  # job_id, task_id, system, etc.
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class JobEvent(BaseEvent):
    """Job-specific events"""
    job_id: str
    job_type: Optional[str] = None
    
    def get_channels(self) -> list[str]: # TODO: Ask if we should be using List[ChannelType] instead?
        """Get all channels this event should be sent to"""
        channels = [
            f"job:{self.job_id}",
            f"user:{self.user_id}:jobs" if self.user_id else None,
            f"org:{self.organization_id}:jobs" if self.organization_id else None,
        ]
        return [c for c in channels if c is not None]

class TaskEvent(BaseEvent):
    """Task-specific events"""
    job_id: str
    task_name: str
    task_id: Optional[str] = None
    
    def get_channels(self) -> list[str]:
        """Get all channels this event should be sent to"""
        channels = [
            f"job:{self.job_id}",
            f"job:{self.job_id}:progress",
            f"user:{self.user_id}:jobs" if self.user_id else None,
            f"org:{self.organization_id}:jobs" if self.organization_id else None,
        ]
        return [c for c in channels if c is not None]

class ProgressEvent(BaseEvent):
    """Progress update events"""
    job_id: str
    progress_percentage: float
    step: Optional[int] = None
    total_steps: Optional[int] = None
    
    def get_channels(self) -> list[str]:
        """Get all channels this event should be sent to"""
        channels = [
            f"job:{self.job_id}",
            f"job:{self.job_id}:progress",
            f"user:{self.user_id}" if self.user_id else None,
            f"org:{self.organization_id}" if self.organization_id else None,
        ]
        return [c for c in channels if c is not None]

class ErrorEvent(BaseEvent):
    """Error events"""
    job_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: str
    
    def get_channels(self) -> list[str]:
        """Get all channels this event should be sent to"""
        channels = [
            f"job:{self.job_id}:errors" if self.job_id else None,
            f"user:{self.user_id}" if self.user_id else None,
            f"org:{self.organization_id}" if self.organization_id else None,
        ]
        return [c for c in channels if c is not None]

class SystemEvent(BaseEvent):
    """System-wide events"""
    severity: str = "info"  # info, warning, error
    
    def get_channels(self) -> list[str]:
        """Get all channels this event should be sent to"""
        if self.severity == "error":
            return ["system:notifications", "system:errors"]
        return ["system:notifications"]

class UserNotificationEvent(BaseEvent):
    """User-specific notification events"""
    notification_type: str
    title: str
    message: str
    
    def get_channels(self) -> list[str]:
        """Get all channels this event should be sent to"""
        return [f"user:{self.user_id}"] if self.user_id else []
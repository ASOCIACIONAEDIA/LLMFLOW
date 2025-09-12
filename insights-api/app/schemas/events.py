from typing import Dict, Any, Optional, List 
from pydantic import BaseModel, Field
from datetime import datetime

from app.domain.types import WebSocketEventType, ChannelType

class EventSubscriptionRequest(BaseModel):
    """
    HTTP API request to manage event subscriptions
    """
    channels: List[str] # TODO: Ask if we should be using List[ChannelType] instead?
    event_types: Optional[List[WebSocketEventType]] = None
    filters: Optional[Dict[str, Any]] = None

class EventSubscriptionResponse(BaseModel):
    """
    HTTP API response for event subscription management
    """
    user_id: int
    active_subscriptions: List[str]
    total_subscriptions: int
    success: bool
    message: Optional[str] = None

class EventHistoryRequest(BaseModel):
    """
    Request for event history
    """
    job_id: Optional[str] = None
    event_types: Optional[List[WebSocketEventType]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=50, le=200)

class EventHistoryResponse(BaseModel):
    """
    Respose containing event history
    """
    events: List[Dict[str, Any]] # TODO: Ask if we should be using List[Event] instead?
    total_count: int 
    has_more: bool

class ActiveSubscriptionsResponse(BaseModel):
    """
    Response for active subscriptions query
    """
    user_id: int
    subscriptions: Dict[str, List[str]] # channel_type -> [channels]
    total_count: int
    last_activity: Optional[datetime] = None

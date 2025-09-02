from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.domain.types import WSMessageType, ChannelType, WebSocketEventType

class WSMessage(BaseModel):
    """
    Base WebSocket message structure
    """
    type: WSMessageType
    data: Optional[Any] = Field(default=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SubscriptionRequest(BaseModel):
    """
    Client request to subscribe to channels
    """
    channels: List[str] # TODO: Ask if we should be using List[ChannelType] instead?
    filters: Optional[Dict[str, Any]] = None 

class UnsubscriptionRequest(BaseModel):
    """
    Client request to unsubscribe from channels
    """
    channels: List[str]

class SubscriptionResponse(BaseModel):
    """
    Server response to subscription request
    """
    actions: str # "subscribed" or "unsubscribed"
    channels: List[str]
    success: bool
    message: Optional[str] = None
    active_subscriptions: List[str] = Field(default_factory=list)

class EventMessage(BaseModel):
    """
    Event message for WebSocket clients
    """
    event_id: str
    event_type: WebSocketEventType
    channel: str
    source: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConnectionStatus(BaseModel):
    """
    Connection status message
    """
    user_id: int
    connected: bool
    subscriptions: List[str] = Field(default_factory=list)
    connection_time: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class HeartbeatMessage(BaseModel):
    """
    Heartbeat message for connection health
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    active_connections: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
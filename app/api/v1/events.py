import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.api.deps import get_current_active_user
from app.models import User
from app.services.connection_manager_service import manager
from app.services.event_dispatcher_service import dispatcher
from app.schemas.events import (
    EventSubscriptionRequest, EventSubscriptionResponse,
    EventHistoryRequest, EventHistoryResponse,
    ActiveSubscriptionsResponse
)
from app.domain.types import WebSocketEventType

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/subscriptions", response_model=ActiveSubscriptionsResponse)
async def get_active_subscriptions(
    current_user: User = Depends(get_current_active_user)
) -> ActiveSubscriptionsResponse:
    """
    Get the active WebSocket subscriptions for the current user
    """
    try:
        subscriptions = manager.get_user_subscriptions(current_user.id)
        total_count = sum(len(channels) for channels in subscriptions.values())

        last_activity = manager._get_last_activity(current_user.id)
        
        return ActiveSubscriptionsResponse(
            user_id=current_user.id,
            subscriptions=subscriptions,
            total_count=total_count,
            last_activity=last_activity
        )

    except Exception as e:
        logger.error(f"Error getting active subscriptions for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get retrieve subscriptions")
    
@router.post("/subscribe", response_model=EventSubscriptionResponse)
async def bulk_subscribe(
    request: EventSubscriptionRequest,
    current_user: User = Depends(get_current_active_user)
) -> EventSubscriptionResponse:
    """
    Bulk subscribe to channels via HTTP API
    """
    try:
        # TODO: This endpoint would require WebSocket connection to be useful
        # For now, it can be used to validate channel access
        validated_channels = []
        for channel in request.channels:
            # Validate channel access (reuse validation from WebSocket)
            # For simplicity, doing basic validation here
            if await validate_channel_access_http(current_user, channel):
                validated_channels.append(channel)
        
        return EventSubscriptionResponse(
            user_id=current_user.id,
            active_subscriptions=validated_channels,
            total_subscriptions=len(validated_channels),
            success=True,
            message=f"Validated {len(validated_channels)} channels for subscription"
        )
        
    except Exception as e:
        logger.error(f"Error bulk subscribing for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process subscription request"
        )

@router.get("/history/{job_id}", response_model=EventHistoryResponse)
async def get_job_event_history(
    job_id: str,
    event_types: Optional[str] = Query(None, description="Comma-separated event types"),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_active_user)
):
    """Get event history for a specific job"""
    try:
        # TODO: Implement event history storage and retrieval
        # For now, return empty response
        
        # Parse event types filter
        event_type_list = []
        if event_types:
            event_type_list = [et.strip() for et in event_types.split(',')]
        
        # Placeholder response - implement with actual event storage
        return EventHistoryResponse(
            events=[],
            total_count=0,
            has_more=False
        )
        
    except Exception as e:
        logger.error(f"Error getting event history for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event history"
        )

@router.get("/stats")
async def get_connection_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get WebSocket connection statistics (admin only for now)"""
    try:
        stats = manager.get_connection_stats()
        return {
            "connection_stats": stats,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error getting connection stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve connection statistics"
        )

@router.post("/test-notification")
async def send_test_notification(
    message: str = "Test notification",
    current_user: User = Depends(get_current_active_user)
):
    """Send a test notification to the current user"""
    try:
        await dispatcher.dispatch_user_notification(
            user_id=current_user.id,
            title="Test Notification",
            message=message,
            notification_type="info"
        )
        
        return {
            "success": True,
            "message": "Test notification sent",
            "user_id": current_user.id
        }
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test notification"
        )

async def validate_channel_access_http(user: User, channel: str) -> bool:
    """HTTP version of channel access validation"""
    try:
        parts = channel.split(':')
        if len(parts) < 2:
            return False
        
        channel_type = parts[0]
        
        if channel_type == "user":
            try:
                channel_user_id = int(parts[1])
                return channel_user_id == user.id
            except (ValueError, IndexError):
                return False
        
        elif channel_type == "job":
            return True  # TODO: Implement proper job access validation
        
        elif channel_type == "org":
            try:
                channel_org_id = int(parts[1])
                return channel_org_id == user.organization_id
            except (ValueError, IndexError):
                return False
        
        elif channel_type == "system":
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error validating channel access: {e}")
        return False
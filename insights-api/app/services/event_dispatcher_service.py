import logging
import asyncio
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

# from app.services.connection_manager_service import manager This import causes a circular dependency. Import it only when needed!
from app.domain.events import BaseEvent, JobEvent, TaskEvent, ProgressEvent, ErrorEvent, SystemEvent, UserNotificationEvent
from app.domain.types import WebSocketEventType
from app.db.redis import get_redis_client

logger = logging.getLogger(__name__)

class EventDispatcher:
    def __init__(self):
        self.redis_client = None 
        self._initialize_redis_client()
    
    def _initialize_redis_client(self):
        """
        Initialize the Redis client for pub/sub operations
        """
        try: 
            self.redis_client = get_redis_client()
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
    
    def _get_manager(self): # type: ignore
        from app.services.connection_manager_service import manager
        return manager
        
    async def dispatch_event(self, event: BaseEvent) -> None:
        """
        Main dispatch method for events
        """
        try:
            manager = self._get_manager()
            await manager.send_event_to_channels(event)

            if self.redis_client:
                await self._publish_to_redis(event)
            
            logger.debug(f"Event dispatched: {event.event_id} of type {event.event_type}")
        
        except Exception as e:
            logger.error(f"Failed to dispatch event {event.event_id}: {e}")

    async def dispatch_job_event(
        self,
        job_id: str,
        event_type: WebSocketEventType,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        job_type: Optional[str] = None,
        ) -> None:
        """
        Dispatch a job-specific event
        """
        event = JobEvent(
            event_type=event_type,
            source=job_id,
            job_id=job_id,
            job_type=job_type,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "message": message,
                **(data or {})
            }
        )
        
        await self.dispatch_event(event)
    
    async def dispatch_task_event(
        self,
        job_id: str,
        task_name: str,
        event_type: WebSocketEventType,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        task_id: Optional[str] = None
    ):
        """
        Dispatch a task-specific event
        """
        event = TaskEvent(
            event_type=event_type,
            source=task_id or f"{job_id}:{task_name}",
            job_id=job_id,
            task_name=task_name,
            task_id=task_id,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "message": message,
                **(data or {})
            }
        )
        
        await self.dispatch_event(event)
    
    async def dispatch_progress_event(
        self,
        job_id: str,
        progress_percentage: float,
        message: str,
        step: Optional[int] = None,
        total_steps: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None
    ):
        """
        Dispatch a progress update event
        """
        event = ProgressEvent(
            event_type=WebSocketEventType.PROGRESS,
            source=job_id,
            job_id=job_id,
            progress_percentage=progress_percentage,
            step=step,
            total_steps=total_steps,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "message": message,
                "progress_percentage": progress_percentage,
                "step": step,
                "total_steps": total_steps,
                **(data or {})
            }
        )
        
        await self.dispatch_event(event)
    
    async def dispatch_error_event(
        self,
        error_message: str,
        job_id: Optional[str] = None,
        error_code: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None
    ):
        """Dispatch an error event"""
        event = ErrorEvent(
            event_type=WebSocketEventType.ERROR,
            source=job_id or "system",
            job_id=job_id,
            error_code=error_code,
            error_message=error_message,
            user_id=user_id,
            organization_id=organization_id,
            data={
                "error_message": error_message,
                "error_code": error_code,
                **(data or {})
            }
        )
        
        await self.dispatch_event(event)
    
    async def dispatch_system_event(
        self,
        message: str,
        severity: str = "info",
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Dispatch a system-wide event
        """
        event = SystemEvent(
            event_type=WebSocketEventType.SYSTEM_NOTIFICATION,
            source="system",
            severity=severity,
            data={
                "message": message,
                "severity": severity,
                **(data or {})
            }
        )
        
        await self.dispatch_event(event)
    
    async def dispatch_user_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Dispatch a user-specific notification
        """
        event = UserNotificationEvent(
            event_type=WebSocketEventType.USER_NOTIFICATION,
            source="system",
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data={
                "title": title,
                "message": message,
                "notification_type": notification_type,
                **(data or {})
            }
        )
        
        await self.dispatch_event(event)
    
    async def _publish_to_redis(self, event: BaseEvent):
        """Publish event to Redis for cross-instance communication"""
        try:
            if not self.redis_client:
                return
            
            # Publish to Redis channel for each target channel
            channels = event.get_channels()
            event_data = event.model_dump_json()
            
            for channel in channels:
                redis_channel = f"events:{channel}"
                await self.redis_client.publish(redis_channel, event_data)
                
        except Exception as e:
            logger.error(f"Error publishing event to Redis: {e}")

# Global instance
dispatcher = EventDispatcher()
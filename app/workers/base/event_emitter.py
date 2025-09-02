import logging
from typing import Dict, Any, Optional
import asyncio

from app.services.event_dispatcher_service import dispatcher
from app.domain.events import WebSocketEventType
from app.domain.events import JobEvent, TaskEvent, ErrorEvent, ProgressEvent

logger = logging.getLogger(__name__)

class EventEmitter:
    """
    Event emitter for workers with multiplexed WEbSocket support
    """

    def __init__(self, job_id: str, organization_id: Optional[int] = None, user_id: Optional[int] = None):
        self.job_id = job_id
        self.organization_id = organization_id
        self.user_id = user_id
        self.logger = logging.getLogger(f"{__name__}.{job_id}")

    async def emit_job_started(
            self,
            job_type: Optional[str] = None,
            message: str = "Job started",
            data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit a job started event
        """
        try:
            await dispatcher.dispatch_job_event(
                job_id=self.job_id,
                event_type=WebSocketEventType.JOB_STARTED,
                message=message,
                data=data,
                job_type=job_type,
                user_id=self.user_id,
                organization_id=self.organization_id,
                job_type=job_type
            )
            self.logger.info(f"Job started event emitted for job {self.job_id}")
        except Exception as e:
            self.logger.error(f"Failed to emit job started event for job {self.job_id}: {e}")
    
    async def emit_job_progress(
            self,
            progress_percentage: float,
            message: str,
            step: Optional[int] = None,
            total_steps: Optional[int] = None,
            data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit a job progress event
        """
        try:
            await dispatcher.dispatch_progress_event(
                job_id=self.job_id,
                progress_percentage=progress_percentage,
                message=message,
                step=step,
                total_steps=total_steps,
                data=data,
                user_id=self.user_id,
                organization_id=self.organization_id
            )
            self.logger.debug(f"Job progress event emitted for job {self.job_id}: {progress_percentage}%")
        except Exception as e:
            self.logger.error(f"Failed to emit job progress event for job {self.job_id}: {e}")
    
    async def emit_job_completed(
            self,
            result: Optional[Dict[str, Any]] = None,
            message: str = "Job completed",
            data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit a job completed event
        """
        try:
            event_data = {
                "result": result,
                **(data or {})
            }
            await dispatcher.dispatch_job_event(
                job_id=self.job_id,
                event_type=WebSocketEventType.JOB_COMPLETED,
                message=message,
                data=event_data,
                user_id=self.user_id,
                organization_id=self.organization_id
            )
            self.logger.info(f"Job completed event emitted for job {self.job_id}")
        except Exception as e:
            self.logger.error(f"Failed to emit job completed event for job {self.job_id}: {e}")
    
    async def emit_job_error(
        self,
        error_message: str,
        error_code: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        """Emit job error event"""
        try:
            await dispatcher.dispatch_error_event(
                error_message=error_message,
                job_id=self.job_id,
                error_code=error_code,
                data=data,
                user_id=self.user_id,
                organization_id=self.organization_id
            )
            self.logger.error(f"Job error event emitted for job {self.job_id}: {error_message}")
        except Exception as e:
            self.logger.error(f"Failed to emit job error event: {e}")
    
    async def emit_task_started(
        self,
        task_name: str,
        task_config: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ):
        """Emit task started event"""
        try:
            if not message:
                message = f"Task {task_name} started"
            
            await dispatcher.dispatch_task_event(
                job_id=self.job_id,
                task_name=task_name,
                event_type=WebSocketEventType.TASK_STARTED,
                message=message,
                data={"task_config": task_config} if task_config else None,
                user_id=self.user_id,
                organization_id=self.organization_id
            )
            self.logger.info(f"Task started event emitted: {task_name}")
        except Exception as e:
            self.logger.error(f"Failed to emit task started event: {e}")
    
    async def emit_task_progress(
        self,
        task_name: str,
        progress_percentage: float,
        message: str,
        step: Optional[int] = None,
        total_steps: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        """Emit task progress event"""
        try:
            task_data = {
                "task_name": task_name,
                "progress_percentage": progress_percentage,
                "step": step,
                "total_steps": total_steps,
                **(data or {})
            }
            
            await dispatcher.dispatch_task_event(
                job_id=self.job_id,
                task_name=task_name,
                event_type=WebSocketEventType.PROGRESS,
                message=message,
                data=task_data,
                user_id=self.user_id,
                organization_id=self.organization_id
            )
            self.logger.debug(f"Task progress event emitted: {task_name} - {progress_percentage}%")
        except Exception as e:
            self.logger.error(f"Failed to emit task progress event: {e}")
    
    async def emit_task_completed(
        self,
        task_name: str,
        result: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ):
        """Emit task completed event"""
        try:
            if not message:
                message = f"Task {task_name} completed successfully"
            
            task_data = {
                "task_name": task_name,
                "result": result
            }
            
            await dispatcher.dispatch_task_event(
                job_id=self.job_id,
                task_name=task_name,
                event_type=WebSocketEventType.TASK_COMPLETED,
                message=message,
                data=task_data,
                user_id=self.user_id,
                organization_id=self.organization_id
            )
            self.logger.info(f"Task completed event emitted: {task_name}")
        except Exception as e:
            self.logger.error(f"Failed to emit task completed event: {e}")
    
    async def emit_task_error(
        self,
        task_name: str,
        error_message: str,
        error_code: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        """Emit task error event"""
        try:
            task_data = {
                "task_name": task_name,
                "error_message": error_message,
                "error_code": error_code,
                **(data or {})
            }
            
            await dispatcher.dispatch_task_event(
                job_id=self.job_id,
                task_name=task_name,
                event_type=WebSocketEventType.ERROR,
                message=f"Task {task_name} failed: {error_message}",
                data=task_data,
                user_id=self.user_id,
                organization_id=self.organization_id
            )
            self.logger.error(f"Task error event emitted: {task_name} - {error_message}")
        except Exception as e:
            self.logger.error(f"Failed to emit task error event: {e}")
    
    async def emit_source_started(
        self,
        source_type: str,
        source_config: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ):
        """Emit source started event"""
        try:
            if not message:
                message = f"Source {source_type} started"
            
            await dispatcher.dispatch_job_event(
                job_id=self.job_id,
                event_type=WebSocketEventType.SOURCE_STARTED,
                message=message,
                data={
                    "source_type": source_type,
                    "source_config": source_config
                },
                user_id=self.user_id,
                organization_id=self.organization_id
            )
            self.logger.info(f"Source started event emitted: {source_type}")
        except Exception as e:
            self.logger.error(f"Failed to emit source started event: {e}")
    
    async def emit_source_completed(
        self,
        source_type: str,
        result: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ):
        """Emit source completed event"""
        try:
            if not message:
                message = f"Source {source_type} completed"
            
            await dispatcher.dispatch_job_event(
                job_id=self.job_id,
                event_type=WebSocketEventType.SOURCE_COMPLETED,
                message=message,
                data={
                    "source_type": source_type,
                    "result": result
                },
                user_id=self.user_id,
                organization_id=self.organization_id
            )
            self.logger.info(f"Source completed event emitted: {source_type}")
        except Exception as e:
            self.logger.error(f"Failed to emit source completed event: {e}")

class TaskEventEmitter(EventEmitter):
    """Specialized event emitter for individual tasks"""
    
    def __init__(self, job_id: str, task_name: str, organization_id: Optional[int] = None, user_id: Optional[int] = None):
        super().__init__(job_id, organization_id, user_id)
        self.task_name = task_name
    
    async def started(self, config: Optional[Dict[str, Any]] = None):
        """Convenience method for task started"""
        await self.emit_task_started(self.task_name, config)
    
    async def progress(self, percentage: float, message: str, step: Optional[int] = None, total_steps: Optional[int] = None):
        """Convenience method for task progress"""
        await self.emit_task_progress(self.task_name, percentage, message, step, total_steps)
    
    async def completed(self, result: Optional[Dict[str, Any]] = None):
        """Convenience method for task completed"""
        await self.emit_task_completed(self.task_name, result)
    
    async def error(self, error_message: str, error_code: Optional[str] = None):
        """Convenience method for task error"""
        await self.emit_task_error(self.task_name, error_message, error_code)
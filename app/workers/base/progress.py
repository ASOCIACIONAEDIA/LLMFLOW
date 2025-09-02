import json
import logging
from typing import Dict, Any, Optional

from app.services.connection_manager_service import manager 
from app.schemas.jobs import JobProgressUpdate
from app.domain.types import WebSocketEventType
from app.workers.base.event_emitter import EventEmitter
from app.services.event_dispatcher_service import dispatcher

logger = logging.getLogger(__name__)

class ProgressNotifier:
    """
    Utility class for sending progress updates to the client via the websocket connection.
    """

    @staticmethod
    async def notify_job_progress(
        job_id: str,
        event_type: WebSocketEventType,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
    ) -> None:
        """
        Sends a progress update to the client via the websocket connection.

        Args: 
            job_id: Unique identifier for the job
            event_type: Type of event to send (started, progress, completed, error)
            message: Message to send to the client, human-readable message
            data: Optional data to send to the client
        """
        try:
            emitter = EventEmitter(job_id, organization_id, user_id)

            if event_type == WebSocketEventType.TASK_STARTED:
                await emitter.emit_job_started(message=message, data=data)
            elif event_type == WebSocketEventType.PROGRESS:
                progress = data.get("progress_percentage", 0) if data else 0
                await emitter.emit_job_progress(progress, message, data=data)
            elif event_type == WebSocketEventType.TASK_COMPLETED:
                await emitter.emit_job_completed(message=message, data=data)
            elif event_type == WebSocketEventType.JOB_COMPLETED:
                await emitter.emit_job_completed(message=message, data=data)
            elif event_type == WebSocketEventType.ERROR:
                error_msg = data.get("error", message) if data else message
                await emitter.emit_job_error(error_msg, data=data)
            else:
                # For other event types, use generic job event dispatch
                await dispatcher.dispatch_job_event(
                    job_id=job_id,
                    event_type=event_type,
                    message=message,
                    data=data,
                    user_id=user_id,
                    organization_id=organization_id
                )
            
            logger.info(f"Progress update sent for job {job_id}: {message}")
            
        except Exception as e:
            logger.error(f"Failed to send progress update for job {job_id}: {e}")
        
    @staticmethod
    async def notify_task_started(job_id: str, task_name: str, config: Dict[str, Any]) -> None:
        """
        Send notification when a task starts execution.
        """
        await ProgressNotifier.notify_job_progress(
            job_id=job_id,
            event_type=WebSocketEventType.TASK_STARTED,
            message=f"Task {task_name} started",
            data={"task_name": task_name, "config": config},
        )

    @staticmethod
    async def notify_task_progress(
        job_id: str,
        task_name: str,
        progress_percentage: float,
        step: int,
        total_steps: int,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Sends a progress update notification for a task.
        """
        data = {
            "task_name": task_name,
            "progress_percentage": progress_percentage,
            "step": step,
            "total_steps": total_steps,
        }
        if additional_data:
            data.update(additional_data)
        
        await ProgressNotifier.notify_job_progress(
            job_id=job_id,
            event_type=WebSocketEventType.PROGRESS,
            message=f"{task_name} progress: {progress_percentage:.0f}%",
            data=data
        )

    @staticmethod
    async def notify_task_completed(job_id: str, task_name: str, result: Dict[str, Any]) -> None:
        """
        Send notification when a task completes execution.
        """
        await ProgressNotifier.notify_job_progress(
            job_id=job_id,
            event_type=WebSocketEventType.TASK_COMPLETED,
            message=f"Completed {task_name} task",
            data={"task_name": task_name, "result": result},
        )
    
    @staticmethod
    async def notify_task_error(job_id: str, task_name: str, error: str) -> None:
        """
        Send notification when a task encounters an error.
        """
        await ProgressNotifier.notify_job_progress(
            job_id=job_id,
            event_type=WebSocketEventType.ERROR,
            message=f"Error in {task_name} task: {error}",
            data={"task_name": task_name, "error": error},
        )
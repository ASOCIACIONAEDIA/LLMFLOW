import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from app.workers.base.task import BaseTask
from app.workers.base.webhook_wait import register_correlation, wait_for_webhook_result
from app.db.session import AsyncSessionLocal
from app.repositories.job_repo import JobRepository
from app.services.job_service import JobService
from app.domain.types import JobStatus
from app.workers.base.progress import ProgressNotifier

class BaseDiscoveryTask(BaseTask, ABC):
    """
    Base class for all discovery tasks.
    This includes products, places in google, trustpilot URLs and tripadvisor URLs.
    """
    def __init__(self, task_name: str, topic: str, correlation_id: str, timeout_seconds: int):
        super().__init__(task_name)
        self.topic = topic
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(f"{__name__}.{task_name}")

    async def execute(self, ctx, job_id: str, organization_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        await ProgressNotifier.notify_task_started(job_id, self.task_name, config)

        if not await self.validate_config(config):
            await ProgressNotifier.notify_task_error(job_id, self.task_name, "Invalid discovery config")
            async with AsyncSessionLocal() as session:
                await JobService(JobRepository(session)).update_job_status(
                    job_id, JobStatus.FAILED, error="Invalid discovery config"
                )
            return {}

        correlation_id = await self.get_correlation_id(job_id, organization_id, config)
        await register_correlation(self.topic, correlation_id, job_id, ttl_seconds=3600)

        try:
            await ProgressNotifier.notify_task_progress(
                job_id, self.task_name, progress_percentage=20.0, step=1, total_steps=4,
                additional_data={"status": "dispatching", "topic": self.topic}
            )
            await self.dispatch_external(job_id, organization_id, config, correlation_id)
        except Exception as e:
            await ProgressNotifier.notify_task_error(job_id, self.task_name, f"Dispatch failed: {e}")
            async with AsyncSessionLocal() as session:
                await JobService(JobRepository(session)).update_job_status(job_id, JobStatus.FAILED, error=str(e))
            return {}

        await ProgressNotifier.notify_task_progress(
            job_id, self.task_name, progress_percentage=50.0, step=2, total_steps=4,
            additional_data={"status": "waiting_for_webhook", "topic": self.topic, "timeout_sec": self.timeout_seconds}
        )

        payload = await wait_for_webhook_result(self.topic, job_id, timeout_seconds=self.timeout_seconds)
        if not payload:
            await ProgressNotifier.notify_task_error(job_id, self.task_name, "Timed out waiting for webhook")
            async with AsyncSessionLocal() as session:
                await JobService(JobRepository(session)).update_job_status(
                    job_id, JobStatus.FAILED, error="Timed out waiting for webhook"
                )
            return {}

        await ProgressNotifier.notify_task_progress(
            job_id, self.task_name, progress_percentage=75.0, step=3, total_steps=4,
            additional_data={"status": "webhook_received", "topic": self.topic, "payload_size": len(str(payload))}
        )

        result_summary: Dict[str, Any] = {}
        try:
            result_summary = await self.process_payload(payload, job_id, organization_id, config)
        except Exception as e:
            await ProgressNotifier.notify_task_error(job_id, self.task_name, f"Processing error: {e}")
            async with AsyncSessionLocal() as session:
                await JobService(JobRepository(session)).update_job_status(job_id, JobStatus.FAILED, error=str(e))
            return {}

        async with AsyncSessionLocal() as session:
            await JobService(JobRepository(session)).update_job_status(
                job_id, JobStatus.COMPLETED, result=result_summary
            )

        await ProgressNotifier.notify_task_completed(job_id, self.task_name, result_summary)
        return result_summary

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        return True

    async def get_correlation_id(self, job_id: str, organization_id: int, config: Dict[str, Any]) -> str:
        return job_id

    @abstractmethod
    async def dispatch_external(self, job_id: str, organization_id: int, config: Dict[str, Any], correlation_id: str) -> None:
        pass

    @abstractmethod
    async def process_payload(self, payload: Dict[str, Any], job_id: str, organization_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        pass
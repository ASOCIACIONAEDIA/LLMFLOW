import logging
import asyncio
from abc import abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.workers.base.task import BaseTask
from app.workers.base.progress import ProgressNotifier
from app.domain.types import JobStatus, WebSocketEventType, JobTargetType
from app.db.session import AsyncSessionLocal
from app.repositories.job_repo import JobRepository
from app.services.job_service import JobService
from app.repositories.review_repo import ReviewRepository
from app.repositories.archetype_repo import ArchetypeRepository

logger = logging.getLogger(__name__)

class BaseArchetypeTask(BaseTask):
    """
    Base class for all archetype generation tasks.
    Provides common functionality for archetype tasks.
    """

    def __init__(self, task_name: str):
        super().__init__(task_name)

    async def execute(self, ctx, job_id: str, organization_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the archetype generation task.
        """
        await self.on_start(job_id, config)

        try:
            if not await self.validate_config(config):
                raise ValueError("Invalid archetype configuration")
            
            await ProgressNotifier.notify_task_started(job_id, self.task_name, config)
            await self._update_job_status(job_id, JobStatus.RUNNING)

            archetypes = await self._execute_archetype_generation(job_id, organization_id, config)

            result_data = await self._save_archetypes(job_id, organization_id, archetypes, config)

            await self._update_job_status(job_id, JobStatus.COMPLETED, result=result_data)
            await ProgressNotifier.notify_task_completed(job_id, self.task_name, result_data)
            await self.on_complete(job_id, result_data)
            return result_data
        
        except Exception as e:
            error_msg = f"Error in {self.task_name} archetype generation: {str(e)}"
            await self._update_job_status(job_id, JobStatus.FAILED, error=error_msg)
            await ProgressNotifier.notify_task_error(job_id, self.task_name, error_msg)
            await self.on_error(job_id, e)
            raise

    @abstractmethod
    async def _execute_archetype_generation(
        self,
        job_id: str,
        organization_id: int,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute the archetype generation.
        Override this in specific archetype implementations.
        """
        pass
    
    async def _fetch_reviews_for_analysis(
        self,
        organization_id: int,
        target_type: JobTargetType,
        target_id: int,
        config: Dict[str, Any]
    ) -> List[str]:
        """
        Fetch reviews for archetype analysis.
        """
        async with AsyncSessionLocal() as session:
            review_repo = ReviewRepository(session)
            if target_type == JobTargetType.COMPETITOR:
                reviews = await review_repo.get_reviews_for_competitor_analysis(
                    organization_id=organization_id,
                    competitor_id=target_id,
                    limit=config.get("sample_size", 100)
                )
            else:
                reviews = await review_repo.get_reviews_for_archetype_analysis(
                    organization_id=organization_id,
                    limit=config.get("sample_size", 100)
                )
            
            return [review.review_text for review in reviews if review.review_text]
    
    async def _save_archetypes(
        self, 
        job_id: str,
        organization_id: int,
        archetypes: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save the generated archetypes to the database.
        """
        await ProgressNotifier.notify_job_progress(
            job_id=job_id,
            event_type=WebSocketEventType.ARCHETYPE_SAVING,
            message=f"Saving {len(archetypes)} archetypes to the database...",
            data={"archetype_count": len(archetypes)}
        )

        async with AsyncSessionLocal() as session:
            archetype_repo = ArchetypeRepository(session)

            saved_archetypes = []
            target_type = JobTargetType(config.get("target_type"), JobTargetType.ORGANIZATION)
            target_id = config.get("target_id", organization_id)

            for archetype_data in archetypes:
                saved_archetype = await archetype_repo.create_archetype(
                    organization_id=organization_id,
                    job_id=job_id,
                    competitor_id=target_id if target_type == JobTargetType.COMPETITOR else None,
                    archetype_data=archetype_data
                )
                saved_archetypes.append(saved_archetype)
            
            await session.commit()

            return {
            "archetypes_generated": len(saved_archetypes),
            "target_type": target_type.value,
            "target_id": target_id,
            "completed_at": datetime.now(timezone.utc).isoformat()
            }
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate archetype generation configuration.
        """
        required_fields = ["brand_name"]
        return all(field in config for field in required_fields)
    
    async def get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration for archetype generation.
        """
        return {
            "brand_name": "My Business",
            "sample_size": 100,
            "target_type": JobTargetType.ORGANIZATION.value,
        }
    
    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update job status in the database
        """
        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            job_service = JobService(job_repo)

            await job_service.update_job_status(
                job_id=job_id,
                status=status,
                result=result,
                error=error
            )
    
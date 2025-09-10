import logging
import uuid 
from typing import List, Dict, Any
from arq.connections import ArqRedis
from app.repositories.job_repo import JobRepository
from app.domain.types import SourceType, JobStatus, JobSourceStatus, JobType, JobTargetType

logger = logging.getLogger(__name__)

class JobService:
    def __init__(self, job_repo: JobRepository, arq_pool: ArqRedis = None):
        self.job_repo = job_repo
        self.arq_pool = arq_pool
    
    async def create_and_start_job(
        self,
        user_id: int,
        organization_id: int,
        job_type: JobType,
        target_type: JobTargetType = JobTargetType.ORGANIZATION,
        target_id: int = None,
        sources_data: List[Dict[str, Any]] = None,
        config: Dict[str, Any] = None
    ) -> str:
        """
        Creates a job with specified type, adds its sources, and enqueues background tasks.
        """
        job_id = str(uuid.uuid4())
        target_id = target_id or organization_id
        
        logger.info(f"Creating {job_type.value} job {job_id} for user {user_id}, org {organization_id}, target {target_type.value}:{target_id}")

        # Create the main job record with job_type and target info
        await self.job_repo.create_job(
            job_id=job_id, 
            user_id=user_id, 
            organization_id=organization_id,
            job_type=job_type,
            target_type=target_type,
            target_id=target_id
        )

        # Enqueue tasks based on job type
        if self.arq_pool:
            await self._enqueue_tasks_for_job_type(
                job_id, organization_id, job_type, target_type, target_id, sources_data, config
            )
        else:
            logger.warning("No ARQ pool available, tasks not enqueued")
        
        await self.job_repo.update_job_status(job_id=job_id, status=JobStatus.RUNNING)
        logger.info(f"Job {job_id} Status set to RUNNING")

        return job_id
    
    async def _enqueue_tasks_for_job_type(
        self, 
        job_id: str, 
        organization_id: int, 
        job_type: JobType,
        target_type: JobTargetType,
        target_id: int,
        sources_data: List[Dict[str, Any]] = None,
        config: Dict[str, Any] = None
    ) -> None:
        """Enqueue appropriate tasks based on job type."""
        
        if job_type == JobType.REVIEW_SCRAPING:
            # Enqueue scraping tasks
            if not sources_data:
                logger.warning(f"No sources data provided for scraping job {job_id}")
                return
                
            # Add sources for tracking 
            source_types = [SourceType(s["source_type"]) for s in sources_data]
            await self.job_repo.add_sources_to_job(job_id=job_id, sources=source_types)
            
            for source_config in sources_data:
                source_type = SourceType(source_config["source_type"])
                task_name = f"scrape_{source_type.value.lower()}_reviews_task"
                
                logger.info(f"Enqueuing {task_name} for {job_type.value} job")
                await self.arq_pool.enqueue_job(
                    task_name,
                    job_id=job_id,
                    organization_id=organization_id,
                    source_config=source_config
                )
        
        elif job_type == JobType.ARCHETYPE_GENERATION:
            # Enqueue archetype generation task
            task_config = config or {}
            task_config.update({
                "target_type": target_type.value,
                "target_id": target_id,
                "job_type": job_type.value
            })
            
            logger.info(f"Enqueuing archetype generation task for job {job_id}")
            await self.arq_pool.enqueue_job(
                "generate_customer_archetypes_task",
                job_id=job_id,
                organization_id=organization_id,
                config=task_config
            )
        
        elif job_type == JobType.SENTIMENT_ANALYSIS:
            # Future: enqueue sentiment analysis tasks
            logger.info(f"Would enqueue sentiment analysis tasks for job {job_id}")
        
        else:
            logger.warning(f"Unknown job type: {job_type}")

    async def update_source_progress(
        self,
        job_id: str,
        source: SourceType,
        status: JobSourceStatus,
        result: str | None = None,
        error: str | None = None
    ) -> None:
        """Called by a worker task to update the status of a single source scrape."""
        logger.info(f"[{job_id}] Updating source '{source.value}' to status '{status.value}'")
        await self.job_repo.update_job_source_status(job_id=job_id, source=source, status=status, result=result, error=error)

        if await self.job_repo.are_all_sources_finished(job_id=job_id):
            await self.finalize_job(job_id=job_id)
    
    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        result: Dict[str, Any] = None,
        error: str = None
    ) -> None:
        """Update job status directly (for non-source jobs like archetype generation)."""
        logger.info(f"[{job_id}] Updating job status to '{status.value}'")
        await self.job_repo.update_job_status(job_id=job_id, status=status, result=result, error=error)
        
        if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            await self.finalize_job(job_id=job_id)
    
    async def finalize_job(self, job_id: str) -> None:
        """Finalizes a job by setting its status to COMPLETED or FAILED."""
        job = await self.job_repo.get_job_by_id(job_id=job_id)
        if not job:
            logger.error(f"[{job_id}] Cannot finalize job, ID not found")
            return
        
        # For jobs with sources, check source status
        if job.sources:
            has_failures = any(s.status == JobSourceStatus.FAILED for s in job.sources)
            final_status = JobStatus.FAILED if has_failures else JobStatus.COMPLETED
        else:
            # For jobs without sources (like archetype generation), status is already set
            final_status = job.status

        logger.info(f"[{job_id}] Finalizing job with status '{final_status.value}'")
        await self.job_repo.update_job_status(job_id=job_id, status=final_status) 
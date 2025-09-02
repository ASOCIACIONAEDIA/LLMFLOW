from typing import List, Optional
from datetime import datetime, timezone
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models import Job, JobSource, JobEvent
from app.domain.types import JobStatus, JobSourceStatus, SourceType, JobType

logger = logging.getLogger(__name__)

class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_job(self, job_id: str, user_id: int, organization_id: int, job_type: JobType, unit_id: Optional[int] = None) -> Job:
        """
        Creates a new job record
        """
        job = Job(
            id=job_id,
            user_id=user_id,
            organization_id=organization_id,
            job_type=job_type,
            unit_id=unit_id,
            created_at=datetime.now(timezone.utc),
            status=JobStatus.PENDING,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def add_sources_to_job(self, job_id: str, sources: List[SourceType]) -> List[JobSource]:
        """
        Add source record to job in a pending state
        """
        job_sources = [
            JobSource(job_id=job_id, source=source_type, status=JobSourceStatus.PENDING)
            for source_type in sources
        ]
        self.session.add_all(job_sources)
        await self.session.commit()
        return job_sources
    
    async def get_job_by_id(self, job_id: str) -> Optional[Job]:
        """
        Retrieves a job by its ID, including its sources
        """
        stmt = (
            select(Job)
            .options(selectinload(Job.sources))
            .where(Job.id == job_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_jobs_by_user_id(self, user_id: int, limit: int = 50, offset: int = 0) -> List[Job]:
        """
        Retrieves jobs for a specific user with pagination
        """
        stmt = (
            select(Job)
            .options(selectinload(Job.sources))
            .where(Job.user_id == user_id)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_job_status(self, job_id: str, status: JobStatus, error: Optional[str] = None) -> None:
        """
        Updates the status and timestamp of a job
        """
        values = {"status": status}
        if status == JobStatus.RUNNING and not (await self.get_job_by_id(job_id)).started_at:
            values["started_at"] = datetime.now(timezone.utc)
        if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            values["finished_at"] = datetime.now(timezone.utc)
        if error:
            values["error"] = error
        
        stmt = update(Job).where(Job.id == job_id).values(**values)
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def update_job_source_status(
        self, job_id: str, source: SourceType, status: JobSourceStatus, result: Optional[dict] = None, error: Optional[str] = None
    ) -> None:
        """
        Updates the status of a specific source within a job
        """
        stmt = select(JobSource).where(JobSource.job_id == job_id, JobSource.source == source)
        db_source = (await self.session.execute(stmt)).scalar_one_or_none()

        if not db_source:
            logger.error(f"Source {source} not found for job {job_id}")
            return
        
        db_source.status = status
        if status == JobSourceStatus.RUNNING and not db_source.started_at:
            db_source.started_at = datetime.now(timezone.utc)
        if status in [JobSourceStatus.COMPLETED, JobSourceStatus.FAILED, JobSourceStatus.SKIPPED]:
            db_source.finished_at = datetime.now(timezone.utc)
            if result:
                db_source.result = result
            if error:
                db_source.error = error
        
        await self.session.commit()
    
    async def are_all_sources_finished(self, job_id: str) -> bool:
        """Checks if all sources for a job are in a terminal state."""
        stmt = select(JobSource.status).where(JobSource.job_id == job_id)
        result = await self.session.execute(stmt)
        statuses = result.scalars().all()
        
        if not statuses:
            return False
        
        terminal_statuses = [JobSourceStatus.COMPLETED, JobSourceStatus.FAILED, JobSourceStatus.SKIPPED]
        return all(status in terminal_statuses for status in statuses)
    
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any

from app.api.deps import get_current_active_user, get_job_service, get_job_repo, get_arq_pool
from app.models import User
from app.services.job_service import JobService 
from app.repositories.job_repo import JobRepository
from app.schemas.jobs import JobCreateRequest, JobResponse
from app.domain.types import JobType
from arq.connections import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_job(
    sources_data: List[Dict[str, Any]],
    job_type: JobType = JobType.REVIEW_SCRAPING,  # NEW parameter
    current_user: User = Depends(get_current_active_user),
    arq_pool: ArqRedis = Depends(get_arq_pool),
    session: AsyncSession = Depends(get_session)
):
    """Create and start a new job with specified type"""
    job_repo = JobRepository(session)
    job_service = JobService(job_repo, arq_pool)
    
    job_id = await job_service.create_and_start_job(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        sources_data=sources_data,
        job_type=job_type  # NEW: Pass job_type
    )
    
    return {"job_id": job_id, "status": "started", "job_type": job_type.value}

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    job_repo: JobRepository = Depends(get_job_repo)
) -> JobResponse:
    """
    Retrieves the details of a specific job by its ID.
    """
    job = await job_repo.get_job_by_id(job_id=job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found"
        )
    
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this job"
        )
    
    return JobResponse.model_validate(job)

@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    current_user: User = Depends(get_current_active_user),
    job_repo: JobRepository = Depends(get_job_repo),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
) -> List[JobResponse]:
    """
    Retrieves a list of jobs for the current user, with pagination.
    """
    jobs = await job_repo.get_jobs_by_user_id(user_id=current_user.id, limit=limit, offset=offset)
    return [JobResponse.model_validate(job) for job in jobs]
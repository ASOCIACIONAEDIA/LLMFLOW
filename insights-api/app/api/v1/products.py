from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession 
from typing import List, Dict, Any

from app.repositories.product_repo import ProductRepository
from app.services.product_discovery_service import ProductDiscoveryService
from app.api import deps
from app.models import User
from arq.connections import ArqRedis
from app.repositories.job_repo import JobRepository
from app.services.job_service import JobService
from app.schemas.jobs import JobCreateRequest
from app.domain.types import JobType, JobTargetType
from app.schemas.user import Role


router = APIRouter()

# We need a few endpoints to manage products: 
# These endpoints are only available for admins.
# 1.- Find new products. Call the worker to do this task
# 2.- Add new products
# 3.- Get one or more products
# 4.- Update a product
# 5.- Delete a product

@router.post("/find", response_status=status.HTTP_202_ACCEPTED)
async def find_products(
    brand_name: str,
    country: str,
    current_user: User = Depends(deps.get_current_active_user),
    arq_pool: ArqRedis = Depends(deps.get_arq_pool),
    session: AsyncSession = Depends(deps.get_db)
):
    """Find new products for a given brand and country. Works via a worker process."""
    if current_user.role not in [Role.ADMIN, Role.CORPORATE_ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    job_repo = JobRepository(session)
    job_service = JobService(job_repo, arq_pool)
    job_id = await job_service.create_and_start_job(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        job_type=JobType.PRODUCT_DISCOVERY,
        target_type=JobTargetType.ORGANIZATION,
        target_id=current_user.organization_id,
        config={
            "brand_name": brand_name,
            "country": country
        }
    ) 
    return {"job_id": job_id, "status": "started", "job_type": JobType.PRODUCT_DISCOVERY.value}



from typing import List, Dict, Optional,Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.models.archetype import Archetype

class ArchetypeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_archetype(
        self,
        organization_id: int,
        job_id: str,
        archetype_data: Dict[str, Any],
        competitor_id: Optional[int] = None
    ) -> Archetype:
        """
        Create a new archetype
        """
        archetype = Archetype(
            organization_id=organization_id,
            competitor_id=competitor_id,
            job_id=job_id,
            name=archetype_data["name"],
            description=archetype_data["description"],
            pain_points=archetype_data["pain_points"],
            fears_and_concerns=archetype_data["fears_and_concerns"],
            objections=archetype_data["objections"],
            goals_and_objectives=archetype_data["goals_and_objectives"],
            expected_benefits=archetype_data["expected_benefits"],
            values=archetype_data["values"],
            influence_factors=archetype_data["influence_factors"],
            social_behavior=archetype_data["social_behavior"],
            internal_narrative=archetype_data["internal_narrative"],
            avatar_url=archetype_data.get("avatar_url"),
            created_at=datetime.now(timezone.utc)
        ) #LOL kill me please

        self.session.add(archetype)
        await self.session.flush()
        return archetype
    
    async def get_archetypes_by_organization(
        self,
        organization_id: int,
        competitor_id: Optional[int] = None,
        is_active: bool = True
    ) -> List[Archetype]:
        """
        Get archetypes by organization or competitor
        """
        query = select(Archetype).where(
            and_(
                Archetype.organization_id == organization_id,
                Archetype.is_active == is_active
            )
        )

        if competitor_id is not None:
            query = query.where(Archetype.competitor_id == competitor_id)
        else:
            query = query.where(Archetype.competitor_id.is_(None))
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_archetype_by_id(
        self,
        archetype_id: int,
        organization_id: int,
    ) -> Optional[Archetype]:
        """
        Get archetype by id and organization
        """
        query = select(Archetype).where(
            and_(
                Archetype.id == archetype_id,
                Archetype.organization_id == organization_id
            )
        )
        result = await self.session.execute(query)
        archetype = result.scalar_one_or_none()
        return archetype
    
    async def deactivate_archetype(
        self,
        archetype_id: int,
        organization_id: int,
    ) -> bool:
        """
        Deactivate an archetype
        """
        archetype = await self.get_archetype_by_id(archetype_id, organization_id)
        if archetype:
            archetype.is_active = False
            await self.session.commit()
            return True
        return False
    
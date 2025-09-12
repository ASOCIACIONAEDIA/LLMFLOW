from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models import SourceConfig
from app.domain.types import SourceType

class SourceConfigRepositoru:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_user_and_source(self, user_id: int, source: SourceType) -> Optional[SourceConfig]:
        """
        Retrives the source config for a specific user and source type
        """
        stmt = select(SourceConfig).where(SourceConfig.user_id == user_id, SourceConfig.source == source)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_for_user(self, user_id: int) -> List[SourceConfig]:
        """
        Retrieves all source configs for a specific user
        """
        stmt = select(SourceConfig).where(SourceConfig.user_id == user_id, SourceConfig.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(self, user_id: int, config_data: dict) -> SourceConfig:
        """
        Creates a new source sonfiguration or updates an existing one
        """
        source_type = config_data.get("source")
        existing_config = await self.get_by_user_and_source(user_id, source_type)

        if existing_config:
            for key, value in config_data.items():
                setattr(existing_config, key, value)
            config = existing_config
        else:
            config = SourceConfig(user_id=user_id, **config_data)
            self.session.add(config)
        
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def delete(self, user_id: int, source: SourceType) -> bool:
        """
        Deletes a source configuration
        """
        stmt = delete(SourceConfig).where(SourceConfig.user_id == user_id, SourceConfig.source == source)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
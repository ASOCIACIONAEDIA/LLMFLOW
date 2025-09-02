from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import Review

class ReviewRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def bulk_insert_reviews(self, reviews_data: List[dict]) -> int:
        """
        Inserts a list of reviews efficiently, ignoring duplicates based on a unique constraint. 
        A unique constraine on (source, external:id, organization_id) is recommended in the 'reviews' table.
        """
        if not reviews_data:
            return 0

        stmt = pg_insert(Review).values(reviews_data)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["source", "external_id", "organization_id"]
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    # TODO: do get_reviews_for_competitor_analysis and get_reviews_for_archetype_analysis
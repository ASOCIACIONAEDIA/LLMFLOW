from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models import DiscoveredProduct

class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def upsert_product(self, organization_id: int, product_data: dict) -> DiscoveredProduct:
        """
        Creates or updates a discovered product based on a unique identifier (e.g. ASIN, EAN, UPC, GTIN, etc.)
        """
        asin = product_data.get("asin")
        if not asin:
            product = DiscoveredProduct(organization_id=organization_id, **product_data)
            self.session.add(product)
        else:
            stmt = select(DiscoveredProduct).where(DiscoveredProduct.asin == asin, DiscoveredProduct.organization_id == organization_id)
            result = await self.session.execute(stmt)
            product = result.scalar_one_or_none()

            if product:
                for key, value in product_data.items():
                    setattr(product, key, value)
            else:
                product = DiscoveredProduct(organization_id=organization_id, **product_data)
                self.session.add(product)
        
        await self.session.commit()
        await self.session.refresh(product)
        return product
    
    async def get_produts_by_organization(self, organization_id: int) -> List[DiscoveredProduct]:
        """
        Retrieves all discovered products for a specific organization
        """
        stmt = select(DiscoveredProduct).where(DiscoveredProduct.organization_id == organization_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def delete_product(self, product_id: int, organization_id: int) -> bool:
        """
        Deletes a product by its ID and organization ID
        """
        stmt = delete(DiscoveredProduct).where(DiscoveredProduct.id == product_id, DiscoveredProduct.organization_id == organization_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
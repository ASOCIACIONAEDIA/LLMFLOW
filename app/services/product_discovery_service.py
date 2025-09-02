import logging
from typing import List, Dict, Any
from app.repositories.product_repo import ProductRepository
from app.core.exceptions import AppError
from app.models import DiscoveredProduct

logger = logging.getLogger(__name__)

class ProductDiscoveryService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo

    async def trigger_discovery_by_keyword(self, organization_id: int, brand_name: str, country: str) -> List[DiscoveredProduct]:
        """
        Triggers an async product discovery job with, most likely,
        an external provider, like brightdata or Outscraper.
        """
        logger.info(f"Triggering product discovery for brand '{brand_name}' in {country}")
        # TODO: Implement the actual discovery logic here. Maybe create afew clients ina folder or something, 
        # like app.clients.brightdata_client import brightdata_client.
        # This is a placeholder for now. 
        return [
            DiscoveredProduct(
                organization_id=organization_id,
                title=f"{brand_name} {country} products",
                asin="B000000000",
                amazon_url="https://www.amazon.com/s?k=B000000000",
                druni_url="https://www.druni.com/search?q=B000000000",
                identifiers=["B000000000"],
                extra={"country": country}
            ),
            DiscoveredProduct(
                organization_id=organization_id,
                title=f"{brand_name} {country} products",
                asin="B000000000",
                amazon_url="https://www.amazon.com/s?k=B000000000",
                druni_url="https://www.druni.com/search?q=B000000000",
                identifiers=["B000000000"],
                extra={"country": country}
            ),
        ]
    
    async def process_discovery_results(self, organization_id: int, results: List[Dict[str, Any]]):
        """
        Processes the results from a discovery job (e.g., from a webhook)
        and saves the products to the database.
        """
        logger.info(f"Processing {len(results)} discovered products for organization {organization_id}.")
        
        for product_data in results:
            try:
                # The repository handles the create-or-update (upsert) logic
                await self.product_repo.upsert_product(organization_id, product_data)
            except Exception as e:
                logger.error(
                    f"Failed to save discovered product with ASIN {product_data.get('asin')}: {e}",
                    exc_info=True
                )
        logger.info("Finished processing discovery results.")

    async def get_discovered_products(self, organization_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all products discovered for an organization.
        """
        products = await self.product_repo.get_produts_by_organization(organization_id)
        # Here you can map the SQLAlchemy models to Pydantic schemas if needed,
        # but for now, we can return them as is, and the API layer will handle it.
        return products
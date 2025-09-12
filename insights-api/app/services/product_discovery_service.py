import logging
from typing import List, Dict, Any, Optional
import httpx
from app.repositories.product_repo import ProductRepository
from app.core.exceptions import AppError
from app.models import DiscoveredProduct
from app.core.config import settings

logger = logging.getLogger(__name__)

def _map_brightdata_item_to_model(item: Dict[str, Any], job_id: str) -> Dict[str, Any]:
    return {
        "job_id": job_id,
        "title": item.get("title") or "Unknown",
        "asin": item.get("asin"),
        "amazon_url": item.get("url"),
        "druni_url": None,
        "identifiers": [i for i in [item.get("asin")] if i],
        "rating": float(item.get("rating") or 0.0),
        "num_reviews": int(item.get("reviews_count") or 0),
        "extra": {
            "brand": item.get("brand"),
            "image_url": item.get("image_url"),
            "categories": item.get("categories"),
            "raw": item,
        },
    }

class ProductDiscoveryService:
    def __init__(self, product_repo: Optional[ProductRepository] = None):
        self.product_repo = product_repo

    async def trigger_brightdata_discovery(self, brand_name: str, country: str, topic: str) -> str:
        if not (settings.BRIGHTDATA_API_TOKEN and settings.BRIGHTDATA_DATASET_ID):
            raise RuntimeError("Bright Data credentials not configured")

        url = f"{settings.BRIGHTDATA_API_BASE}/datasets/v3/trigger"
        headers = {
            "Authorization": f"Bearer {settings.BRIGHTDATA_API_TOKEN}",
            "Content-Type": "application/json",
        }
        notify_url = f"{settings.PUBLIC_API_BASE_URL.rstrip('/')}{settings.API_PREFIX}/webhooks/{topic}"
        params = {
            "dataset_id": settings.BRIGHTDATA_DATASET_ID,
            "auth_header": f"Bearer {settings.WEBHOOK_SHARED_SECRET}",
            "notify": notify_url,
            "format": "json",
            "uncompressed_webhook": "true",
            "force_deliver": "true",
            "include_errors": "true",
            "type": "discover_new",
            "discover_by": "keyword",
        }
        data = [{"keyword": f"{brand_name} {country}"}]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, params=params, json=data)
            resp.raise_for_status()
            js = resp.json()
            snap = js.get("snapshot_id")
            if not snap:
                raise RuntimeError(f"Bright Data trigger missing snapshot_id: {js}")
            logger.info(f"Bright Data snapshot_id={snap} for {brand_name}/{country}")
            return snap

    async def process_discovery_results(self, organization_id: int, results: List[Dict[str, Any]], job_id: str):
        logger.info(f"Processing {len(results)} discovered products for org {organization_id}.")
        for item in results:
            try:
                mapped = _map_brightdata_item_to_model(item, job_id)
                await self.product_repo.upsert_product(organization_id, mapped)
            except Exception as e:
                logger.error(f"Failed to save discovered product (asin={item.get('asin')}): {e}", exc_info=True)
        logger.info("Finished processing discovery results.")
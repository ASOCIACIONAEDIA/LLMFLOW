import logging
from typing import Dict, Any, List
from app.workers.tasks.discoveries.base_discovery import BaseDiscoveryTask
from app.db.session import AsyncSessionLocal
from app.repositories.product_repo import ProductRepository
from app.services.product_discovery_service import ProductDiscoveryService
from app.workers.base.webhook_wait import register_correlation

logger = logging.getLogger(__name__)

class ProductDiscoveryTask(BaseDiscoveryTask):
    def __init__(self):
        super().__init__(task_name="discovery_product", topic="products", timeout_seconds=3600)
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("brand_name") and config.get("country"))
    
    async def dispatch_external(self, job_id: str, organization_id: int, config: Dict[str, Any], correlation_id: str) -> None:
        # correlation_id not used; we rely on Bright Data snapshot_id
        svc = ProductDiscoveryService()
        snapshot_id = await svc.trigger_brightdata_discovery(
            brand_name=config["brand_name"],
            country=config["country"],
            topic=self.topic,
        )
        # Map snapshot_id -> job_id so webhook can resolve the job
        await register_correlation(self.topic, snapshot_id, job_id, ttl_seconds=3600)
        logger.info(f"[{job_id}] Registered snapshot {snapshot_id} -> job")

    async def process_payload(self, payload: Dict[str, Any], job_id: str, organization_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        items: List[Dict[str, Any]]
        if isinstance(payload, list):
            items = payload
        else:
            items = payload.get("results") or payload.get("items") or []
        persisted = 0
        async with AsyncSessionLocal() as session:
            repo = ProductRepository(session)
            svc = ProductDiscoveryService(repo)
            if items:
                await svc.process_discovery_results(organization_id, items, job_id=job_id)
                persisted = len(items)
        return {
            "topic": self.topic,
            "discovered_count": persisted,
            "brand_name": config.get("brand_name"),
            "country": config.get("country"),
        }

async def discover_products_task(ctx, job_id: str, organization_id: int, config: Dict[str, Any]):
    return await ProductDiscoveryTask().execute(ctx, job_id, organization_id, config)
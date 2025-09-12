import json
import logging
from typing import Dict, Any, Optional

from app.db.redis import get_redis_client

logger = logging.getLogger(__name__)

def _results_list_key(topic: str, job_id: str) -> str:
    return f"webhook:results:{topic}:{job_id}"

def _corr_key(topic: str, correlation_id: str) -> str:
    return f"webhook:corr:{topic}:{correlation_id}"

async def register_correlation(topic: str, correlation_id: str, job_id: str, ttl_seconds: int = 3600) -> None:
    """
    Register a correlation ID for a given topic and job ID.
    """
    redis = get_redis_client()
    await redis.set(_corr_key(topic, correlation_id), job_id, ex=ttl_seconds)

async def resolve_job_id_from_correlation(topic: str, correlation_id: Optional[str]) -> Optional[str]:
    """
    Resolve a job ID from a correlation ID.
    """
    if not correlation_id:
        return None
    redis = get_redis_client()
    return await redis.get(_corr_key(topic, correlation_id))

async def push_webhook_result(topic: str, job_id: str, payload: Dict[str, Any], ttl_seconds: int = 3600) -> None:
    """
    Push webhook result to Redis (rpush pairs with brpop).
    """
    redis = get_redis_client()
    key = _results_list_key(topic, job_id)
    await redis.rpush(key, json.dumps(payload))
    await redis.expire(key, ttl_seconds)

async def wait_for_webhook_result(topic: str, job_id: str, timeout_seconds: int) -> Optional[Dict[str, Any]]:
    """
    Wait for a webhook result to be pushed to Redis.
    """
    redis = get_redis_client()
    key = _results_list_key(topic, job_id)
    logger.info(f"Waiting for webhook result on {key} (timeout: {timeout_seconds} seconds)")
    res = await redis.brpop(key, timeout=timeout_seconds)
    if not res:
        logger.warning(f"No webhook result found on {key} after {timeout_seconds} seconds")
        return None
    _, raw_payload = res
    return json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
import redis.asyncio as redis
from app.core.config import settings

_client: redis.Redis | None = None

def get_redis_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client
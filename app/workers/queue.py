from arq.connections import RedisSettings
from app.core.config import settings

ARQ_REDIS_SETTINGS = RedisSettings(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT
)

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from arq import create_pool

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import add_exception_handlers
from app.db.redis import get_redis_client
from app.db.session import engine

from app.api.v1 import router as api_v1_router


from app.workers.queue import ARQ_REDIS_SETTINGS

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting up {settings.APP_NAME} in {settings.ENV} mode...")



    redis_client = get_redis_client()
    app.state.arq_worker = await create_pool(ARQ_REDIS_SETTINGS)
    try:
        await redis_client.ping()
        logger.info("Successfully connected to Redis.")
    except Exception as e:
        logger.error(f"Could not connect to Redis: {e}", exc_info=True)
    
    yield
    
    logger.info("Shutting down...")
    if app.state.arq_worker:
        await app.state.arq_worker.aclose()
        logger.info("ARQ worker closed.")

    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed.")
    
    await engine.dispose()
    logger.info("Database engine disposed.")



app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


add_exception_handlers(app)


app.include_router(api_v1_router, prefix=settings.API_PREFIX)

@app.get("/", tags=["Health Check"])
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} v{settings.VERSION}"}

if __name__ == "__main__":
    import uvicorn
    # TODO: Use Gunicorn/Uvicorn for production
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
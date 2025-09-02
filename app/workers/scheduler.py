from app.workers.queue import ARQ_REDIS_SETTINGS
from app.workers.registry import task_registry

class WorkerSettings:
    """
    Configuration for the ARQ worker
    """
    functions = task_registry.get_arq_functions()
    redis_settings = ARQ_REDIS_SETTINGS 
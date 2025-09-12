# Legacy compatibility - import the new scheduler
from app.workers.scheduler import WorkerSettings

# Re-export for backward compatibility
__all__ = ["WorkerSettings"]
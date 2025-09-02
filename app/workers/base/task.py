import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional 
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseTask(ABC):
    """
    Abstract base class for all worker tasks.
    Provides commmon functionality and defines the common interface that all tasks must implement
    """

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.logger = logging.getLogger(f"{__name__}.{task_name}")

    @abstractmethod
    async def execute(self, ctx, job_id: str, organization_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the task given thenew configuration.

        Args:
            ctx: ARQ worker context
            job_id: Unique identifier for the job
            organization_id: ID of the organization
            config: Configuration for the task

        Returns:
            Dict[str, Any]: Result of the task execution
        """
        pass

    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate the configuration for the task before the execution.
        Args:
            config: Configuration for the task to be validated.

        Returns:
            bool: True if the configuration is valid, False otherwise
        """
        pass
    
    async def on_start(self, job_id: str, config: Dict[str, Any]) -> None:
        """
        Called when the task starts execution.
        Override this method to perform setup operations.
        """
        self.logger.info(f"Task {self.task_name} started for job {job_id}")
    
    async def on_complete(self, job_id: str, result: Dict[str, Any]) -> None:
        """
        Called when the task completes execution.
        Override this method to perform cleanup operations.
        """
        self.logger.info(f"Task {self.task_name} completed for job {job_id}")
    
    async def on_error(self, job_id: str, error: Exception) -> None:
        """
        Called when the task encounters an error.
        Override this method to perform error handling.
        """
        self.logger.error(f"Task {self.task_name} encountered an error for job {job_id}: {error}")
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get the default configuration for the task.
        """
        return {}
    
    
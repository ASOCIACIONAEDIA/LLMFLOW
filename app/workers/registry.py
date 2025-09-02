import logging 
from typing import Dict, Any, Callable, Type
from app.workers.base.task import BaseTask

logger = logging.getLogger(__name__)

class TaskRegistry:
    def __init__(self):
        self._tasks: Dict[str, Callable] = {}
        self._task_classes: Dict[str, Type[BaseTask]] = {}
    
    def register_task(self, name: str, task_function: Callable, task_class: Type[BaseTask] = None) -> None:
        self._tasks[name] = task_function
        if task_class:
            self._task_classes[name] = task_class
        logger.info(f"Registered task: {name}")
    
    def get_task(self, name: str) -> Callable:
        if name not in self._tasks:
            raise ValueError(f"Task {name} not found")
        return self._tasks[name]
    
    def get_all_tasks(self) -> Dict[str, Callable]:
        return self._tasks.copy()
    
    def get_task_names(self) -> list:
        return list(self._tasks.keys())
    
    def task_exists(self, name: str) -> bool:
        return name in self._tasks
    
    def get_arq_functions(self) -> list:
        return list(self._tasks.values())

# Global task registry instance
task_registry = TaskRegistry()

def register_all_tasks():
    """Register all tasks with the registry."""
    # Register scraping tasks
    from app.workers.tasks.scraping.trustpilot import scrape_trustpilot_reviews_task
    from app.workers.tasks.scraping.google import scrape_google_reviews_task
    from app.workers.tasks.scraping.tripadvisor import scrape_tripadvisor_reviews_task
    from app.workers.tasks.scraping.amazon import scrape_amazon_reviews_task
    
    task_registry.register_task("scrape_trustpilot_reviews_task", scrape_trustpilot_reviews_task)
    task_registry.register_task("scrape_google_reviews_task", scrape_google_reviews_task)
    task_registry.register_task("scrape_tripadvisor_reviews_task", scrape_tripadvisor_reviews_task)
    task_registry.register_task("scrape_amazon_reviews_task", scrape_amazon_reviews_task)
    

    from app.workers.tasks.archetypes.customer_archetype import generate_customer_archetypes_task
    
    task_registry.register_task("generate_customer_archetypes_task", generate_customer_archetypes_task)

# Auto-register tasks when module is imported
register_all_tasks()
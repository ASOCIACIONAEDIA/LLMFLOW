import asyncio 
import uuid 
from abc import abstractmethod 
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.workers.base.task import BaseTask
from app.workers.base.progress import ProgressNotifier
from app.domain.types import JobSourceStatus, SourceType, WebSocketEventType
from app.schemas.jobs import ReviewData

from app.db.session import AsyncSessionLocal
from app.repositories.job_repo import JobRepository
from app.services.job_service import JobService

class BaseScraper(BaseTask):
    """
    Base class for all scraping tasks.
    Provides common functionality for scraping tasks and progress tracking.
    """

    def __init__(self, task_name: str, source_type: SourceType):
        super().__init__(task_name)
        self.source_type = source_type

    async def execute(self, ctx, job_id: str, organization_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the scraping task.
        """
        await self.on_start(job_id, config)
        try:
            if not await self.validate_config(config):
                raise ValueError("Invalid configuration")
            
            await ProgressNotifier.notify_task_started(job_id, self.source_type.value, config)
            await self._update_job_source_status(job_id, JobSourceStatus.RUNNING)

            reviews = await self._execute_scraping(job_id, organization_id, config)

            result_data = await self._process_results(job_id, reviews, config)

            await self._update_job_source_status(job_id, JobSourceStatus.COMPLETED, result=result_data)
            await ProgressNotifier.notify_task_completed(job_id, self.source_type.value, result_data)

            await self.on_complete(job_id, result_data)
            return result_data
        
        except Exception as e:
            error_msg = f"Error in {self.source_type.value} scraping: {str(e)}"
            await self._update_job_source_status(job_id, JobSourceStatus.FAILED, error=error_msg)
            await ProgressNotifier.notify_task_error(job_id, self.source_type.value, error_msg)
            await self.on_error(job_id, e)
            raise 
    
    @abstractmethod
    async def _execute_scraping(self, job_id: str, organization_id: int, config: Dict[str, Any]) -> List[ReviewData] or List[Dict[str, Any]]:
        """
        Execute the actual scrapping logic,
        Override this method in the subclass to implement the actual scraping logic.
        """
        pass 

    async def _process_results(self, job_id: str, reviews: List[ReviewData], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and format the results.
        """

        await ProgressNotifier.notify_task_progress(
            job_id=job_id,
            task_name=self.source_type.value,
            progress_percentage=50.0,
            step=2,
            total_steps=2,  
            additional_data={
                "reviews_count": len(reviews),
            }
        )

        # TODO: Implement the actual processing logic 
        await asyncio.sleep(1)

        await ProgressNotifier.notify_task_progress(
            job_id=job_id,
            task_name=self.source_type.value,
            progress_percentage=100.0,
            step=2,
            total_steps=2,
            additional_data={
                "reviews_count": len(reviews),
            }
        )

        return {
            "reviews_scraped": len(reviews),
            "source": self.source_type.value,
            "brand_name": config.get("brand_name", "Unknown"),
            "countries": config.get("countries", []),
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate the configuration for the scraping task.
        """
        required_fields = ["brand_name", "countries"]
        return all(field in config for field in required_fields)

    async def get_default_config(self) -> Dict[str, Any]:
        """
        Get the default configuration for the scraping task.
        """
        return {
            "brand_name": "Unknown",
            "countries": [],
            "number_of_reviews": 100,
            "options": {},
        }

    async def _update_job_source_status(
            self, 
            job_id: str,
            status: JobSourceStatus,
            result: Optional[Dict[str, Any]] = None,
            error: Optional[str] = None,
    ) -> None:
        """
        Update the job source status in the database.
        """
        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            job_service = JobService(job_repo)
            
            await job_service.update_source_progress(
                job_id=job_id,
                source=self.source_type,
                status=status,
                result=result,
                error=error,
            )

    
    # --- PLACEHOLDERS
    def generate_dummy_reviews(self, brand_name: str, countries: list, num_reviews: int) -> List[ReviewData]:
        """Generate dummy review data for testing"""
        dummy_reviews = []
        
        sample_reviews = [
            "Great product! Really satisfied with the quality.",
            "Good value for money. Would recommend to others.",
            "Excellent customer service and fast delivery.",
            "Not bad, but could be improved in some areas.",
            "Outstanding quality and attention to detail.",
            "Fair product, meets basic expectations.",
            "Wonderful experience, exceeded my expectations!",
            "Decent product, though the price is a bit high.",
            "Amazing quality, will definitely buy again.",
            "Good but not exceptional, average product overall."
        ]
        
        for i in range(min(num_reviews, 50)):  # Limit to 50 for demo
            country = countries[i % len(countries)] if countries else "US"
            review = ReviewData(
                external_id=f"{self.source_type.value}_{uuid.uuid4().hex[:8]}",
                brand_name=brand_name,
                country=country,
                rating=4 + (i % 2),  # Alternate between 4 and 5 stars
                review_text=sample_reviews[i % len(sample_reviews)],
                review_date=datetime.now(timezone.utc),
                source=self.source_type,
                raw={"scraped_at": datetime.now(timezone.utc).isoformat(), "page": i // 10 + 1}
            )
            dummy_reviews.append(review)
        
        return dummy_reviews
    
    async def _simulate_scraping_progress(self, job_id: str, total_duration: int = 20, progress_steps: int = 10) -> None:
        """
        Simulate scraping progress with regular updates.
        """
        step_duration = total_duration / progress_steps
        
        for step in range(progress_steps + 1):
            progress_percentage = (step / progress_steps) * 100
            
            await ProgressNotifier.notify_task_progress(
                job_id=job_id,
                task_name=self.source_type.value,
                progress_percentage=progress_percentage,
                step=step,
                total_steps=progress_steps,
                additional_data={"source": self.source_type.value}
            )
            
            if step < progress_steps:
                await asyncio.sleep(step_duration)
            
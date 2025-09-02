import logging 
from typing import List, Dict, Any
from datetime import datetime, timezone
from app.repositories.review_repo import ReviewRepository
from app.domain.types import SourceType, JobSourceStatus
from app.models import DiscoveredProduct

# TODO: Both this file and product_discovery_service are functional skeletons; they
# do not hit any endpoint, or accurately adapt to the ingest of data from those endpoints,
# however, this is the last of our issues, so, we leave this for the last thing; 
# I just want to know that the system itself works. 

logger = logging.getLogger(__name__)

class ReviewIngestService:
    def __init__(self, review_repo: ReviewRepository):
        self.review_repo = review_repo
    
    def _clean_and_transform(
        self, 
        raw_reviews: List[Dict[str, Any]],
        organization_id: int,
        source: SourceType,
        brand_name: str 
    ) -> List[Dict[str, any]]:
        """
        Private helper to standardize review data from different scrapers
        into the format expected by the Review Model.
        """
        cleaned_data = []
        for raw_review in raw_reviews:
            # Example transformation (adapt for each source) TODO
            # You would have more complex logic here based on scraper output
            review_date = raw_review.get("date")
            if isinstance(review_date, str):
                try:
                    # Handle different date formats from scrapers
                    review_date = datetime.fromisoformat(review_date.replace('Z', '+00:00'))
                except ValueError:
                    review_date = None
            
            # This dictionary must match the columns of the `Review` model
            transformed = {
                "organization_id": organization_id,
                "source": source,
                "external_id": raw_review.get("review_id") or raw_review.get("id"),
                "brand_name": brand_name,
                "country": raw_review.get("country"),
                "rating": raw_review.get("rating"),
                "review_text": raw_review.get("review") or raw_review.get("text"),
                "review_date": review_date,
                "raw": raw_review, # Store the original scraped data
                "created_at": datetime.now(timezone.utc)
            }
            cleaned_data.append(transformed)
        return cleaned_data
    
    async def ingest_reviews(
        self, 
        organization_id: int,
        source: SourceType,
        brand_name: str,
        raw_data: List[Dict[str, Any]]
    ) -> int:
        """
        Processes and ingests a batch of scraped reviews.
        """
        if not raw_data:
            logger.warning(f"No reviews data provided for organization {organization_id} from source {source}")
            return 0
        
        logger.info(f"Ingesting {len(raw_data)} reviews from {source.value} for brand {brand_name}")

        # 1.- Clean and transform the data to matcch our DB schema 
        reviews_to_insert = self._clean_and_transform(raw_reviews=raw_data, organization_id=organization_id, source=source, brand_name=brand_name)

        # 2.- Bulk insert into the databse
        inserted_count = await self.review_repo.bulk_insert_reviews(reviews_data=reviews_to_insert)

        logger.info(f"Successfully ingested {inserted_count} reviews from {source.value} for brand {brand_name}")
        return inserted_count
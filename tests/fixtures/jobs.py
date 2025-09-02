"""Job test data fixtures."""
from app.domain.types import JobType, JobStatus

# Sample job data
SAMPLE_JOBS = [
    {
        "job_type": JobType.REVIEW_SCRAPING,
        "status": JobStatus.PENDING,
        "sources_data": [
            {"name": "Amazon", "url": "https://amazon.com/product/123"},
            {"name": "TripAdvisor", "url": "https://tripadvisor.com/hotel/456"}
        ]
    },
    {
        "job_type": JobType.PRODUCT_DISCOVERY,
        "status": JobStatus.RUNNING,
        "sources_data": [
            {"name": "Google", "url": "https://google.com/search?q=restaurants"}
        ]
    },
    {
        "job_type": JobType.ARCHETYPE_ANALYSIS,
        "status": JobStatus.COMPLETED,
        "sources_data": []
    }
]

# Job creation data for API tests
JOB_CREATE_DATA = {
    "sources_data": [
        {"name": "Test Source", "url": "https://example.com/test"}
    ],
    "job_type": "REVIEW_SCRAPING"
}

# Invalid job data for testing validation
INVALID_JOB_DATA = [
    {
        "sources_data": [],  # Empty sources
        "job_type": "INVALID_TYPE"
    },
    {
        "sources_data": [{"name": "Test"}],  # Missing URL
        "job_type": "REVIEW_SCRAPING"
    }
]
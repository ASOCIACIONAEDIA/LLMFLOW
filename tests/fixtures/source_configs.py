"""Source configuration test data fixtures."""

# Sample source configuration data
SAMPLE_SOURCE_CONFIGS = [
    {
        "name": "Amazon Scraper",
        "source_type": "AMAZON",
        "base_url": "https://amazon.com",
        "is_active": True,
        "config_data": {
            "selectors": {
                "product_title": ".product-title",
                "price": ".price",
                "reviews": ".review-list .review"
            },
            "rate_limit": {
                "requests_per_minute": 60
            }
        }
    },
    {
        "name": "TripAdvisor Scraper",
        "source_type": "TRIPADVISOR",
        "base_url": "https://tripadvisor.com",
        "is_active": True,
        "config_data": {
            "selectors": {
                "hotel_name": ".hotel-name",
                "rating": ".rating",
                "reviews": ".review-container .review"
            },
            "rate_limit": {
                "requests_per_minute": 30
            }
        }
    }
]

# Source config creation data
SOURCE_CONFIG_CREATE_DATA = {
    "name": "Test Scraper",
    "source_type": "CUSTOM",
    "base_url": "https://example.com",
    "config_data": {
        "selectors": {
            "title": ".title",
            "content": ".content"
        }
    }
}
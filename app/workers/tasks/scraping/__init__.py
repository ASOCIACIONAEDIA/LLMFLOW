from .trustpilot import scrape_trustpilot_reviews_task
from .google import scrape_google_reviews_task
from .tripadvisor import scrape_tripadvisor_reviews_task
from .amazon import scrape_amazon_reviews_task

__all__ = [
    "scrape_trustpilot_reviews_task",
    "scrape_google_reviews_task",
    "scrape_tripadvisor_reviews_task",
    "scrape_amazon_reviews_task",
]

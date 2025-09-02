"""Review test data fixtures."""

# Sample review data
SAMPLE_REVIEWS = [
    {
        "rating": 5.0,
        "content": "Excellent product! Highly recommended.",
        "reviewer_name": "John Doe",
        "source": "Amazon",
        "verified_purchase": True
    },
    {
        "rating": 4.0,
        "content": "Good product, but could be better.",
        "reviewer_name": "Jane Smith",
        "source": "TripAdvisor",
        "verified_purchase": False
    },
    {
        "rating": 2.0,
        "content": "Not satisfied with the quality.",
        "reviewer_name": "Bob Johnson",
        "source": "Trustpilot",
        "verified_purchase": True
    }
]

# Review creation data
REVIEW_CREATE_DATA = {
    "rating": 4.5,
    "content": "Great product, would buy again!",
    "reviewer_name": "Test Reviewer",
    "source": "Test Source"
}

# Invalid review data
INVALID_REVIEW_DATA = [
    {
        "rating": 6.0,  # Rating too high
        "content": "Invalid rating"
    },
    {
        "rating": -1.0,  # Rating too low
        "content": "Negative rating"
    },
    {
        "rating": 3.0,
        "content": ""  # Empty content
    }
]
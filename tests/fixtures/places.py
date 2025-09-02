"""Places test data fixtures."""
from datetime import datetime

# Sample discovered places data
SAMPLE_PLACES = [
    {
        "organization_id": 1,
        "job_id": "test-job-1",
        "name": "Grand Hotel Central",
        "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
        "full_address": "123 Main Street, Barcelona, Spain",
        "postal_code": "08002",
        "country": "Spain",
        "typical_time_spent": 120,  # minutes
        "rating": 4.5,
        "num_reviews": 1250,
        "extra": {
            "phone": "+34 93 295 79 00",
            "website": "https://grandhotelcentral.com",
            "category": "Hotel",
            "price_level": 4,
            "opening_hours": {
                "monday": "00:00-23:59",
                "tuesday": "00:00-23:59",
                "wednesday": "00:00-23:59",
                "thursday": "00:00-23:59",
                "friday": "00:00-23:59",
                "saturday": "00:00-23:59",
                "sunday": "00:00-23:59"
            }
        }
    },
    {
        "organization_id": 1,
        "job_id": "test-job-1",
        "name": "Restaurant Can Culleretes",
        "google_place_id": "ChIJd8BlQ2VEEmsRAFH0XY7_z-E",
        "full_address": "Carrer d'en Quintana, 5, 08002 Barcelona, Spain",
        "postal_code": "08002",
        "country": "Spain",
        "typical_time_spent": 90,  # minutes
        "rating": 4.2,
        "num_reviews": 3420,
        "extra": {
            "phone": "+34 93 317 30 22",
            "website": "https://culleretes.com",
            "category": "Restaurant",
            "cuisine": "Traditional Catalan",
            "price_level": 2,
            "opening_hours": {
                "monday": "13:00-16:00,20:00-23:00",
                "tuesday": "13:00-16:00,20:00-23:00",
                "wednesday": "Closed",
                "thursday": "13:00-16:00,20:00-23:00",
                "friday": "13:00-16:00,20:00-23:00",
                "saturday": "13:00-16:00,20:00-23:00",
                "sunday": "13:00-16:00,20:00-23:00"
            }
        }
    },
    {
        "organization_id": 1,
        "job_id": "test-job-2",
        "name": "Park Güell",
        "google_place_id": "ChIJjx37cOypEmsRAI_gHzWAyD4",
        "full_address": "Gràcia, 08024 Barcelona, Spain",
        "postal_code": "08024",
        "country": "Spain",
        "typical_time_spent": 180,  # minutes
        "rating": 4.6,
        "num_reviews": 89540,
        "extra": {
            "website": "https://parkguell.barcelona",
            "category": "Tourist Attraction",
            "subcategory": "Park",
            "entrance_fee": "€10.00",
            "accessibility": "Partially accessible",
            "opening_hours": {
                "monday": "09:30-19:30",
                "tuesday": "09:30-19:30",
                "wednesday": "09:30-19:30",
                "thursday": "09:30-19:30",
                "friday": "09:30-19:30",
                "saturday": "09:30-19:30",
                "sunday": "09:30-19:30"
            }
        }
    },
    {
        "organization_id": 2,
        "job_id": "test-job-3",
        "name": "The Louvre Museum",
        "google_place_id": "ChIJD3uTd9hx5kcR1IQvGfr8dbk",
        "full_address": "Rue de Rivoli, 75001 Paris, France",
        "postal_code": "75001",
        "country": "France",
        "typical_time_spent": 240,  # minutes
        "rating": 4.7,
        "num_reviews": 125000,
        "extra": {
            "phone": "+33 1 40 20 50 50",
            "website": "https://louvre.fr",
            "category": "Museum",
            "subcategory": "Art Museum",
            "entrance_fee": "€17.00",
            "audio_guide": "Available in 7 languages",
            "opening_hours": {
                "monday": "09:00-18:00",
                "tuesday": "Closed",
                "wednesday": "09:00-21:45",
                "thursday": "09:00-18:00",
                "friday": "09:00-21:45",
                "saturday": "09:00-18:00",
                "sunday": "09:00-18:00"
            }
        }
    }
]

# Places creation data for API tests
PLACE_CREATE_DATA = {
    "name": "Test Venue",
    "google_place_id": "ChIJTest123456789",
    "full_address": "123 Test Street, Test City, Test Country",
    "postal_code": "12345",
    "country": "Test Country",
    "typical_time_spent": 60,
    "rating": 4.0,
    "num_reviews": 100,
    "extra": {
        "phone": "+1 123 456 7890",
        "category": "Test Category",
        "price_level": 2
    }
}

# Places update data
PLACE_UPDATE_DATA = {
    "name": "Updated Test Venue",
    "rating": 4.5,
    "num_reviews": 150,
    "extra": {
        "phone": "+1 123 456 7890",
        "category": "Updated Category",
        "price_level": 3,
        "last_updated": "2024-01-15"
    }
}

# Invalid places data for testing validation
INVALID_PLACE_DATA = [
    {
        "name": "",  # Empty name
        "google_place_id": "ChIJTest123456789",
        "full_address": "123 Test Street",
        "postal_code": "12345",
        "country": "Test Country",
        "typical_time_spent": 60,
        "rating": 4.0,
        "num_reviews": 100
    },
    {
        "name": "Test Place",
        "google_place_id": "",  # Empty google_place_id
        "full_address": "123 Test Street",
        "postal_code": "12345",
        "country": "Test Country",
        "typical_time_spent": 60,
        "rating": 4.0,
        "num_reviews": 100
    },
    {
        "name": "Test Place",
        "google_place_id": "ChIJTest123456789",
        "full_address": "123 Test Street",
        "postal_code": "12345",
        "country": "Test Country",
        "typical_time_spent": -10,  # Negative time
        "rating": 4.0,
        "num_reviews": 100
    },
    {
        "name": "Test Place",
        "google_place_id": "ChIJTest123456789",
        "full_address": "123 Test Street",
        "postal_code": "12345",
        "country": "Test Country",
        "typical_time_spent": 60,
        "rating": 6.0,  # Rating too high (should be 0-5)
        "num_reviews": 100
    },
    {
        "name": "Test Place",
        "google_place_id": "ChIJTest123456789",
        "full_address": "123 Test Street",
        "postal_code": "12345",
        "country": "Test Country",
        "typical_time_spent": 60,
        "rating": 4.0,
        "num_reviews": -5  # Negative reviews
    }
]

# Realistic places data for different types of venues
VENUE_TYPES = {
    "hotel": {
        "name": "Luxury Beach Resort",
        "google_place_id": "ChIJHotel123456789",
        "full_address": "Ocean Drive 456, Miami Beach, FL, USA",
        "postal_code": "33139",
        "country": "USA",
        "typical_time_spent": 1440,  # Full day stay
        "rating": 4.8,
        "num_reviews": 2500,
        "extra": {
            "category": "Hotel",
            "star_rating": 5,
            "amenities": ["Pool", "Spa", "Beach Access", "Restaurant"],
            "check_in": "15:00",
            "check_out": "11:00"
        }
    },
    "restaurant": {
        "name": "Michelin Star Bistro",
        "google_place_id": "ChIJRestaurant123456789",
        "full_address": "Gourmet Street 789, New York, NY, USA",
        "postal_code": "10001",
        "country": "USA",
        "typical_time_spent": 120,
        "rating": 4.9,
        "num_reviews": 850,
        "extra": {
            "category": "Restaurant",
            "cuisine": "French",
            "price_level": 4,
            "michelin_stars": 1,
            "reservations_required": True
        }
    },
    "attraction": {
        "name": "Historic Castle",
        "google_place_id": "ChIJAttraction123456789",
        "full_address": "Castle Hill 1, Edinburgh, Scotland, UK",
        "postal_code": "EH1 2NG",
        "country": "United Kingdom",
        "typical_time_spent": 150,
        "rating": 4.6,
        "num_reviews": 15600,
        "extra": {
            "category": "Tourist Attraction",
            "subcategory": "Historical Site",
            "entrance_fee": "£17.50",
            "audio_guide_available": True,
            "wheelchair_accessible": False
        }
    },
    "museum": {
        "name": "Modern Art Gallery",
        "google_place_id": "ChIJMuseum123456789",
        "full_address": "Art District 321, London, UK",
        "postal_code": "SW1A 1AA",
        "country": "United Kingdom",
        "typical_time_spent": 180,
        "rating": 4.4,
        "num_reviews": 5200,
        "extra": {
            "category": "Museum",
            "subcategory": "Art Gallery",
            "entrance_fee": "£12.00",
            "free_admission_days": ["First Friday of month"],
            "exhibitions": ["Contemporary Art", "Digital Installations"]
        }
    }
}

# Places data with different ratings for testing filters
PLACES_BY_RATING = [
    {
        "name": "Excellent Venue",
        "rating": 4.8,
        "num_reviews": 1000,
        "google_place_id": "ChIJExcellent123",
        "full_address": "High Quality St, City, Country",
        "postal_code": "12345",
        "country": "Test Country",
        "typical_time_spent": 120
    },
    {
        "name": "Good Venue",
        "rating": 4.2,
        "num_reviews": 500,
        "google_place_id": "ChIJGood123",
        "full_address": "Good Quality St, City, Country",
        "postal_code": "12346",
        "country": "Test Country",
        "typical_time_spent": 90
    },
    {
        "name": "Average Venue",
        "rating": 3.5,
        "num_reviews": 200,
        "google_place_id": "ChIJAverage123",
        "full_address": "Average St, City, Country",
        "postal_code": "12347",
        "country": "Test Country",
        "typical_time_spent": 60
    },
    {
        "name": "Poor Venue",
        "rating": 2.1,
        "num_reviews": 50,
        "google_place_id": "ChIJPoor123",
        "full_address": "Low Quality St, City, Country",
        "postal_code": "12348",
        "country": "Test Country",
        "typical_time_spent": 30
    }
]
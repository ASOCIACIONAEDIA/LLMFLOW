"""Product test data fixtures."""

# Sample product data
SAMPLE_PRODUCTS = [
    {
        "name": "Test Product 1",
        "description": "A sample product for testing",
        "category": "Electronics",
        "price": 99.99,
        "is_active": True
    },
    {
        "name": "Test Product 2",
        "description": "Another sample product",
        "category": "Books",
        "price": 19.99,
        "is_active": True
    },
    {
        "name": "Inactive Product",
        "description": "An inactive product",
        "category": "Misc",
        "price": 5.00,
        "is_active": False
    }
]

# Product creation data
PRODUCT_CREATE_DATA = {
    "name": "New Product",
    "description": "A new product for testing",
    "category": "Test Category",
    "price": 29.99
}

# Product update data
PRODUCT_UPDATE_DATA = {
    "name": "Updated Product",
    "price": 39.99,
    "is_active": False
}
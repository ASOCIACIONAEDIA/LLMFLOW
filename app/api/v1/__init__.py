from fastapi import APIRouter

from . import (
    auth, 
    jobs,
    places,
    products,
    reviews,
    source_config,
    units,
    users,
    ws
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(units.router, prefix="/units", tags=["Units"])
router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
router.include_router(source_config.router, prefix="/source-configs", tags=["Source Configurations"])
router.include_router(products.router, prefix="/products", tags=["Products"])
router.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
router.include_router(places.router, prefix="/places", tags=["Places"])
router.include_router(ws.router, prefix="/ws", tags=["WebSockets"])
from fastapi import APIRouter
from app.api.v1.endpoints import health

router = APIRouter()

router.include_router(health.router)
# Add more routers here as you create endpoints
# router.include_router(todos.router)
# router.include_router(auth.router)

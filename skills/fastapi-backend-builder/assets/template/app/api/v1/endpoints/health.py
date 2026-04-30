from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    return {"status": "healthy"}


@router.get("/ready")
def readiness_check():
    # Add database connectivity check here
    return {"status": "ready"}

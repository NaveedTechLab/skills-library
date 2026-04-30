from fastapi import APIRouter

api_router = APIRouter()

# Import and include routers here
# from app.api.v1.endpoints import auth, users
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])


@api_router.get("/")
async def root():
    return {"message": "API v1"}

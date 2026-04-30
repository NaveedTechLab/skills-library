from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.router import api_router
from app.core.middleware import add_middleware
from app.core.exception_handlers import add_exception_handlers
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_PREFIX}/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    add_middleware(app)
    add_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_PREFIX)
    return app


app = create_app()

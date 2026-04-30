from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
    ConflictError,
    AuthenticationError,
    AuthorizationError,
)


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "not_found",
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "validation_failed",
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "conflict",
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(AuthenticationError)
    async def auth_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "unauthorized",
                "message": exc.message,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthorizationError)
    async def authz_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "forbidden",
                "message": exc.message,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            loc = error.get("loc", ())
            field = ".".join(str(loc_part) for loc_part in loc[1:]) if len(loc) > 1 else str(loc[0]) if loc else "unknown"
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_failed",
                "message": "Request validation failed",
                "details": errors,
            },
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        # Log the error here in production
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
            },
        )

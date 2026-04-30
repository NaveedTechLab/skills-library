# Error Handling & Validation

## Table of Contents
1. [Custom Exceptions](#custom-exceptions)
2. [Exception Handlers](#exception-handlers)
3. [Pydantic Validation](#pydantic-validation)
4. [Response Models](#response-models)

---

## Custom Exceptions

### `app/core/exceptions.py`

```python
from typing import Any

class AppException(Exception):
    """Base exception for application errors."""
    def __init__(self, message: str, details: Any = None):
        self.message = message
        self.details = details
        super().__init__(message)

class NotFoundError(AppException):
    """Resource not found."""
    pass

class ValidationError(AppException):
    """Validation failed."""
    pass

class ConflictError(AppException):
    """Resource conflict (e.g., duplicate, optimistic lock)."""
    pass

class AuthenticationError(AppException):
    """Authentication failed."""
    pass

class AuthorizationError(AppException):
    """Insufficient permissions."""
    pass

class ExternalServiceError(AppException):
    """External service call failed."""
    pass
```

---

## Exception Handlers

### `app/core/exception_handlers.py`

```python
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from app.core.exceptions import (
    AppException,
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
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"][1:]),  # Skip 'body'
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
        # Log the error here
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
            },
        )
```

---

## Pydantic Validation

### `app/schemas/base.py`

```python
from pydantic import BaseModel, ConfigDict

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode
        str_strip_whitespace=True,
        validate_assignment=True,
    )

class CreateSchema(BaseSchema):
    """Base for create operations."""
    pass

class UpdateSchema(BaseSchema):
    """Base for update operations - all fields optional."""
    pass

class ResponseSchema(BaseSchema):
    """Base for response models."""
    pass
```

### Common Validators

```python
from typing import Annotated
from pydantic import AfterValidator, StringConstraints

def not_empty(v: str) -> str:
    if not v or not v.strip():
        raise ValueError("Field cannot be empty")
    return v.strip()

NonEmptyStr = Annotated[str, AfterValidator(not_empty)]

# String with length constraints
Title = Annotated[str, StringConstraints(min_length=1, max_length=255, strip_whitespace=True)]
Description = Annotated[str, StringConstraints(max_length=2000)]

# Email validation
from pydantic import EmailStr
Email = EmailStr
```

### Schema Examples

```python
from datetime import datetime
from pydantic import Field
from app.schemas.base import CreateSchema, UpdateSchema, ResponseSchema

class TodoCreate(CreateSchema):
    title: Title
    description: Description | None = None
    priority: Literal["low", "medium", "high"] | None = None
    due_date: datetime | None = None

class TodoUpdate(UpdateSchema):
    title: Title | None = None
    description: Description | None = None
    status: Literal["pending", "completed", "archived"] | None = None
    priority: Literal["low", "medium", "high"] | None = None
    due_date: datetime | None = None

class TodoResponse(ResponseSchema):
    id: int
    title: str
    description: str | None
    status: str
    priority: str | None
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime
```

---

## Response Models

### `app/schemas/common.py`

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginationParams(BaseModel):
    skip: int = 0
    limit: int = 20

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int

    @property
    def has_more(self) -> bool:
        return self.skip + len(self.items) < self.total

class ErrorDetail(BaseModel):
    field: str
    message: str
    type: str | None = None

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: list[ErrorDetail] | None = None

class SuccessResponse(BaseModel):
    message: str
    data: dict | None = None
```

### Using Generic Responses

```python
from app.schemas.common import PaginatedResponse
from app.schemas.todo import TodoResponse

# Type alias for paginated todos
TodoListResponse = PaginatedResponse[TodoResponse]

# In endpoint
@router.get("", response_model=TodoListResponse)
def list_todos(db: DbSession, pagination: Pagination):
    items, total = TodoService(db).list(pagination)
    return {
        "items": items,
        "total": total,
        "skip": pagination.skip,
        "limit": pagination.limit,
    }
```

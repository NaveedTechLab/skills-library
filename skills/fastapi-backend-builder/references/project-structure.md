# FastAPI Project Structure

## Table of Contents
1. [Standard Layout](#standard-layout)
2. [Module Responsibilities](#module-responsibilities)
3. [Naming Conventions](#naming-conventions)
4. [Import Organization](#import-organization)

---

## Standard Layout

```
project_name/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory, lifespan
│   ├── config.py            # Settings via pydantic-settings
│   ├── dependencies.py      # Shared dependencies (get_db, get_current_user)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py        # Main router aggregating all routes
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── endpoints/
│   │       │   ├── __init__.py
│   │       │   ├── health.py
│   │       │   ├── auth.py
│   │       │   └── {resource}.py
│   │       └── router.py    # v1 router
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py      # JWT, password hashing
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── middleware.py    # Custom middleware
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py          # SQLAlchemy Base, mixins
│   │   └── {resource}.py    # ORM models
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── base.py          # Shared schema mixins
│   │   ├── common.py        # Pagination, responses
│   │   └── {resource}.py    # Pydantic schemas per resource
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── {resource}.py    # Business logic
│   │
│   └── db/
│       ├── __init__.py
│       ├── session.py       # Engine, SessionLocal
│       └── migrations/      # Alembic migrations
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Fixtures
│   ├── test_api/
│   └── test_services/
│
├── alembic.ini
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Module Responsibilities

### `app/main.py`
- Create FastAPI application instance
- Configure lifespan (startup/shutdown)
- Include routers
- Add middleware
- Configure CORS

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.router import api_router
from app.core.middleware import add_middleware
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
        lifespan=lifespan,
    )
    add_middleware(app)
    app.include_router(api_router, prefix="/api")
    return app

app = create_app()
```

### `app/config.py`
- Environment-based configuration
- Validation via pydantic-settings

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "FastAPI App"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

settings = Settings()
```

### `app/dependencies.py`
- Database session dependency
- Current user dependency
- Pagination dependency

```python
from typing import Annotated, Generator
from fastapi import Depends, Query
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.schemas.common import PaginationParams

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbSession = Annotated[Session, Depends(get_db)]

def get_pagination(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> PaginationParams:
    return PaginationParams(skip=skip, limit=limit)

Pagination = Annotated[PaginationParams, Depends(get_pagination)]
```

### `app/api/v1/endpoints/{resource}.py`
- Route definitions only
- Delegate to services for business logic
- Use type annotations for all parameters

```python
from fastapi import APIRouter, status
from app.dependencies import DbSession, Pagination
from app.schemas.todo import TodoCreate, TodoResponse, TodoListResponse
from app.services.todo import TodoService

router = APIRouter(prefix="/todos", tags=["todos"])

@router.get("", response_model=TodoListResponse)
def list_todos(db: DbSession, pagination: Pagination):
    return TodoService(db).list(pagination)

@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(db: DbSession, data: TodoCreate):
    return TodoService(db).create(data)
```

### `app/services/{resource}.py`
- All business logic lives here
- Database operations
- Validation beyond Pydantic
- No HTTP concepts (status codes, Request, Response)

```python
from sqlalchemy.orm import Session
from app.models.todo import Todo
from app.schemas.todo import TodoCreate
from app.schemas.common import PaginationParams
from app.core.exceptions import NotFoundError

class TodoService:
    def __init__(self, db: Session):
        self.db = db

    def list(self, pagination: PaginationParams):
        query = self.db.query(Todo)
        total = query.count()
        items = query.offset(pagination.skip).limit(pagination.limit).all()
        return {"items": items, "total": total}

    def create(self, data: TodoCreate) -> Todo:
        todo = Todo(**data.model_dump())
        self.db.add(todo)
        self.db.commit()
        self.db.refresh(todo)
        return todo

    def get_or_404(self, id: int) -> Todo:
        todo = self.db.query(Todo).filter(Todo.id == id).first()
        if not todo:
            raise NotFoundError(f"Todo {id} not found")
        return todo
```

---

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Modules | snake_case | `user_service.py` |
| Classes | PascalCase | `UserService` |
| Functions | snake_case | `get_current_user` |
| Constants | UPPER_SNAKE | `DATABASE_URL` |
| Pydantic models | PascalCase + suffix | `UserCreate`, `UserResponse` |
| SQLAlchemy models | PascalCase (singular) | `User`, `Todo` |
| Database tables | snake_case (plural) | `users`, `todos` |
| API routes | kebab-case (plural) | `/api/v1/todos` |

---

## Import Organization

Order imports as:
1. Standard library
2. Third-party packages
3. Local application imports

```python
# Standard library
from datetime import datetime
from typing import Annotated

# Third-party
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Local
from app.dependencies import get_db
from app.schemas.user import UserCreate
from app.services.user import UserService
```

---
name: fastapi-backend-builder
description: Generate clean, production-ready FastAPI backends with RESTful API design, Pydantic models, SQLAlchemy database integration, and authentication-ready structure. Use when building new FastAPI projects, creating REST APIs, setting up backend services, implementing CRUD endpoints, or scaffolding Python web applications. Produces Kubernetes-ready, scalable project structures.
---

# FastAPI Backend Builder

Generate production-ready FastAPI backends following clean architecture principles with proper separation of concerns.

## Quick Start

Copy the template from `assets/template/` to create a new project:

```bash
cp -r assets/template/ ./my-project
cd my-project
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Architecture Principles

1. **No business logic in endpoints** - Routes delegate to services
2. **Services own business logic** - All validation, queries, and mutations
3. **Schemas separate from models** - Pydantic for API, SQLAlchemy for DB
4. **Dependencies for cross-cutting concerns** - DB sessions, auth, pagination
5. **Clean folder structure** - See project-structure.md reference

## Project Structure

```
app/
├── main.py              # App factory, lifespan
├── config.py            # Settings (pydantic-settings)
├── dependencies.py      # get_db, get_current_user, pagination
├── api/v1/endpoints/    # Route handlers only
├── core/                # Security, exceptions, middleware
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response models
├── services/            # Business logic layer
└── db/                  # Database session, migrations
```

## Adding a New Resource

### 1. Create Model (`app/models/{resource}.py`)

```python
from sqlalchemy import Column, String, ForeignKey, Integer
from app.models.base import BaseModel

class Todo(BaseModel):
    title = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
```

### 2. Create Schemas (`app/schemas/{resource}.py`)

```python
from app.schemas.base import CreateSchema, UpdateSchema, ResponseSchema

class TodoCreate(CreateSchema):
    title: str

class TodoUpdate(UpdateSchema):
    title: str | None = None

class TodoResponse(ResponseSchema):
    id: int
    title: str
```

### 3. Create Service (`app/services/{resource}.py`)

```python
from sqlalchemy.orm import Session
from app.models.todo import Todo
from app.core.exceptions import NotFoundError

class TodoService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_404(self, id: int) -> Todo:
        todo = self.db.query(Todo).filter(Todo.id == id).first()
        if not todo:
            raise NotFoundError(f"Todo {id} not found")
        return todo
```

### 4. Create Endpoint (`app/api/v1/endpoints/{resource}.py`)

```python
from fastapi import APIRouter, status
from app.dependencies import DbSession
from app.schemas.todo import TodoCreate, TodoResponse
from app.services.todo import TodoService

router = APIRouter(prefix="/todos", tags=["todos"])

@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(db: DbSession, data: TodoCreate):
    return TodoService(db).create(data)
```

### 5. Register Router (`app/api/v1/router.py`)

```python
from app.api.v1.endpoints import todos
router.include_router(todos.router)
```

## Key Patterns

### Type-Annotated Dependencies

```python
from typing import Annotated
from fastapi import Depends

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
```

### Response Models

```python
from app.schemas.common import PaginatedResponse
TodoListResponse = PaginatedResponse[TodoResponse]
```

### Exception Flow

Services raise domain exceptions → Exception handlers convert to HTTP responses

```python
# In service
raise NotFoundError("Todo not found")

# Handled automatically → 404 JSON response
```

## References

- [references/project-structure.md](references/project-structure.md) - Detailed folder layout and module responsibilities
- [references/database-patterns.md](references/database-patterns.md) - SQLAlchemy models, async support, Alembic migrations
- [references/auth-security.md](references/auth-security.md) - JWT, OAuth2, RBAC, security middleware
- [references/error-handling.md](references/error-handling.md) - Custom exceptions, validation, response models

## Kubernetes Readiness

The template includes:
- Health endpoints (`/health`, `/health/ready`)
- Dockerfile with non-root user
- docker-compose for local development
- Environment-based configuration
- Connection pooling for databases

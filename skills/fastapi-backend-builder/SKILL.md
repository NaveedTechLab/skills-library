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

---

## When NOT to Use This

- **Simple scripts or CLIs** — Use plain Python, not a full FastAPI app
- **Serverless functions** — AWS Lambda/Cloud Functions have different patterns; this template assumes a long-running process
- **Read-only data APIs with no auth** — Overkill; use a lightweight framework
- **Prototypes under 50 lines** — Start simple, migrate to this structure only when the project grows
- **You need GraphQL** — This template is REST-only; use Strawberry or Ariadne for GraphQL

---

## Common Mistakes

1. **Business logic inside endpoints** — Endpoints must only call services; never put DB queries or calculations directly in route handlers
2. **Not using async for I/O** — All DB calls and HTTP requests must be `async def` to avoid blocking the event loop
3. **Skipping Pydantic validation** — Never accept raw `dict` from requests; always validate with a Pydantic schema
4. **Hardcoding secrets** — Use `pydantic-settings` with `.env` files; never commit credentials
5. **Missing database migrations** — Always use Alembic; never let SQLAlchemy auto-create tables in production
6. **No pagination on list endpoints** — Every endpoint returning a list must support `limit` + `offset` or cursor pagination
7. **Ignoring connection pool limits** — Set `pool_size` and `max_overflow` on your SQLAlchemy engine or you'll exhaust DB connections under load

---

## Performance Tips

- **Enable async SQLAlchemy** — Use `asyncpg` driver with `create_async_engine` for 3–5x throughput improvement on DB-heavy endpoints
- **Add Redis caching** — Cache frequently-read, rarely-changed data (user profiles, config) with a 60s TTL
- **Use `response_model_exclude_unset=True`** — Reduces payload size by omitting None fields
- **Batch DB operations** — Use `db.execute(insert(Model).values([...]))` for bulk inserts instead of looping
- **Profile slow endpoints** — Add `X-Process-Time` middleware to log response time; optimize anything over 200ms
- **Use Uvicorn with multiple workers** — `uvicorn app.main:app --workers 4` for multi-core machines

---

## Real Production Example

**User Authentication Microservice** (deployed at hackathon, handling 500+ req/min):

```
POST /auth/register   → Create user, hash password (bcrypt), return JWT
POST /auth/login      → Verify credentials, return access + refresh token
GET  /auth/me         → Return current user profile (JWT-protected)
POST /auth/refresh    → Rotate refresh token
DELETE /auth/logout   → Blacklist refresh token in Redis
```

Key decisions made:
- Refresh tokens stored in Redis with 7-day TTL (not DB — faster lookup)
- Passwords hashed with bcrypt cost factor 12 (balances security vs. speed)
- JWT expiry: 15 min access, 7 day refresh
- Rate limiting via `slowapi`: 5 login attempts per minute per IP

---

## Related Skills

- [`database-postgresql-design`](../database-postgresql-design/SKILL.md) — Design the schema before building the API
- [`kubernetes-deployer`](../kubernetes-deployer/SKILL.md) — Deploy this FastAPI app to Kubernetes
- [`backend-rest-api`](../backend-rest-api/SKILL.md) — REST API design principles
- [`realtime-websocket-system`](../realtime-websocket-system/SKILL.md) — Add WebSocket endpoints alongside REST
- [`qa-debugging-performance`](../qa-debugging-performance/SKILL.md) — Test and benchmark the API

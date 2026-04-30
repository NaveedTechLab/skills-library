# Database Integration Patterns

## Table of Contents
1. [SQLAlchemy Setup](#sqlalchemy-setup)
2. [Model Patterns](#model-patterns)
3. [Async Support](#async-support)
4. [Alembic Migrations](#alembic-migrations)

---

## SQLAlchemy Setup

### `app/db/session.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### `app/models/base.py`

```python
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import declarative_base, declared_attr

Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class TableNameMixin:
    @declared_attr
    def __tablename__(cls) -> str:
        # Convert CamelCase to snake_case and pluralize
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        return f"{name}s"

class BaseModel(Base, TimestampMixin, TableNameMixin):
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)
```

---

## Model Patterns

### Basic Model

```python
from sqlalchemy import Column, String, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.models.base import BaseModel

class TodoStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class Todo(BaseModel):
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(TodoStatus),
        default=TodoStatus.PENDING,
        nullable=False
    )
```

### UUID Primary Key

```python
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
import uuid

class BaseModelUUID(Base, TimestampMixin, TableNameMixin):
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

### Foreign Key Relationships

```python
from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

class Todo(BaseModel):
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="todos")

class User(BaseModel):
    todos = relationship("Todo", back_populates="user", cascade="all, delete-orphan")
```

### Soft Delete

```python
from sqlalchemy import Column, DateTime
from datetime import datetime

class SoftDeleteMixin:
    deleted_at = Column(DateTime, nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self):
        self.deleted_at = datetime.utcnow()
```

---

## Async Support

### `app/db/session.py` (async)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

# Convert sync URL to async: postgresql:// -> postgresql+asyncpg://
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

### Async Dependency

```python
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

AsyncDbSession = Annotated[AsyncSession, Depends(get_async_db)]
```

### Async Service Pattern

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class TodoService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, pagination: PaginationParams):
        query = select(Todo).offset(pagination.skip).limit(pagination.limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create(self, data: TodoCreate) -> Todo:
        todo = Todo(**data.model_dump())
        self.db.add(todo)
        await self.db.commit()
        await self.db.refresh(todo)
        return todo
```

---

## Alembic Migrations

### Initialize

```bash
alembic init app/db/migrations
```

### `alembic.ini` key settings

```ini
[alembic]
script_location = app/db/migrations
sqlalchemy.url = driver://user:pass@localhost/dbname
```

### `app/db/migrations/env.py`

```python
from app.config import settings
from app.models.base import Base
# Import all models so Alembic can detect them
from app.models import user, todo  # noqa

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

### Common Commands

```bash
# Create migration
alembic revision --autogenerate -m "Add todos table"

# Run migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

### Migration Best Practices

1. **Review auto-generated migrations** - Alembic may miss some changes
2. **Test rollback** - Ensure `downgrade()` works
3. **One change per migration** - Keep migrations focused
4. **Name migrations clearly** - `add_todos_table`, `add_user_email_index`
5. **Handle data migrations separately** - Don't mix schema and data changes

import re
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
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return f"{name}s"


class BaseModel(Base, TimestampMixin, TableNameMixin):
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)

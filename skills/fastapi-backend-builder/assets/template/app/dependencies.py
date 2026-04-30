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
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
) -> PaginationParams:
    return PaginationParams(skip=skip, limit=limit)


Pagination = Annotated[PaginationParams, Depends(get_pagination)]

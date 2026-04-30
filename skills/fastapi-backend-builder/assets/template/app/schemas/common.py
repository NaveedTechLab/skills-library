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

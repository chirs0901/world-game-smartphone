"""Common Pydantic schemas shared across modules."""

from typing import Optional

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None

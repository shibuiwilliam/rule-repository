"""Common schema types shared across API endpoints."""

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Standard pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class ErrorDetail(BaseModel):
    """Structured error detail returned in API error responses."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard API error response envelope."""

    error: ErrorDetail

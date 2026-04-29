"""Pydantic schemas for search operations."""

from pydantic import BaseModel, Field

from rulerepo_server.domain.rule import Modality, Severity
from rulerepo_server.schemas.rule import RuleResponse


class SearchQuery(BaseModel):
    """Parameters for a search request."""

    query: str = Field(..., min_length=1, max_length=2000, description="Search query text")
    scope: list[str] | None = None
    modality: Modality | None = None
    severity: Severity | None = None
    tags: list[str] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CategorySearchQuery(BaseModel):
    """Parameters for category/filter-based search (no free-text query)."""

    scope: list[str] | None = None
    modality: Modality | None = None
    severity: Severity | None = None
    tags: list[str] | None = None
    status: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ContextSearchQuery(BaseModel):
    """Parameters for context search — given facts, find applicable rules."""

    facts: dict[str, str | int | float | bool | list[str]] = Field(
        ..., description="Key-value pairs describing the current context/situation"
    )
    scope: list[str] | None = Field(default=None, description="Narrow search to specific scopes")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchResultItem(BaseModel):
    """A single search result with relevance score."""

    rule: RuleResponse
    score: float = 0.0


class SearchResponse(BaseModel):
    """Paginated search results."""

    items: list[SearchResultItem]
    total: int
    page: int
    page_size: int
    query: str = ""


class DocumentSearchQuery(BaseModel):
    """Parameters for document search by filename or content."""

    query: str = Field(..., min_length=1, max_length=2000, description="Search by filename or content")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SourceDocSearchQuery(BaseModel):
    """Parameters for searching rules by their source document."""

    document_id: str = Field(..., description="Document UUID to find rules extracted from")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

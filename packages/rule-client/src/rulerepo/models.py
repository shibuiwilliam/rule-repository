"""SDK response models — Pydantic models mirroring server response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class Rule(BaseModel):
    """A rule returned by the API."""

    model_config = ConfigDict(extra="allow")

    id: str
    statement: str
    modality: str
    severity: str
    status: str
    scope: list[str] = []
    tags: list[str] = []
    rationale: str = ""
    preconditions: list[str] = []
    exceptions: list[str] = []
    source_refs: list[dict[str, Any]] = []
    effective_period: dict[str, Any] = {}
    governance: dict[str, Any] = {}
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RuleList(BaseModel):
    """Paginated list of rules."""

    items: list[Rule]
    total: int
    page: int
    page_size: int


class SearchResultItem(BaseModel):
    """A search result with score."""

    rule: Rule
    score: float = 0.0


class SearchResult(BaseModel):
    """Search response."""

    items: list[SearchResultItem]
    total: int
    page: int
    page_size: int
    query: str = ""


class IntentResult(BaseModel):
    """Response from the Intent API."""

    intent: str
    result: dict[str, Any] = {}
    explanation: str = ""


class Revision(BaseModel):
    """A rule revision."""

    model_config = ConfigDict(extra="allow")

    id: str
    rule_id: str
    revision_number: int
    statement: str
    modality: str
    severity: str
    status: str
    changed_by: str = ""
    change_note: str = ""
    created_at: datetime | None = None


class Relationship(BaseModel):
    """A rule relationship."""

    source_id: str
    target_id: str
    relationship_type: str
    created_at: datetime | None = None
    created_by: str = ""


class UploadResult(BaseModel):
    """Document upload response."""

    document_id: str
    filename: str
    mime_type: str
    size_bytes: int


class ExtractionResult(BaseModel):
    """Extraction pipeline response."""

    model_config = ConfigDict(extra="allow")

    extraction_id: str
    document_id: str
    candidates: list[dict[str, Any]] = []
    model_id: str = ""

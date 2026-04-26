"""Pydantic schemas for document upload and rule extraction."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from rulerepo_server.schemas.rule import RuleCreate


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""

    document_id: str
    filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


class CandidateRule(BaseModel):
    """A candidate rule proposed by the extraction pipeline, pending human review."""

    index: int
    statement: str
    modality: str = "MUST"
    severity: str = "MEDIUM"
    scope: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    rationale: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_section: str | None = None
    source_page: int | None = None
    suggested_relationships: list[dict[str, str]] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Result of running the extraction pipeline on a document."""

    extraction_id: UUID
    document_id: str
    candidates: list[CandidateRule]
    model_id: str
    extracted_at: datetime


class CandidateReviewRequest(BaseModel):
    """Request to approve/reject/edit extracted candidate rules."""

    extraction_id: UUID
    approved_indices: list[int] = Field(
        default_factory=list,
        description="Indices of candidates to approve as-is",
    )
    edits: dict[int, RuleCreate] = Field(
        default_factory=dict,
        description="Edited versions of candidates, keyed by index",
    )

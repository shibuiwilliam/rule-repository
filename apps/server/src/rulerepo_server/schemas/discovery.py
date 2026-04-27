"""Pydantic request/response schemas for the discovery API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ScanRequest(BaseModel):
    """Request body for starting a discovery scan.

    Attributes:
        sources: List of source type identifiers to analyze.
        file_contents: Mapping of file path to file content text.
        repository: Optional repository name or URL.
    """

    model_config = ConfigDict(strict=True)

    sources: list[str]
    file_contents: dict[str, str] = {}
    repository: str | None = None


class ScanResponse(BaseModel):
    """Response for a discovery scan.

    Attributes:
        scan_id: UUID of the scan.
        status: Current scan status.
        candidates_found: Number of candidates discovered.
    """

    model_config = ConfigDict(from_attributes=True)

    scan_id: str
    status: str
    candidates_found: int


class CandidateResponse(BaseModel):
    """Response for a single discovery candidate.

    Attributes:
        id: UUID of the candidate.
        statement: The candidate rule statement.
        modality: Deontic modality (MUST, SHOULD, etc.).
        severity: Severity level.
        scope: Applicable scope tags.
        tags: Categorization tags.
        rationale: Optional explanation for why this rule matters.
        source_type: The analyzer that discovered this candidate.
        source_evidence: Raw evidence supporting the candidate.
        confidence: Confidence score in [0, 1].
        status: Review status (pending, approved, dismissed).
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    statement: str
    modality: str
    severity: str
    scope: list[str]
    tags: list[str]
    rationale: str | None = None
    source_type: str
    source_evidence: str | None = None
    confidence: float
    status: str


class CandidateEditRequest(BaseModel):
    """Request body for editing a candidate before approval.

    All fields are optional — only provided fields are updated.

    Attributes:
        statement: Updated rule statement.
        modality: Updated modality.
        severity: Updated severity.
        scope: Updated scope tags.
        tags: Updated categorization tags.
    """

    model_config = ConfigDict(strict=True)

    statement: str | None = None
    modality: str | None = None
    severity: str | None = None
    scope: list[str] | None = None
    tags: list[str] | None = None

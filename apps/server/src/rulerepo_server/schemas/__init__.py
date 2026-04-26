"""Pydantic request/response schemas for API boundaries."""

from rulerepo_server.schemas.common import ErrorDetail, ErrorResponse, PaginationParams
from rulerepo_server.schemas.extraction import (
    CandidateReviewRequest,
    CandidateRule,
    DocumentUploadResponse,
    ExtractionResult,
)
from rulerepo_server.schemas.intent import IntentRequest, IntentResponse
from rulerepo_server.schemas.rule import (
    RelationshipCreate,
    RelationshipResponse,
    RuleCreate,
    RuleListResponse,
    RuleResponse,
    RuleRevisionResponse,
    RuleUpdate,
)
from rulerepo_server.schemas.search import (
    CategorySearchQuery,
    SearchQuery,
    SearchResponse,
    SearchResultItem,
)

__all__ = [
    "CandidateReviewRequest",
    "CandidateRule",
    "CategorySearchQuery",
    "DocumentUploadResponse",
    "ErrorDetail",
    "ErrorResponse",
    "ExtractionResult",
    "IntentRequest",
    "IntentResponse",
    "PaginationParams",
    "RelationshipCreate",
    "RelationshipResponse",
    "RuleCreate",
    "RuleListResponse",
    "RuleResponse",
    "RuleRevisionResponse",
    "RuleUpdate",
    "SearchQuery",
    "SearchResponse",
    "SearchResultItem",
]

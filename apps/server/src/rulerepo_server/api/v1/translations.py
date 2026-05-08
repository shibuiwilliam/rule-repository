"""REST API routes for polyglot rule translations.

See IMPROVEMENT.md RR-020.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.translation.service import TranslationService

logger = get_logger(__name__)

router = APIRouter(tags=["translations"])

# ---------------------------------------------------------------------------
# Singleton service (in-memory for now; will be replaced by DI with Postgres)
# ---------------------------------------------------------------------------

_service: TranslationService | None = None


def _get_service() -> TranslationService:
    """Return the module-level TranslationService singleton."""
    global _service
    if _service is None:
        _service = TranslationService()
    return _service


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CreateTranslationRequest(BaseModel):
    """Request body for adding a translation to a rule."""

    language: str = Field(
        ...,
        min_length=2,
        max_length=35,
        description="BCP-47 language tag (e.g. 'ja', 'de', 'fr').",
    )
    statement: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Translated rule statement text.",
    )
    translator: str = Field(
        default="human",
        max_length=100,
        description="Who or what produced the translation.",
    )


class TranslationResponse(BaseModel):
    """Serialized rule translation."""

    id: str
    rule_id: str
    language: str
    statement: str
    translator: str
    equivalence_score: float
    last_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VerificationResponse(BaseModel):
    """Result of a translation verification."""

    translation_id: str
    original_statement: str
    translated_statement: str
    back_translated: str
    equivalence_score: float
    verified_at: datetime
    passed: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_translation(t: object) -> TranslationResponse:
    """Convert a domain RuleTranslation to its API response model."""
    from rulerepo_server.domain.translation import RuleTranslation

    assert isinstance(t, RuleTranslation)
    return TranslationResponse(
        id=str(t.id),
        rule_id=str(t.rule_id),
        language=t.language,
        statement=t.statement,
        translator=t.translator,
        equivalence_score=t.equivalence_score,
        last_verified_at=t.last_verified_at,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/rules/{rule_id}/translations",
    response_model=TranslationResponse,
    status_code=201,
)
async def create_translation(
    rule_id: UUID,
    body: CreateTranslationRequest,
    svc: TranslationService = Depends(_get_service),
) -> TranslationResponse:
    """Add a translation for an existing rule."""
    translation = await svc.create_translation(
        rule_id=rule_id,
        language=body.language,
        statement=body.statement,
        translator=body.translator,
    )
    return _serialize_translation(translation)


@router.get(
    "/rules/{rule_id}/translations",
    response_model=list[TranslationResponse],
)
async def list_translations(
    rule_id: UUID,
    svc: TranslationService = Depends(_get_service),
) -> list[TranslationResponse]:
    """List all translations for a rule."""
    translations = await svc.get_translations(rule_id)
    return [_serialize_translation(t) for t in translations]


@router.post(
    "/translations/{translation_id}/verify",
    response_model=VerificationResponse,
)
async def verify_translation(
    translation_id: UUID,
    svc: TranslationService = Depends(_get_service),
) -> VerificationResponse:
    """Trigger verification of a translation's accuracy.

    Back-translates the statement and computes semantic similarity
    against the original rule.
    """
    try:
        result = await svc.verify_translation(translation_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return VerificationResponse(
        translation_id=str(result.translation_id),
        original_statement=result.original_statement,
        translated_statement=result.translated_statement,
        back_translated=result.back_translated,
        equivalence_score=result.equivalence_score,
        verified_at=result.verified_at,
        passed=result.passed,
    )


@router.get(
    "/translations/stale",
    response_model=list[TranslationResponse],
)
async def list_stale_translations(
    days_threshold: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days after which a verification is considered stale.",
    ),
    svc: TranslationService = Depends(_get_service),
) -> list[TranslationResponse]:
    """List translations that need reverification."""
    translations = await svc.list_stale_translations(days_threshold=days_threshold)
    return [_serialize_translation(t) for t in translations]

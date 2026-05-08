"""Onboarding wizard API — guides new users to first value (RR-004)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import RuleModel
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/onboarding", tags=["onboarding"])

AVAILABLE_TEMPLATES: list[str] = [
    "engineering/python-fastapi",
    "engineering/typescript-react",
    "engineering/security-owasp",
    "legal/contract-review",
    "hr/attendance-policy",
    "finance/expense-compliance",
]


class OnboardingStatus(BaseModel):
    """Current onboarding state for the tenant."""

    needs_onboarding: bool = True
    total_rules: int = 0
    has_active_rules: bool = False
    suggested_domain: str = "engineering"
    available_templates: list[str] = Field(default_factory=list)


@router.get("/status", response_model=OnboardingStatus)
async def get_onboarding_status(
    session: AsyncSession = Depends(get_db_session),
) -> OnboardingStatus:
    """Check whether onboarding is needed (zero rules = needs onboarding).

    Returns the current onboarding state including rule counts and
    available domain templates.
    """
    result = await session.execute(select(func.count(RuleModel.id)))
    total_rules = result.scalar() or 0

    active_result = await session.execute(
        select(func.count(RuleModel.id)).where(RuleModel.status.in_(["APPROVED", "EFFECTIVE"]))
    )
    active_rules = active_result.scalar() or 0

    logger.info(
        "onboarding_status_checked",
        total_rules=total_rules,
        active_rules=active_rules,
    )

    return OnboardingStatus(
        needs_onboarding=total_rules == 0,
        total_rules=total_rules,
        has_active_rules=active_rules > 0,
        available_templates=AVAILABLE_TEMPLATES,
    )

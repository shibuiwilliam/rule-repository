"""Upcoming changes API -- pending rule proposals and effective-date changes (RR-036)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/upcoming-changes", tags=["governance"])


class UpcomingChange(BaseModel):
    """Schema for a single upcoming rule change."""

    rule_id: str = ""
    change_type: str = ""  # "new_rule", "amendment", "retirement", "effective_date"
    summary: str = ""
    effective_date: str | None = None
    status: str = ""  # "pending_approval", "approved", "scheduled"
    proposed_by: str = ""


@router.get("")
async def get_upcoming_changes(
    days_ahead: int = 30,
    tenant_id: str = "default",
) -> dict:
    """Get rules with upcoming effective dates or pending proposals.

    In production, queries the proposals table and rules with
    future effective_period.valid_from dates.

    Args:
        days_ahead: How many days into the future to look.
        tenant_id: Tenant to filter by.

    Returns:
        Dict with upcoming changes list and metadata.
    """
    logger.info(
        "upcoming_changes_requested",
        days_ahead=days_ahead,
        tenant_id=tenant_id,
    )
    return {
        "tenant_id": tenant_id,
        "period_days": days_ahead,
        "changes": [],
        "total": 0,
        "generated_at": datetime.now(tz=UTC).isoformat(),
    }

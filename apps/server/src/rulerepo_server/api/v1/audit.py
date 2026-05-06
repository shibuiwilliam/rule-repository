"""REST API routes for audit log inspection.

Provides read-only access to the append-only audit log with
filtering, pagination, and chain verification.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.audit_repo import AuditLogRepository
from rulerepo_server.adapters.postgres.models import AuditLogModel
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


def _model_to_dict(entry: AuditLogModel) -> dict:
    """Convert an AuditLogModel to a JSON-serializable dict."""
    return {
        "id": str(entry.id),
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "action": entry.action,
        "actor": entry.actor,
        "resource_type": entry.resource_type,
        "resource_id": entry.resource_id,
        "details": entry.details,
        "previous_hash": entry.previous_hash,
        "entry_hash": entry.entry_hash,
    }


@router.get("")
async def list_audit_entries(
    rule_id: str | None = Query(default=None, description="Filter by resource_id matching this rule ID"),
    action: str | None = Query(default=None, description="Filter by action (e.g. rule_created, evaluation_completed)"),
    actor: str | None = Query(default=None, description="Filter by actor"),
    since: datetime | None = Query(default=None, description="Only entries after this timestamp (ISO 8601)"),
    until: datetime | None = Query(default=None, description="Only entries before this timestamp (ISO 8601)"),
    resource_type: str | None = Query(default=None, description="Filter by resource type (e.g. rule, extraction)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """List audit log entries with optional filters and pagination.

    Returns a paginated list of audit entries ordered by timestamp descending.
    """
    # Build base query
    query = select(AuditLogModel)
    count_query = select(func.count(AuditLogModel.id))

    # Apply filters
    if rule_id is not None:
        query = query.where(AuditLogModel.resource_id == rule_id)
        count_query = count_query.where(AuditLogModel.resource_id == rule_id)
    if action is not None:
        query = query.where(AuditLogModel.action == action)
        count_query = count_query.where(AuditLogModel.action == action)
    if actor is not None:
        query = query.where(AuditLogModel.actor == actor)
        count_query = count_query.where(AuditLogModel.actor == actor)
    if since is not None:
        query = query.where(AuditLogModel.timestamp >= since)
        count_query = count_query.where(AuditLogModel.timestamp >= since)
    if until is not None:
        query = query.where(AuditLogModel.timestamp <= until)
        count_query = count_query.where(AuditLogModel.timestamp <= until)
    if resource_type is not None:
        query = query.where(AuditLogModel.resource_type == resource_type)
        count_query = count_query.where(AuditLogModel.resource_type == resource_type)

    # Get total count
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    query = query.order_by(AuditLogModel.timestamp.desc()).offset(offset).limit(page_size)

    result = await session.execute(query)
    entries = list(result.scalars().all())

    logger.info(
        "audit_entries_listed",
        total=total,
        page=page,
        page_size=page_size,
        filters_applied={
            "rule_id": rule_id,
            "action": action,
            "actor": actor,
            "since": str(since) if since else None,
            "until": str(until) if until else None,
            "resource_type": resource_type,
        },
    )

    return {
        "entries": [_model_to_dict(e) for e in entries],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@router.get("/verify")
async def verify_audit_chain(
    limit: int = Query(default=1000, ge=1, le=10000, description="Max entries to verify"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Verify the integrity of the audit log hash chain.

    Walks the chain from oldest to newest, recomputing hashes
    and checking that each entry's previous_hash matches the
    prior entry's entry_hash.
    """
    repo = AuditLogRepository(session)
    is_valid = await repo.verify_chain(limit=limit)

    # Get entry count for the response
    count_result = await session.execute(select(func.count(AuditLogModel.id)))
    total_entries = count_result.scalar_one()
    entries_checked = min(limit, total_entries)

    logger.info(
        "audit_chain_verification_requested",
        is_valid=is_valid,
        entries_checked=entries_checked,
        total_entries=total_entries,
    )

    return {
        "valid": is_valid,
        "entries_checked": entries_checked,
        "total_entries": total_entries,
    }

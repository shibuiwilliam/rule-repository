"""Audit exporter -- period x scope -> structured export.

Produces a structured audit export for auditors, including hash-chain
integrity verification. Supports filtering by scope and time period.

See CLAUDE.md section 11.4, IMPROVEMENT.md section 4.4 / RR-011.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import AuditLogModel
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AuditExport:
    """Result of an audit export operation.

    Attributes:
        scope: The scope filter applied (or ``None`` for all scopes).
        period_start: Start of the export period.
        period_end: End of the export period.
        entries: Serialised audit entries.
        total_count: Number of entries in the export.
        chain_valid: Whether the hash chain verified successfully.
    """

    scope: str | None
    period_start: datetime | None
    period_end: datetime | None
    entries: list[dict[str, Any]] = field(default_factory=list)
    total_count: int = 0
    chain_valid: bool = True


async def export_audit_log(
    session: AsyncSession,
    *,
    scope: str | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    tenant_id: str = "default",
    format: str = "json",
) -> dict[str, Any]:
    """Export audit log entries for a given scope and period.

    Queries the audit log, verifies chain integrity over the returned
    entries, and produces a structured dictionary suitable for JSON
    serialisation or downstream report generation.

    Args:
        session: Async SQLAlchemy session.
        scope: Optional scope filter (matched against ``resource_type``).
        period_start: Only include entries at or after this timestamp.
        period_end: Only include entries at or before this timestamp.
        tenant_id: Tenant scope for multi-tenant deployments.
        format: Output format hint (currently only ``json`` is supported).

    Returns:
        A dictionary containing export metadata, chain status, and entries.
    """
    stmt = select(AuditLogModel).order_by(AuditLogModel.timestamp.asc())

    if scope is not None:
        stmt = stmt.where(AuditLogModel.resource_type == scope)
    if period_start is not None:
        stmt = stmt.where(AuditLogModel.timestamp >= period_start)
    if period_end is not None:
        stmt = stmt.where(AuditLogModel.timestamp <= period_end)

    result = await session.execute(stmt)
    entries = list(result.scalars().all())

    # Verify chain integrity over the exported window
    chain_valid = verify_chain(entries)

    export_data: dict[str, Any] = {
        "export_timestamp": datetime.now(tz=UTC).isoformat(),
        "scope": scope,
        "tenant_id": tenant_id,
        "period": {
            "start": period_start.isoformat() if period_start else None,
            "end": period_end.isoformat() if period_end else None,
        },
        "total_entries": len(entries),
        "chain_integrity": "valid" if chain_valid else "BROKEN",
        "entries": [_entry_to_dict(e) for e in entries],
    }

    logger.info(
        "audit_exported",
        scope=scope,
        tenant_id=tenant_id,
        entries=len(entries),
        chain_valid=chain_valid,
    )

    return export_data


def verify_chain(entries: list[Any]) -> bool:
    """Verify hash chain integrity of audit entries.

    Walks the entry list (assumed to be in chronological order) and
    checks that each entry's ``previous_hash`` matches the preceding
    entry's ``entry_hash``.

    Args:
        entries: Ordered list of ``AuditLogModel`` instances.

    Returns:
        ``True`` if the chain is intact, ``False`` if any link is broken.
    """
    if not entries:
        return True

    for i in range(1, len(entries)):
        prev_hash = getattr(entries[i - 1], "entry_hash", None)
        curr_prev = getattr(entries[i], "previous_hash", None)
        if curr_prev != prev_hash:
            logger.warning(
                "export_chain_break_detected",
                index=i,
                entry_id=str(getattr(entries[i], "id", "?")),
                expected=prev_hash,
                actual=curr_prev,
            )
            return False

    return True


def _entry_to_dict(entry: Any) -> dict[str, Any]:
    """Serialise an ``AuditLogModel`` to a JSON-safe dictionary.

    Args:
        entry: An ``AuditLogModel`` instance.

    Returns:
        Dictionary representation of the entry.
    """
    return {
        "id": str(entry.id),
        "timestamp": (entry.timestamp.isoformat() if hasattr(entry.timestamp, "isoformat") else str(entry.timestamp)),
        "action": entry.action,
        "actor": entry.actor,
        "resource_type": entry.resource_type,
        "resource_id": str(entry.resource_id),
        "details": entry.details,
        "entry_hash": entry.entry_hash,
        "previous_hash": entry.previous_hash,
    }

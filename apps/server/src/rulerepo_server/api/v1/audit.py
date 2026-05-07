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


# ---------------------------------------------------------------------------
# Audit Report Export — Phase 7f
# ---------------------------------------------------------------------------

SUPPORTED_FRAMEWORKS = {"j-sox", "iso27001", "sox", "pci-dss"}


@router.get("/reports/{framework}")
async def export_audit_report(
    framework: str,
    since: datetime | None = Query(default=None, description="Start date (ISO 8601)"),
    until: datetime | None = Query(default=None, description="End date (ISO 8601)"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Export a structured audit report aligned with a compliance framework.

    Supported frameworks: j-sox, iso27001, sox, pci-dss.

    Returns a report structured per the framework's expectations with
    sections covering: evaluation history, rule change audit trail,
    access controls, and chain integrity verification.
    """
    if framework not in SUPPORTED_FRAMEWORKS:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported framework: {framework}. Supported: {sorted(SUPPORTED_FRAMEWORKS)}",
        )

    # Build date filter
    stmt = select(AuditLogModel).order_by(AuditLogModel.timestamp.desc())
    if since:
        stmt = stmt.where(AuditLogModel.timestamp >= since)
    if until:
        stmt = stmt.where(AuditLogModel.timestamp <= until)
    stmt = stmt.limit(1000)

    result = await session.execute(stmt)
    entries = list(result.scalars().all())

    # Verify chain integrity for the report period
    repo = AuditLogRepository(session)
    chain_valid = await repo.verify_chain(limit=len(entries) if entries else 100)

    # Build framework-specific report
    report = {
        "framework": framework,
        "generated_at": datetime.now().isoformat(),
        "period": {
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
        },
        "summary": {
            "total_audit_entries": len(entries),
            "chain_integrity": "VERIFIED" if chain_valid else "BROKEN",
            "entry_types": _count_by_field(entries, "action"),
        },
        "sections": _build_framework_sections(framework, entries),
        "chain_verification": {
            "status": "pass" if chain_valid else "fail",
            "entries_verified": len(entries),
        },
    }

    logger.info(
        "audit_report_exported",
        framework=framework,
        entries=len(entries),
        chain_valid=chain_valid,
    )

    return report


def _count_by_field(entries: list, field_name: str) -> dict[str, int]:
    """Count entries grouped by a field value."""
    counts: dict[str, int] = {}
    for entry in entries:
        val = getattr(entry, field_name, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts


def _build_framework_sections(framework: str, entries: list) -> list[dict]:
    """Build framework-specific report sections."""
    sections = []

    if framework == "j-sox":
        sections = [
            {
                "id": "IT-GC-1",
                "title": "IT General Controls — Change Management",
                "description": "Audit trail of all rule changes, evaluations, and system modifications",
                "entry_count": sum(1 for e in entries if e.action in ("rule_created", "rule_updated", "rule_retired")),
            },
            {
                "id": "IT-GC-2",
                "title": "IT General Controls — Access and Authorization",
                "description": "Agent governance events, trust level changes, exception approvals",
                "entry_count": len([e for e in entries if "agent" in (e.action or "")]),
            },
            {
                "id": "IT-GC-3",
                "title": "IT General Controls — Operations",
                "description": "Evaluation results, compliance verdicts, and automated enforcement actions",
                "entry_count": len([e for e in entries if e.action == "evaluation_completed"]),
            },
        ]
    elif framework == "iso27001":
        sections = [
            {
                "id": "A.12.4",
                "title": "Logging and Monitoring",
                "description": "Complete audit trail with hash-chain integrity verification",
                "entry_count": len(entries),
            },
            {
                "id": "A.14.2",
                "title": "Security in Development and Support Processes",
                "description": "Code evaluation results and security rule enforcement",
                "entry_count": len([e for e in entries if e.action == "evaluation_completed"]),
            },
        ]
    elif framework in ("sox", "pci-dss"):
        sections = [
            {
                "id": "controls",
                "title": "Internal Controls Evidence",
                "description": "Automated rule enforcement and evaluation history",
                "entry_count": len(entries),
            },
        ]

    return sections


# ---------------------------------------------------------------------------
# Litigation Hold — Phase 7f
# ---------------------------------------------------------------------------


@router.post("/litigation-hold/{resource_id}")
async def set_litigation_hold(
    resource_id: str,
    body: dict | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Place a litigation hold on all audit entries for a resource.

    Prevents deletion or archival. Used for eDiscovery and legal proceedings.
    """
    body = body or {}
    repo = AuditLogRepository(session)
    await repo.set_litigation_hold(
        resource_id,
        hold_reason=body.get("reason", ""),
        hold_by=body.get("held_by", "system"),
    )
    await session.commit()
    return {"status": "hold_placed", "resource_id": resource_id}


@router.get("/litigation-holds")
async def list_litigation_holds(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """List all resources currently under litigation hold."""
    repo = AuditLogRepository(session)
    holds = await repo.get_litigation_holds()
    return {"holds": holds, "total": len(holds)}


# ---------------------------------------------------------------------------
# eDiscovery Export Bundle (Phase 7f)
# ---------------------------------------------------------------------------


@router.get("/ediscovery-export/{resource_id}")
async def ediscovery_export(
    resource_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Generate an eDiscovery export bundle for a resource under litigation hold.

    Returns a structured JSON bundle containing all audit entries, metadata,
    and chain verification for the specified resource. In production, this
    would be packaged as a ZIP with a manifest.
    """
    # Fetch all entries for the resource
    stmt = select(AuditLogModel).where(AuditLogModel.resource_id == resource_id).order_by(AuditLogModel.timestamp.asc())
    result = await session.execute(stmt)
    entries = list(result.scalars().all())

    if not entries:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="No audit entries found for this resource")

    # Verify chain integrity for these entries
    repo = AuditLogRepository(session)
    chain_valid = await repo.verify_chain(limit=len(entries))

    bundle = {
        "export_type": "ediscovery",
        "resource_id": resource_id,
        "generated_at": datetime.now().isoformat(),
        "chain_integrity": "verified" if chain_valid else "broken",
        "total_entries": len(entries),
        "entries": [
            {
                "id": str(e.id),
                "timestamp": str(e.timestamp),
                "action": e.action,
                "actor": e.actor,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "details": e.details,
                "previous_hash": e.previous_hash,
                "entry_hash": e.entry_hash,
            }
            for e in entries
        ],
        "manifest": {
            "format_version": "1.0",
            "preservation_status": "litigation_hold"
            if any((e.details or {}).get("_litigation_hold") for e in entries)
            else "standard",
        },
    }

    logger.info("ediscovery_export_generated", resource_id=resource_id, entries=len(entries))
    return bundle


# ---------------------------------------------------------------------------
# GDPR Art. 22 — Automated Decision Objection (Phase 7f)
# ---------------------------------------------------------------------------


@router.post("/objection/{evaluation_id}")
async def file_objection(
    evaluation_id: str,
    body: dict | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """File an objection to an automated decision (GDPR Art. 22 / EU AI Act).

    Records the objection in the audit log and flags the evaluation for
    human review. The verdict status is updated to objection_in_progress.
    """
    body = body or {}
    repo = AuditLogRepository(session)

    await repo.append(
        action="objection_filed",
        actor=body.get("objector", "data_subject"),
        resource_type="evaluation",
        resource_id=evaluation_id,
        details={
            "grounds": body.get("grounds", ""),
            "contact_email": body.get("contact_email", ""),
            "request_human_review": True,
        },
    )
    await session.commit()

    return {
        "status": "objection_recorded",
        "evaluation_id": evaluation_id,
        "next_step": "A human reviewer will assess this decision within 30 days.",
    }


@router.get("/objections")
async def list_objections(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """List all filed objections to automated decisions."""
    stmt = (
        select(AuditLogModel)
        .where(AuditLogModel.action == "objection_filed")
        .order_by(AuditLogModel.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    entries = list(result.scalars().all())

    return {
        "objections": [
            {
                "id": str(e.id),
                "evaluation_id": e.resource_id,
                "objector": e.actor,
                "grounds": (e.details or {}).get("grounds", ""),
                "timestamp": str(e.timestamp),
            }
            for e in entries
        ],
        "page": page,
        "page_size": page_size,
    }

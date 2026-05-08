"""REST API routes for the compliance and privacy layer.

Endpoints:

- ``DELETE /data-subjects/{subject_id}``      — right-to-erasure (GDPR Art. 17)
- ``GET    /data-subjects/{subject_id}/inventory`` — data subject inventory (GDPR Art. 15)
- ``GET    /compliance/policies``              — list approval policies
- ``POST   /compliance/policies``              — create an approval policy
- ``GET    /compliance/access-log/{resource_id}`` — read-access log
- ``GET    /compliance/encryption/status``     — CMEK status for the tenant

See CLAUDE.md section 14 and 15.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from rulerepo_server.core.logging import get_logger
from rulerepo_server.core.pii.shadow_store import ShadowStore
from rulerepo_server.services.compliance.approval_policy import (
    ApprovalPolicyEngine,
    ApprovalPolicyRule,
    ApprovalRequirement,
)
from rulerepo_server.services.compliance.cmek import CMEKService
from rulerepo_server.services.compliance.erasure import ErasureService
from rulerepo_server.services.compliance.read_access_log import ReadAccessLogger

logger = get_logger(__name__)

router = APIRouter(tags=["compliance"])

# ---------------------------------------------------------------------------
# Service singletons (wired at import time for development; production
# replaces these via dependency injection).
# ---------------------------------------------------------------------------

_shadow_store = ShadowStore()
_erasure_service = ErasureService(shadow_store=_shadow_store)
_approval_engine = ApprovalPolicyEngine()
_cmek_service = CMEKService()
_access_logger = ReadAccessLogger()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ApprovalRequirementSchema(BaseModel):
    """Schema for a single approval requirement."""

    role: str = Field(..., description="Role required to approve")
    count: int = Field(1, ge=1, description="Number of approvals needed from this role")
    sla_hours: int | None = Field(None, ge=1, description="SLA deadline in hours")


class ApprovalPolicyCreateRequest(BaseModel):
    """Request body for creating an approval policy."""

    match_conditions: dict[str, Any] = Field(
        ...,
        description="Conditions to match (e.g. classification, severity)",
    )
    requirements: list[ApprovalRequirementSchema] = Field(
        ...,
        min_length=1,
        description="Approval requirements to impose when matched",
    )
    mandatory_consultation: list[str] | None = Field(
        None,
        description="Roles to consult (notify) without blocking",
    )


class ApprovalPolicyResponse(BaseModel):
    """Response schema for an approval policy."""

    match_conditions: dict[str, Any]
    requirements: list[ApprovalRequirementSchema]
    mandatory_consultation: list[str] | None = None


class ErasureResponse(BaseModel):
    """Response schema for a right-to-erasure operation."""

    subject_id: str
    records_affected: int
    shadow_entries_deleted: int
    timestamp: str


class DataSubjectInventoryResponse(BaseModel):
    """Response schema for a data subject inventory."""

    subject_id: str
    evaluations: list[dict[str, Any]]
    rules_authored: list[str]
    audit_entries: list[dict[str, Any]]
    shadow_entries: int
    generated_at: str


class AccessLogEntryResponse(BaseModel):
    """Response schema for a single access log entry."""

    principal_id: str
    resource_type: str
    resource_id: str
    classification: str
    accessed_at: str
    tenant_id: str
    action: str = "read"


class EncryptionStatusResponse(BaseModel):
    """Response schema for CMEK encryption status."""

    key_id: str
    provider: str
    created_at: str
    last_rotated_at: str
    tenant_id: str


# ---------------------------------------------------------------------------
# Data subject endpoints
# ---------------------------------------------------------------------------


@router.delete("/data-subjects/{subject_id}")
async def erase_data_subject(
    subject_id: str,
    tenant_id: str = Query(default="default", description="Tenant identifier"),
) -> ErasureResponse:
    """Execute a right-to-erasure request for a data subject (GDPR Art. 17).

    Deletes all PII from the shadow store and replaces identifiers in
    evaluation records with tombstone markers.  The audit chain integrity
    is preserved.
    """
    logger.info("erasure_request_received", subject_id=subject_id, tenant_id=tenant_id)

    report = await _erasure_service.erase_data_subject(
        subject_id=subject_id,
        tenant_id=tenant_id,
    )

    return ErasureResponse(
        subject_id=report.subject_id,
        records_affected=report.records_affected,
        shadow_entries_deleted=report.shadow_entries_deleted,
        timestamp=report.timestamp.isoformat(),
    )


@router.get("/data-subjects/{subject_id}/inventory")
async def get_data_subject_inventory(
    subject_id: str,
    tenant_id: str = Query(default="default", description="Tenant identifier"),
) -> DataSubjectInventoryResponse:
    """List all data held about a data subject (GDPR Art. 15 access request).

    Returns an inventory of evaluations, rules authored, and audit
    entries associated with the subject.
    """
    inventory = await _erasure_service.list_data_subject_data(
        subject_id=subject_id,
        tenant_id=tenant_id,
    )

    return DataSubjectInventoryResponse(
        subject_id=inventory.subject_id,
        evaluations=inventory.evaluations,
        rules_authored=inventory.rules_authored,
        audit_entries=inventory.audit_entries,
        shadow_entries=inventory.shadow_entries,
        generated_at=inventory.generated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Approval policy endpoints
# ---------------------------------------------------------------------------


@router.get("/compliance/policies")
async def list_approval_policies() -> dict[str, Any]:
    """List all configured approval policies."""
    policies = _approval_engine._policies
    return {
        "policies": [
            {
                "match_conditions": p.match_conditions,
                "requirements": [{"role": r.role, "count": r.count, "sla_hours": r.sla_hours} for r in p.requirements],
                "mandatory_consultation": p.mandatory_consultation,
            }
            for p in policies
        ],
        "total": len(policies),
    }


@router.post("/compliance/policies", status_code=201)
async def create_approval_policy(
    body: ApprovalPolicyCreateRequest,
) -> dict[str, Any]:
    """Create a new approval policy rule.

    The policy is added to the in-memory engine.  In production,
    policies are persisted to the database.
    """
    requirements = [
        ApprovalRequirement(
            role=r.role,
            count=r.count,
            sla_hours=r.sla_hours,
        )
        for r in body.requirements
    ]

    policy = ApprovalPolicyRule(
        match_conditions=body.match_conditions,
        requirements=requirements,
        mandatory_consultation=body.mandatory_consultation,
    )

    _approval_engine.add_policy(policy)

    logger.info(
        "approval_policy_created",
        match_conditions=body.match_conditions,
        requirement_count=len(requirements),
    )

    return {
        "status": "created",
        "policy": {
            "match_conditions": policy.match_conditions,
            "requirements": [{"role": r.role, "count": r.count, "sla_hours": r.sla_hours} for r in policy.requirements],
            "mandatory_consultation": policy.mandatory_consultation,
        },
    }


# ---------------------------------------------------------------------------
# Read-access log endpoints
# ---------------------------------------------------------------------------


@router.get("/compliance/access-log/{resource_id}")
async def get_access_log(
    resource_id: str,
    tenant_id: str = Query(default="default", description="Tenant identifier"),
    since: datetime | None = Query(default=None, description="Filter entries after this timestamp (ISO 8601)"),
) -> dict[str, Any]:
    """Retrieve the read-access log for a classified resource.

    Returns all recorded accesses, ordered most recent first.
    """
    entries = await _access_logger.get_access_log(
        resource_id=resource_id,
        tenant_id=tenant_id,
        since=since,
    )

    return {
        "resource_id": resource_id,
        "entries": [
            {
                "principal_id": e.principal_id,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "classification": e.classification,
                "accessed_at": e.accessed_at.isoformat(),
                "tenant_id": e.tenant_id,
                "action": e.action,
            }
            for e in entries
        ],
        "total": len(entries),
    }


# ---------------------------------------------------------------------------
# CMEK status endpoint
# ---------------------------------------------------------------------------


@router.get("/compliance/encryption/status")
async def get_encryption_status(
    tenant_id: str = Query(default="default", description="Tenant identifier"),
) -> EncryptionStatusResponse:
    """Return the CMEK encryption status for the tenant.

    Shows key metadata including provider, creation date, and last
    rotation date.
    """
    info = _cmek_service.get_key_info(tenant_id)

    return EncryptionStatusResponse(
        key_id=info.key_id,
        provider=info.provider,
        created_at=info.created_at.isoformat(),
        last_rotated_at=info.last_rotated_at.isoformat(),
        tenant_id=info.tenant_id,
    )

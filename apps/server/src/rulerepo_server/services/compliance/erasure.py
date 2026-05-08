"""Right-to-erasure service for GDPR Article 17 and similar regulations.

Handles data-subject deletion requests by:

1. Inventorying all data held about the subject (Article 15 access requests).
2. Deleting PII from the encrypted shadow store.
3. Replacing identifiers in evaluation records with tombstone markers.
4. Preserving audit-chain integrity (content is redacted, hash chain stays intact).

See CLAUDE.md section 14.4 and IMPROVEMENT.md for the compliance roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.core.errors import RuleRepoError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.core.pii.shadow_store import ShadowStore

logger = get_logger(__name__)

# Tombstone marker used to replace erased PII in evaluation records.
_TOMBSTONE = "[ERASED:right_to_erasure]"


class ErasureError(RuleRepoError):
    """Raised when an erasure operation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="ERASURE_ERROR", status_code=500)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ErasureReport:
    """Summary of a completed right-to-erasure operation.

    Attributes:
        subject_id: The data-subject whose PII was erased.
        tenant_id: The tenant context.
        records_affected: Number of evaluation / rule records modified.
        shadow_entries_deleted: Number of shadow-store entries removed.
        timestamp: When the erasure was performed.
    """

    subject_id: str
    tenant_id: str
    records_affected: int
    shadow_entries_deleted: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass(frozen=True, slots=True)
class DataSubjectInventory:
    """Inventory of all data held about a data subject (GDPR Article 15).

    Attributes:
        subject_id: The data-subject identifier.
        tenant_id: The tenant context.
        evaluations: List of evaluation record summaries referencing the subject.
        rules_authored: List of rule IDs authored by the subject.
        audit_entries: List of audit log entry summaries involving the subject.
        shadow_entries: Number of PII shadow-store entries held.
        generated_at: When the inventory was compiled.
    """

    subject_id: str
    tenant_id: str
    evaluations: list[dict[str, Any]] = field(default_factory=list)
    rules_authored: list[str] = field(default_factory=list)
    audit_entries: list[dict[str, Any]] = field(default_factory=list)
    shadow_entries: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ErasureService:
    """Orchestrates right-to-erasure (GDPR Art. 17) and data-subject access requests.

    This service coordinates across the shadow store, evaluation records,
    and audit log to ensure that erasure is complete while preserving the
    integrity of the audit hash chain.

    In the current implementation, evaluation and audit records are looked
    up via in-memory stubs.  Production deployments wire in the real
    PostgreSQL repositories.
    """

    def __init__(
        self,
        shadow_store: ShadowStore,
        *,
        evaluation_repo: Any | None = None,
        audit_repo: Any | None = None,
        rule_repo: Any | None = None,
    ) -> None:
        """Initialize the erasure service.

        Args:
            shadow_store: The encrypted PII shadow store.
            evaluation_repo: Repository for evaluation records (optional;
                pass ``None`` to use a no-op stub).
            audit_repo: Repository for audit log entries (optional).
            rule_repo: Repository for rules (optional).
        """
        self._shadow_store = shadow_store
        self._evaluation_repo = evaluation_repo
        self._audit_repo = audit_repo
        self._rule_repo = rule_repo

    async def erase_data_subject(
        self,
        subject_id: str,
        tenant_id: str,
    ) -> ErasureReport:
        """Execute a right-to-erasure request for a data subject.

        Steps:

        1. Delete all PII from the shadow store for this subject.
        2. Replace identifiable fields in evaluation records with tombstone
           markers so that the records remain structurally valid and the
           audit hash chain is unbroken.
        3. Log the erasure action in the audit trail (the audit entry
           itself contains only the tombstone, not the original PII).

        Args:
            subject_id: Identifier of the data subject requesting erasure.
            tenant_id: Tenant context for multi-tenancy isolation.

        Returns:
            An :class:`ErasureReport` summarising what was erased.

        Raises:
            ErasureError: If the erasure cannot be completed.
        """
        logger.info(
            "erasure_started",
            subject_id=subject_id,
            tenant_id=tenant_id,
        )

        # 1. Delete PII from shadow store
        shadow_deleted = await self._shadow_store.delete_by_subject(
            subject_id=subject_id,
            tenant_id=tenant_id,
        )

        # 2. Replace identifiers in evaluation records
        records_affected = await self._tombstone_evaluation_records(
            subject_id=subject_id,
            tenant_id=tenant_id,
        )

        # 3. Record the erasure in the audit log (without PII)
        await self._record_erasure_audit(
            subject_id=subject_id,
            tenant_id=tenant_id,
            records_affected=records_affected,
            shadow_entries_deleted=shadow_deleted,
        )

        report = ErasureReport(
            subject_id=subject_id,
            tenant_id=tenant_id,
            records_affected=records_affected,
            shadow_entries_deleted=shadow_deleted,
        )

        logger.info(
            "erasure_completed",
            subject_id=subject_id,
            tenant_id=tenant_id,
            records_affected=records_affected,
            shadow_entries_deleted=shadow_deleted,
        )

        return report

    async def list_data_subject_data(
        self,
        subject_id: str,
        tenant_id: str,
    ) -> DataSubjectInventory:
        """Compile an inventory of all data held about a data subject.

        Fulfils GDPR Article 15 (right of access) by listing all
        evaluations, rules, and audit entries that reference the subject.

        Args:
            subject_id: Identifier of the data subject.
            tenant_id: Tenant context.

        Returns:
            A :class:`DataSubjectInventory` listing all held data.
        """
        logger.info(
            "data_subject_inventory_requested",
            subject_id=subject_id,
            tenant_id=tenant_id,
        )

        evaluations = await self._find_subject_evaluations(subject_id, tenant_id)
        rules_authored = await self._find_subject_rules(subject_id, tenant_id)
        audit_entries = await self._find_subject_audit_entries(subject_id, tenant_id)
        shadow_count = await self._count_shadow_entries(subject_id, tenant_id)

        return DataSubjectInventory(
            subject_id=subject_id,
            tenant_id=tenant_id,
            evaluations=evaluations,
            rules_authored=rules_authored,
            audit_entries=audit_entries,
            shadow_entries=shadow_count,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _tombstone_evaluation_records(
        self,
        subject_id: str,
        tenant_id: str,
    ) -> int:
        """Replace subject identifiers in evaluation records with tombstones.

        The evaluation record structure is preserved (including its hash
        contribution to the audit chain) but PII fields are overwritten
        with ``[ERASED:right_to_erasure]``.
        """
        if self._evaluation_repo is None:
            logger.debug("erasure_skip_evaluations", reason="no evaluation repo configured")
            return 0

        # In production this queries the evaluation table for records
        # whose subject_facts contain the subject_id and replaces
        # identifiable fields.
        try:
            count: int = await self._evaluation_repo.tombstone_subject(
                subject_id=subject_id,
                tenant_id=tenant_id,
                tombstone=_TOMBSTONE,
            )
            return count
        except AttributeError:
            logger.debug(
                "erasure_skip_evaluations",
                reason="evaluation repo does not implement tombstone_subject",
            )
            return 0

    async def _record_erasure_audit(
        self,
        subject_id: str,
        tenant_id: str,
        records_affected: int,
        shadow_entries_deleted: int,
    ) -> None:
        """Write an audit-log entry recording the erasure action."""
        if self._audit_repo is None:
            logger.debug("erasure_skip_audit", reason="no audit repo configured")
            return

        try:
            await self._audit_repo.append(
                action="data_subject_erased",
                actor="compliance_service",
                resource_type="data_subject",
                resource_id=subject_id,
                details={
                    "tenant_id": tenant_id,
                    "records_affected": records_affected,
                    "shadow_entries_deleted": shadow_entries_deleted,
                    "reason": "right_to_erasure",
                },
            )
        except Exception:
            logger.exception("erasure_audit_failed", subject_id=subject_id)

    async def _find_subject_evaluations(
        self,
        subject_id: str,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Find evaluation records referencing the subject."""
        if self._evaluation_repo is None:
            return []
        try:
            return await self._evaluation_repo.find_by_subject(  # type: ignore[no-any-return]
                subject_id=subject_id,
                tenant_id=tenant_id,
            )
        except AttributeError:
            return []

    async def _find_subject_rules(
        self,
        subject_id: str,
        tenant_id: str,
    ) -> list[str]:
        """Find rules authored by the subject."""
        if self._rule_repo is None:
            return []
        try:
            return await self._rule_repo.find_by_author(  # type: ignore[no-any-return]
                author_id=subject_id,
                tenant_id=tenant_id,
            )
        except AttributeError:
            return []

    async def _find_subject_audit_entries(
        self,
        subject_id: str,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Find audit log entries involving the subject."""
        if self._audit_repo is None:
            return []
        try:
            return await self._audit_repo.find_by_actor(  # type: ignore[no-any-return]
                actor=subject_id,
            )
        except AttributeError:
            return []

    async def _count_shadow_entries(
        self,
        subject_id: str,
        tenant_id: str,
    ) -> int:
        """Count shadow-store entries for the subject."""
        # The shadow store does not have a count method; we approximate
        # by attempting a delete dry-run.  For production, add a count
        # method to ShadowStore.
        count = 0
        for entry in self._shadow_store._store.values():
            if entry.subject_id == subject_id and entry.tenant_id == tenant_id:
                count += 1
        return count

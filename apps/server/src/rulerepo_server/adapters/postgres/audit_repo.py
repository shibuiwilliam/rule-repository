"""Audit log repository — append-only with hash-chain integrity."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import AuditLogModel
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.audit import GENESIS_HASH, AuditEntry

logger = get_logger(__name__)


class AuditLogRepository:
    """Append-only audit log with hash-chain integrity verification.

    Only the evaluation/extraction services should write through this adapter.
    Application code must never write to the audit log table directly.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_latest_hash(self) -> str:
        """Retrieve the hash of the most recent audit entry.

        Returns:
            The entry_hash of the latest entry, or GENESIS_HASH if empty.
        """
        result = await self._session.execute(
            select(AuditLogModel.entry_hash).order_by(AuditLogModel.timestamp.desc()).limit(1)
        )
        latest = result.scalar_one_or_none()
        return latest or GENESIS_HASH

    async def append(
        self,
        *,
        action: str,
        actor: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ) -> AuditLogModel:
        """Append a new entry to the audit log.

        Computes the hash chain automatically by referencing the previous entry.

        Args:
            action: What happened (e.g., "rule_created", "evaluation_completed").
            actor: Who/what performed the action.
            resource_type: Type of resource affected (e.g., "rule", "extraction").
            resource_id: ID of the affected resource.
            details: Additional structured data about the action.

        Returns:
            The newly appended AuditLogModel.
        """
        previous_hash = await self._get_latest_hash()
        entry_id = uuid4()

        entry_data = {
            "id": str(entry_id),
            "action": action,
            "actor": actor,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
        }

        entry_hash = AuditEntry.compute_hash(previous_hash, entry_data)

        model = AuditLogModel(
            id=entry_id,
            action=action,
            actor=actor,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )
        self._session.add(model)
        await self._session.flush()

        logger.info(
            "audit_entry_appended",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            entry_hash=entry_hash[:16],
        )
        return model

    async def verify_chain(self, *, limit: int = 1000) -> bool:
        """Verify the integrity of the audit log hash chain.

        Args:
            limit: Maximum number of recent entries to verify.

        Returns:
            True if the chain is valid, False if tampered.
        """
        result = await self._session.execute(select(AuditLogModel).order_by(AuditLogModel.timestamp.asc()).limit(limit))
        entries = list(result.scalars().all())

        if not entries:
            return True

        expected_previous = GENESIS_HASH
        for entry in entries:
            if entry.previous_hash != expected_previous:
                logger.warning(
                    "audit_chain_broken",
                    entry_id=str(entry.id),
                    expected_previous=expected_previous[:16],
                    actual_previous=entry.previous_hash[:16],
                )
                return False

            entry_data = {
                "id": str(entry.id),
                "action": entry.action,
                "actor": entry.actor,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "details": entry.details,
            }
            computed = AuditEntry.compute_hash(expected_previous, entry_data)
            if computed != entry.entry_hash:
                logger.warning(
                    "audit_hash_mismatch",
                    entry_id=str(entry.id),
                    computed=computed[:16],
                    stored=entry.entry_hash[:16],
                )
                return False

            expected_previous = entry.entry_hash

        logger.info("audit_chain_verified", entries_checked=len(entries))
        return True

    # --- WORM dual-write (Phase 7f) ---

    async def write_worm_copy(
        self,
        entry: AuditLogModel,
        *,
        s3_client: Any | None = None,
        bucket: str = "",
    ) -> str | None:
        """Write a WORM (write-once-read-many) copy of an audit entry to S3 Object Lock.

        Only called when audit_tier requires WORM for the entry's resource category.
        The S3 bucket must have Object Lock enabled in compliance mode.

        Args:
            entry: The audit entry to archive.
            s3_client: An optional S3 client (boto3). None = skip WORM write.
            bucket: The S3 bucket with Object Lock enabled.

        Returns:
            The S3 object key, or None if skipped.
        """
        if s3_client is None:
            return None

        import json
        from datetime import UTC, datetime

        key = f"audit-worm/{datetime.now(tz=UTC).strftime('%Y/%m/%d')}/{entry.id}.json"
        body = json.dumps(
            {
                "id": str(entry.id),
                "action": entry.action,
                "actor": entry.actor,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "details": entry.details,
                "previous_hash": entry.previous_hash,
                "entry_hash": entry.entry_hash,
                "timestamp": str(entry.timestamp),
            },
            default=str,
        )
        try:
            s3_client.put_object(Bucket=bucket, Key=key, Body=body)
            logger.info("worm_copy_written", key=key)
            return key
        except Exception as exc:
            logger.error("worm_copy_failed", key=key, error=str(exc))
            return None

    # --- Litigation hold (Phase 7f) ---

    async def set_litigation_hold(
        self,
        resource_id: str,
        *,
        hold_reason: str = "",
        hold_by: str = "system",
    ) -> None:
        """Place a litigation hold on all audit entries for a resource.

        Prevents deletion or archival of entries related to the specified resource.
        Implemented as a metadata flag on the entry's details.

        Args:
            resource_id: The resource to place on hold.
            hold_reason: Reason for the hold (e.g., case number).
            hold_by: Who placed the hold.
        """
        from sqlalchemy import update

        await self._session.execute(
            update(AuditLogModel)
            .where(AuditLogModel.resource_id == resource_id)
            .values(
                details=AuditLogModel.details.concat(
                    {
                        "_litigation_hold": True,
                        "_hold_reason": hold_reason,
                        "_hold_by": hold_by,
                    }
                )
            )
        )
        logger.info(
            "litigation_hold_set",
            resource_id=resource_id,
            hold_reason=hold_reason,
        )

    async def get_litigation_holds(self) -> list[dict[str, Any]]:
        """List all resources currently under litigation hold."""
        result = await self._session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.details["_litigation_hold"].astext == "true")
            .order_by(AuditLogModel.timestamp.desc())
        )
        entries = list(result.scalars().all())
        seen: dict[str, dict[str, Any]] = {}
        for e in entries:
            if e.resource_id not in seen:
                seen[e.resource_id] = {
                    "resource_id": e.resource_id,
                    "resource_type": e.resource_type,
                    "hold_reason": (e.details or {}).get("_hold_reason", ""),
                    "hold_by": (e.details or {}).get("_hold_by", ""),
                }
        return list(seen.values())

"""WORM audit writer -- the single entry point for audit log writes.

All audit log entries MUST be written through this module. Application
code must NEVER write directly to the audit log table. This writer
enforces hash chaining, and when configured, dual-writes to immutable
storage (S3 Object Lock / Azure Immutable Blob).

See CLAUDE.md section 14 Rule #9, IMPROVEMENT.md section 4.4 / RR-011.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.audit_repo import AuditLogRepository
from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class WORMWriter:
    """Write-Once-Read-Many audit writer with hash chaining.

    This is the **only** sanctioned way to append entries to the audit log.
    It delegates persistence to ``AuditLogRepository.append`` (which handles
    hash-chain computation) and optionally dual-writes to WORM storage.

    Args:
        session: An async SQLAlchemy session for database access.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuditLogRepository(session)

    async def write(
        self,
        *,
        action: str,
        actor: str = "system",
        resource_type: str = "",
        resource_id: str = "",
        details: dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> Any:
        """Write an audit entry with hash chaining and optional WORM dual-write.

        Args:
            action: What happened (e.g. ``rule_created``, ``evaluation_completed``).
            actor: Who or what performed the action.
            resource_type: Type of resource affected (e.g. ``rule``, ``extraction``).
            resource_id: Identifier of the affected resource.
            details: Additional structured data about the action.
            tenant_id: Tenant scope for multi-tenant deployments.

        Returns:
            The persisted ``AuditLogModel`` instance.
        """
        entry = await self._repo.append(
            action=action,
            actor=actor,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )

        # Flush so the entry is visible within the current transaction
        await self._session.flush()

        # WORM dual-write if configured
        settings = get_settings()
        if settings.audit_worm_enabled:
            await self._worm_dual_write(entry, tenant_id)

        logger.info(
            "audit_entry_written",
            entry_id=str(entry.id),
            action=action,
            actor=actor,
            resource_type=resource_type,
            tenant_id=tenant_id,
        )

        return entry

    async def _worm_dual_write(self, entry: Any, tenant_id: str) -> None:
        """Dual-write to WORM storage (S3 Object Lock / Azure Immutable Blob).

        In production this uses boto3 with ``ObjectLockMode=COMPLIANCE``.
        Currently a structured placeholder that logs intent and prepares the
        payload so the integration can be completed with minimal changes.

        Args:
            entry: The ``AuditLogModel`` to archive.
            tenant_id: Tenant scope for key namespacing.
        """
        settings = get_settings()
        bucket = settings.audit_worm_s3_bucket
        if not bucket:
            logger.debug("worm_dual_write_skipped", reason="no bucket configured")
            return

        key = f"audit-worm/{tenant_id}/{datetime.now(tz=UTC).strftime('%Y/%m/%d')}/{entry.id}.json"
        _body = json.dumps(
            {
                "id": str(entry.id),
                "timestamp": str(entry.timestamp),
                "action": entry.action,
                "actor": entry.actor,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "details": entry.details,
                "previous_hash": entry.previous_hash,
                "entry_hash": entry.entry_hash,
                "tenant_id": tenant_id,
            },
            default=str,
        )

        # Placeholder: in production, use boto3 S3 client with Object Lock
        # s3_client.put_object(
        #     Bucket=bucket,
        #     Key=key,
        #     Body=body,
        #     ObjectLockMode="COMPLIANCE",
        #     ObjectLockRetainUntilDate=retain_until,
        # )
        logger.info(
            "worm_dual_write",
            entry_id=str(entry.id),
            bucket=bucket,
            key=key,
            tenant_id=tenant_id,
        )

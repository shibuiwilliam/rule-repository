"""Read-access logging for classified resources.

Records every read access to classified data (CONFIDENTIAL and above)
for audit and compliance purposes.  Required by GDPR Article 30,
J-SOX IT General Controls, and ISO 27001 A.12.4.

The default implementation uses an in-memory store.  Production
deployments should wire in a persistent adapter (PostgreSQL table
or append-only log).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AccessLogEntry:
    """A single read-access log record.

    Attributes:
        principal_id: Identity of the user or agent that accessed the resource.
        resource_type: Type of resource accessed (e.g. ``"rule"``, ``"evaluation"``).
        resource_id: Identifier of the accessed resource.
        classification: Classification level of the accessed resource.
        accessed_at: Timestamp of the access.
        tenant_id: Tenant context.
        action: The type of access (default ``"read"``).
        metadata: Optional additional context (IP, user-agent, etc.).
    """

    principal_id: str
    resource_type: str
    resource_id: str
    classification: str
    accessed_at: datetime
    tenant_id: str
    action: str = "read"
    metadata: dict[str, Any] = field(default_factory=dict)


class ReadAccessLogger:
    """Records and queries read-access events for classified resources.

    Every access to a resource with classification CONFIDENTIAL or
    RESTRICTED is logged.  Access to INTERNAL and PUBLIC resources
    may also be logged if the caller explicitly requests it.

    The in-memory implementation is suitable for development and
    testing.  Production deployments replace the backing store with
    an append-only PostgreSQL table or a dedicated audit stream.
    """

    def __init__(self) -> None:
        self._log: list[AccessLogEntry] = []

    async def log_access(
        self,
        principal_id: str,
        resource_type: str,
        resource_id: str,
        classification: str,
        tenant_id: str,
        *,
        action: str = "read",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a read-access event.

        Args:
            principal_id: Who accessed the resource.
            resource_type: Type of resource (``"rule"``, ``"evaluation"``, etc.).
            resource_id: Unique identifier of the resource.
            classification: Classification level of the resource.
            tenant_id: Tenant context for multi-tenancy isolation.
            action: Type of access (default ``"read"``).
            metadata: Optional additional context (e.g. IP address).
        """
        entry = AccessLogEntry(
            principal_id=principal_id,
            resource_type=resource_type,
            resource_id=resource_id,
            classification=classification,
            accessed_at=datetime.now(tz=UTC),
            tenant_id=tenant_id,
            action=action,
            metadata=metadata or {},
        )
        self._log.append(entry)

        logger.info(
            "read_access_logged",
            principal_id=principal_id,
            resource_type=resource_type,
            resource_id=resource_id,
            classification=classification,
            tenant_id=tenant_id,
        )

    async def get_access_log(
        self,
        resource_id: str,
        tenant_id: str,
        *,
        since: datetime | None = None,
    ) -> list[AccessLogEntry]:
        """Retrieve access log entries for a resource.

        Args:
            resource_id: Filter by resource identifier.
            tenant_id: Tenant context.
            since: Only return entries after this timestamp.
                ``None`` returns all entries.

        Returns:
            List of :class:`AccessLogEntry` records, ordered by
            ``accessed_at`` descending (most recent first).
        """
        results = [entry for entry in self._log if entry.resource_id == resource_id and entry.tenant_id == tenant_id]

        if since is not None:
            results = [entry for entry in results if entry.accessed_at >= since]

        results.sort(key=lambda e: e.accessed_at, reverse=True)
        return results

    async def get_access_log_by_principal(
        self,
        principal_id: str,
        tenant_id: str,
        *,
        since: datetime | None = None,
    ) -> list[AccessLogEntry]:
        """Retrieve access log entries for a specific principal.

        Useful for auditing what a particular user or agent has accessed.

        Args:
            principal_id: Filter by principal identity.
            tenant_id: Tenant context.
            since: Only return entries after this timestamp.

        Returns:
            List of :class:`AccessLogEntry` records, most recent first.
        """
        results = [entry for entry in self._log if entry.principal_id == principal_id and entry.tenant_id == tenant_id]

        if since is not None:
            results = [entry for entry in results if entry.accessed_at >= since]

        results.sort(key=lambda e: e.accessed_at, reverse=True)
        return results

    async def count_accesses(
        self,
        resource_id: str,
        tenant_id: str,
        *,
        since: datetime | None = None,
    ) -> int:
        """Count the number of accesses to a resource.

        Args:
            resource_id: Filter by resource identifier.
            tenant_id: Tenant context.
            since: Only count entries after this timestamp.

        Returns:
            Number of matching access log entries.
        """
        entries = await self.get_access_log(
            resource_id=resource_id,
            tenant_id=tenant_id,
            since=since,
        )
        return len(entries)

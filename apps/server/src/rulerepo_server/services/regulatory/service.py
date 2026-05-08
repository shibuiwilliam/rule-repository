"""Regulatory source management and amendment propagation.

Tracks external regulatory sources and propagates amendments to
downstream rules that derive from them.

See IMPROVEMENT.md §3.2 / RR-012.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.regulatory import (
    AmendmentStatus,
    RegulatoryAmendment,
    RegulatorySource,
    SourceType,
)

logger = get_logger(__name__)


class RegulatoryService:
    """Manages regulatory sources, amendments, and rule propagation."""

    def __init__(self) -> None:
        self._sources: dict[str, RegulatorySource] = {}
        self._amendments: dict[str, RegulatoryAmendment] = {}
        self._source_rule_links: dict[str, list[str]] = {}

    async def create_source(
        self,
        *,
        jurisdiction: str,
        authority: str,
        citation: str,
        title: str,
        source_type: str = "law",
        effective_date: str | None = None,
        source_url: str = "",
        feed_id: str = "",
        tenant_id: str = "default",
    ) -> RegulatorySource:
        """Register a new regulatory source."""
        source = RegulatorySource(
            id=uuid4(),
            jurisdiction=jurisdiction,
            authority=authority,
            citation=citation,
            title=title,
            source_type=SourceType(source_type),
            effective_date=(datetime.fromisoformat(effective_date) if effective_date else None),
            source_url=source_url,
            feed_id=feed_id,
            tenant_id=tenant_id,
        )
        self._sources[str(source.id)] = source
        logger.info(
            "regulatory_source_created",
            source_id=str(source.id),
            citation=citation,
            jurisdiction=jurisdiction,
        )
        return source

    async def get_source(self, source_id: UUID) -> RegulatorySource:
        """Get a regulatory source by ID."""
        key = str(source_id)
        if key not in self._sources:
            from rulerepo_server.core.errors import NotFoundError

            raise NotFoundError(f"Regulatory source {source_id} not found")
        return self._sources[key]

    async def list_sources(
        self,
        *,
        tenant_id: str = "default",
        jurisdiction: str | None = None,
        source_type: str | None = None,
    ) -> list[RegulatorySource]:
        """List regulatory sources with optional filters."""
        results = [s for s in self._sources.values() if s.tenant_id == tenant_id]
        if jurisdiction:
            results = [s for s in results if s.jurisdiction == jurisdiction]
        if source_type:
            results = [s for s in results if s.source_type.value == source_type]
        return sorted(results, key=lambda s: s.created_at, reverse=True)

    async def link_rule(self, source_id: UUID, rule_id: UUID) -> None:
        """Link a rule to a regulatory source (DERIVES_FROM)."""
        key = str(source_id)
        if key not in self._source_rule_links:
            self._source_rule_links[key] = []
        rule_key = str(rule_id)
        if rule_key not in self._source_rule_links[key]:
            self._source_rule_links[key].append(rule_key)
        logger.info(
            "rule_linked_to_source",
            source_id=key,
            rule_id=rule_key,
        )

    async def get_derived_rules(self, source_id: UUID) -> list[str]:
        """Get all rule IDs that derive from a regulatory source."""
        return self._source_rule_links.get(str(source_id), [])

    async def record_amendment(
        self,
        *,
        source_id: UUID,
        summary: str,
        amendment_date: str | None = None,
        diff_url: str = "",
    ) -> RegulatoryAmendment:
        """Record an amendment to a regulatory source.

        Automatically identifies affected rules and marks them for
        review via the propagator.
        """
        affected = await self.get_derived_rules(source_id)

        amendment = RegulatoryAmendment(
            id=uuid4(),
            source_id=source_id,
            summary=summary,
            amendment_date=(datetime.fromisoformat(amendment_date) if amendment_date else datetime.now(tz=UTC)),
            diff_url=diff_url,
            status=AmendmentStatus.DETECTED,
            affected_rule_ids=affected,
        )
        self._amendments[str(amendment.id)] = amendment

        logger.warning(
            "regulatory_amendment_detected",
            source_id=str(source_id),
            amendment_id=str(amendment.id),
            affected_rules=len(affected),
            summary=summary[:200],
        )
        return amendment

    async def propagate_amendment(self, amendment_id: UUID) -> dict[str, Any]:
        """Propagate an amendment — mark affected rules as needs_review.

        In production, this would update rule status in the database
        and send notifications to rule owners.
        """
        key = str(amendment_id)
        if key not in self._amendments:
            from rulerepo_server.core.errors import NotFoundError

            raise NotFoundError(f"Amendment {amendment_id} not found")

        amendment = self._amendments[key]
        amendment = RegulatoryAmendment(
            id=amendment.id,
            source_id=amendment.source_id,
            summary=amendment.summary,
            amendment_date=amendment.amendment_date,
            diff_url=amendment.diff_url,
            status=AmendmentStatus.PROPAGATED,
            affected_rule_ids=amendment.affected_rule_ids,
            created_at=amendment.created_at,
        )
        self._amendments[key] = amendment

        logger.info(
            "amendment_propagated",
            amendment_id=key,
            rules_marked=len(amendment.affected_rule_ids),
        )

        return {
            "amendment_id": key,
            "status": "propagated",
            "rules_marked_for_review": amendment.affected_rule_ids,
            "count": len(amendment.affected_rule_ids),
        }

    async def list_amendments(
        self,
        *,
        source_id: UUID | None = None,
        status: str | None = None,
    ) -> list[RegulatoryAmendment]:
        """List amendments with optional filters."""
        results = list(self._amendments.values())
        if source_id:
            results = [a for a in results if a.source_id == source_id]
        if status:
            results = [a for a in results if a.status.value == status]
        return sorted(results, key=lambda a: a.created_at, reverse=True)

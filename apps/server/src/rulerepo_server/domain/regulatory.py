"""Regulatory Source domain model — external laws, regulations, and standards.

A ``RegulatorySource`` represents an authoritative external document
(law, regulation, standard) from which internal rules derive.  When the
source is amended, the ``propagator`` marks all descendant rules as
``needs_review``.

See IMPROVEMENT.md §3.2 / RR-012.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


class SourceType(str, enum.Enum):
    """Type of regulatory source."""

    LAW = "law"
    REGULATION = "regulation"
    STANDARD = "standard"
    GUIDELINE = "guideline"
    DIRECTIVE = "directive"


class AmendmentStatus(str, enum.Enum):
    """Status of an amendment notification."""

    DETECTED = "detected"
    REVIEWED = "reviewed"
    PROPAGATED = "propagated"
    DISMISSED = "dismissed"


@dataclass
class RegulatorySource:
    """An external authoritative source (law, regulation, standard).

    Attributes:
        id: Unique identifier.
        jurisdiction: Country/region code (e.g., ``JP``, ``US``, ``EU``).
        authority: Issuing authority (e.g., ``MHLW``, ``SEC``, ``EU Commission``).
        citation: Official citation string.
        title: Human-readable title.
        source_type: Type of source document.
        effective_date: When the source takes effect.
        source_url: URL to the authoritative text.
        feed_id: Identifier of the feed that discovered this source.
        tenant_id: Owning tenant.
    """

    id: UUID = field(default_factory=uuid4)
    jurisdiction: str = ""
    authority: str = ""
    citation: str = ""
    title: str = ""
    source_type: SourceType = SourceType.LAW
    effective_date: datetime | None = None
    source_url: str = ""
    feed_id: str = ""
    tenant_id: str = "default"
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass
class RegulatoryAmendment:
    """A detected change to a regulatory source.

    When an upstream source is amended, this record triggers the
    propagator to mark descendant rules as ``needs_review``.
    """

    id: UUID = field(default_factory=uuid4)
    source_id: UUID = field(default_factory=uuid4)
    summary: str = ""
    amendment_date: datetime | None = None
    diff_url: str = ""
    status: AmendmentStatus = AmendmentStatus.DETECTED
    affected_rule_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

"""Attestation domain model -- campaigns, responses, and completion tracking.

See IMPROVEMENT.md RR-014.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


class CampaignStatus(str, enum.Enum):
    """Lifecycle status of an attestation campaign."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class ResponseStatus(str, enum.Enum):
    """Status of a single user's attestation response."""

    PENDING = "PENDING"
    ATTESTED = "ATTESTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"


@dataclass
class AttestationCampaign:
    """A campaign requiring users to attest to understanding specific rules."""

    id: UUID = field(default_factory=uuid4)
    tenant_id: str = "default"
    title: str = ""
    description: str = ""
    rule_ids: list[str] = field(default_factory=list)
    target_users: list[str] = field(default_factory=list)
    target_departments: list[str] = field(default_factory=list)
    status: CampaignStatus = CampaignStatus.DRAFT
    due_date: datetime | None = None
    reminder_interval_days: int = 7
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass
class AttestationResponse:
    """A single user's response to an attestation campaign."""

    id: UUID = field(default_factory=uuid4)
    campaign_id: UUID = field(default_factory=uuid4)
    user_id: str = ""
    status: ResponseStatus = ResponseStatus.PENDING
    attested_at: datetime | None = None
    declined_reason: str = ""
    ip_address: str = ""
    user_agent: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass
class CampaignProgress:
    """Aggregate progress for a campaign."""

    campaign_id: UUID = field(default_factory=uuid4)
    total_users: int = 0
    attested: int = 0
    declined: int = 0
    pending: int = 0
    expired: int = 0
    completion_rate: float = 0.0

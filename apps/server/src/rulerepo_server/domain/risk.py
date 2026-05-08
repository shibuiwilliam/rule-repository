"""Risk Register domain model -- risks and rule-to-risk mappings.

Every rule (control) is justified by the risk it mitigates. The Risk
entity enables the system to answer auditor questions like:
- "Which controls cover risk R-12?"
- "What is our SOX/J-SOX/HIPAA coverage?"

See IMPROVEMENT.md RR-019.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


class RiskLikelihood(str, enum.Enum):
    """Qualitative likelihood of a risk event occurring."""

    RARE = "RARE"
    UNLIKELY = "UNLIKELY"
    POSSIBLE = "POSSIBLE"
    LIKELY = "LIKELY"
    ALMOST_CERTAIN = "ALMOST_CERTAIN"


class RiskImpact(str, enum.Enum):
    """Qualitative impact severity if the risk materializes."""

    NEGLIGIBLE = "NEGLIGIBLE"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    CATASTROPHIC = "CATASTROPHIC"


class RiskStatus(str, enum.Enum):
    """Lifecycle status of a risk entry."""

    IDENTIFIED = "IDENTIFIED"
    ASSESSED = "ASSESSED"
    MITIGATED = "MITIGATED"
    ACCEPTED = "ACCEPTED"
    CLOSED = "CLOSED"


@dataclass
class Risk:
    """A single risk in the Risk Register."""

    id: UUID = field(default_factory=uuid4)
    tenant_id: str = "default"
    title: str = ""
    description: str = ""
    likelihood: RiskLikelihood = RiskLikelihood.POSSIBLE
    impact: RiskImpact = RiskImpact.MODERATE
    status: RiskStatus = RiskStatus.IDENTIFIED
    owner: str = ""
    category: str = ""  # e.g., "operational", "financial", "compliance", "strategic"
    framework_refs: list[str] = field(default_factory=list)  # e.g., ["ISO 27001 A.8", "SOX 404"]
    inherent_score: float = 0.0  # likelihood x impact before controls
    residual_score: float = 0.0  # after controls applied
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass
class RiskRuleMapping:
    """Links a risk to the rules (controls) that mitigate it."""

    risk_id: UUID = field(default_factory=uuid4)
    rule_id: UUID = field(default_factory=uuid4)
    mitigation_strength: str = "partial"  # full, partial, minimal
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

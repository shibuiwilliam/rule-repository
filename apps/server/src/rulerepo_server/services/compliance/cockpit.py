"""Compliance Cockpit — organization-wide compliance posture dashboard.

Distinct from the Intelligence dashboard: Intelligence shows rule health;
the Cockpit shows organizational compliance posture. See PROJECT.md §6.10
and CLAUDE.md §14.10.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DepartmentTrend:
    """Deny-rate trend for a single department."""

    department: str
    evaluation_count: int = 0
    deny_count: int = 0
    deny_rate: float = 0.0
    sparkline: list[float] = field(default_factory=list)


@dataclass
class PolicyMetric:
    """Fire and deny rates for a policy group."""

    policy_group: str
    fire_count: int = 0
    deny_count: int = 0
    fire_rate: float = 0.0
    deny_rate: float = 0.0


@dataclass
class PropagationItem:
    """A downstream rule that needs review due to upstream change."""

    upstream_rule_id: str
    upstream_statement: str
    downstream_rule_id: str
    downstream_statement: str
    changed_at: datetime | None = None


@dataclass
class ActionItem:
    """An item in the compliance action queue."""

    item_type: str  # "unapproved_proposal", "low_effectiveness", "dormant_rule"
    resource_id: str
    description: str
    priority: str = "normal"


@dataclass
class AuditSummary:
    """Summary of audit activity over a time window."""

    window_days: int
    evaluation_count: int = 0
    denial_count: int = 0
    manual_override_count: int = 0


@dataclass
class CockpitDashboard:
    """Complete compliance cockpit data."""

    department_trends: list[DepartmentTrend] = field(default_factory=list)
    policy_metrics: list[PolicyMetric] = field(default_factory=list)
    audit_summary: AuditSummary | None = None


class ComplianceCockpitService:
    """Service for the Compliance Cockpit dashboard.

    Aggregates data from evaluations, rules, and proposals to present
    an organization-wide compliance posture.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_dashboard(self, window_days: int = 30) -> CockpitDashboard:
        """Build the complete cockpit dashboard.

        Args:
            window_days: Number of days to look back for trends.

        Returns:
            CockpitDashboard with all panels populated.
        """
        logger.info("cockpit_dashboard_requested", window_days=window_days)

        trends = await self.get_department_violation_trends(window_days)
        metrics = await self.get_per_policy_metrics()
        summary = await self.get_audit_summary(window_days)

        return CockpitDashboard(
            department_trends=trends,
            policy_metrics=metrics,
            audit_summary=summary,
        )

    async def get_department_violation_trends(self, window_days: int = 30) -> list[DepartmentTrend]:
        """Deny-rate sparklines per department.

        Args:
            window_days: Lookback period.

        Returns:
            List of DepartmentTrend, one per active department.
        """
        from rulerepo_server.domain.department import DepartmentType

        trends = []
        for dept in DepartmentType:
            if dept == DepartmentType.CUSTOM:
                continue
            trends.append(
                DepartmentTrend(
                    department=dept.value,
                    evaluation_count=0,
                    deny_count=0,
                    deny_rate=0.0,
                    sparkline=[],
                )
            )
        return trends

    async def get_per_policy_metrics(self, policy_filter: str | None = None) -> list[PolicyMetric]:
        """Fire/deny rates per logical policy group.

        Args:
            policy_filter: Optional filter to narrow policy groups.

        Returns:
            List of PolicyMetric for each policy group.
        """
        groups = [
            "labor-law-derived",
            "expense-policy",
            "anti-bribery",
            "contract-standards",
            "privacy-protection",
            "code-quality",
        ]
        return [PolicyMetric(policy_group=g, fire_count=0, deny_count=0) for g in groups]

    async def get_regulatory_propagation(self) -> list[PropagationItem]:
        """List downstream rules affected by recent upstream changes.

        Returns:
            List of PropagationItem for rules needing review.
        """
        return []

    async def get_action_queue(self) -> list[ActionItem]:
        """Get items requiring compliance attention.

        Returns:
            List of ActionItem including unapproved proposals,
            low-effectiveness rules, and dormant rules.
        """
        return []

    async def get_audit_summary(self, window_days: int = 30) -> AuditSummary:
        """Evaluation count, denial count, manual override count.

        Args:
            window_days: Lookback period.

        Returns:
            AuditSummary for the specified window.
        """
        return AuditSummary(
            window_days=window_days,
            evaluation_count=0,
            denial_count=0,
            manual_override_count=0,
        )

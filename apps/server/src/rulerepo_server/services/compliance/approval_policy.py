"""Approval policy DSL and engine.

Defines a declarative policy language for specifying who must approve
rule changes based on the rule's attributes (domain, severity,
classification, legal force).  The engine evaluates these policies
at proposal-creation time and tracks approval progress.

Example policy rule (YAML-serializable)::

    match_conditions:
      classification: restricted
      severity: critical
    requirements:
      - role: legal_counsel
        count: 2
        sla_hours: 48
      - role: department_head
        count: 1
        sla_hours: 72
    mandatory_consultation:
      - compliance_officer

See CLAUDE.md section 13.3 for integration with the proposal workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ApprovalRequirement:
    """A single approval requirement within a policy.

    Attributes:
        role: The role required to approve (e.g. ``"legal_counsel"``).
        count: How many approvals from this role are needed.
        sla_hours: Maximum hours allowed for this approval step.
            ``None`` means no deadline.
    """

    role: str
    count: int = 1
    sla_hours: int | None = None


@dataclass(frozen=True, slots=True)
class ApprovalPolicyRule:
    """A single policy rule mapping conditions to requirements.

    Attributes:
        match_conditions: Dictionary of attribute names to required values.
            All conditions must match for the rule to apply.
        requirements: List of approval requirements to impose when matched.
        mandatory_consultation: Roles that must be consulted (notified) but
            whose approval is not blocking.  ``None`` means no consultation.
    """

    match_conditions: dict[str, Any]
    requirements: list[ApprovalRequirement]
    mandatory_consultation: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ApprovalStatus:
    """Current approval status for a rule change.

    Attributes:
        complete: Whether all required approvals have been obtained.
        pending_roles: Roles that still need to approve.
        sla_deadline: The earliest SLA deadline among pending approvals,
            or ``None`` if no deadline applies.
        approvals_received: Number of approvals already given.
        approvals_required: Total number of approvals needed.
    """

    complete: bool
    pending_roles: list[str]
    sla_deadline: datetime | None = None
    approvals_received: int = 0
    approvals_required: int = 0


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class ApprovalPolicyEngine:
    """Evaluates approval policies against rule attributes and tracks progress.

    Usage::

        engine = ApprovalPolicyEngine()
        engine.load_policies([
            ApprovalPolicyRule(
                match_conditions={"classification": "restricted"},
                requirements=[ApprovalRequirement(role="ciso", count=1, sla_hours=24)],
            ),
        ])

        reqs = engine.evaluate(
            rule_attrs={"classification": "restricted", "severity": "critical"},
            change_type="create",
        )
        # reqs == [ApprovalRequirement(role="ciso", count=1, sla_hours=24)]
    """

    def __init__(self) -> None:
        self._policies: list[ApprovalPolicyRule] = []

    def load_policies(self, policies: list[ApprovalPolicyRule]) -> None:
        """Replace the current policy set with the provided policies.

        Args:
            policies: List of approval policy rules.
        """
        self._policies = list(policies)
        logger.info("approval_policies_loaded", count=len(self._policies))

    def add_policy(self, policy: ApprovalPolicyRule) -> None:
        """Append a single policy rule.

        Args:
            policy: The policy rule to add.
        """
        self._policies.append(policy)

    def evaluate(
        self,
        rule_attrs: dict[str, Any],
        change_type: str,
    ) -> list[ApprovalRequirement]:
        """Determine the approval requirements for a rule change.

        All matching policies contribute their requirements.  Requirements
        for the same role across multiple policies are merged by taking the
        maximum count and the tightest (shortest) SLA.

        Args:
            rule_attrs: Attributes of the rule being changed.  Keys
                typically include ``classification``, ``severity``,
                ``domain``, ``legal_force``.
            change_type: The type of change (``"create"``, ``"update"``,
                ``"retire"``, ``"delete"``).

        Returns:
            De-duplicated list of approval requirements.
        """
        # Collect all requirements from matching policies
        merged: dict[str, ApprovalRequirement] = {}

        attrs_with_change = {**rule_attrs, "change_type": change_type}

        for policy in self._policies:
            if self._matches(policy.match_conditions, attrs_with_change):
                for req in policy.requirements:
                    existing = merged.get(req.role)
                    if existing is None:
                        merged[req.role] = req
                    else:
                        # Merge: max count, tightest SLA
                        merged_sla = _tightest_sla(existing.sla_hours, req.sla_hours)
                        merged[req.role] = ApprovalRequirement(
                            role=req.role,
                            count=max(existing.count, req.count),
                            sla_hours=merged_sla,
                        )

        return list(merged.values())

    def check_approval_complete(
        self,
        rule_id: str,
        approvals_given: list[dict[str, Any]],
        *,
        requirements: list[ApprovalRequirement] | None = None,
        rule_attrs: dict[str, Any] | None = None,
        change_type: str = "update",
    ) -> ApprovalStatus:
        """Check whether all required approvals have been obtained.

        Either pass pre-computed *requirements* or pass *rule_attrs* and
        *change_type* to have the engine evaluate them.

        Args:
            rule_id: The rule being approved.
            approvals_given: List of approval records.  Each must have
                at least a ``"role"`` key.
            requirements: Pre-evaluated requirements.  If ``None``,
                the engine evaluates from *rule_attrs* and *change_type*.
            rule_attrs: Rule attributes for on-the-fly evaluation.
            change_type: Change type for on-the-fly evaluation.

        Returns:
            An :class:`ApprovalStatus` summarising progress.
        """
        if requirements is None:
            if rule_attrs is None:
                return ApprovalStatus(
                    complete=True,
                    pending_roles=[],
                    approvals_received=len(approvals_given),
                    approvals_required=0,
                )
            requirements = self.evaluate(rule_attrs, change_type)

        if not requirements:
            return ApprovalStatus(
                complete=True,
                pending_roles=[],
                approvals_received=len(approvals_given),
                approvals_required=0,
            )

        # Count approvals per role
        role_counts: dict[str, int] = {}
        for approval in approvals_given:
            role = approval.get("role", "")
            if role:
                role_counts[role] = role_counts.get(role, 0) + 1

        pending_roles: list[str] = []
        total_required = 0
        total_received = 0
        earliest_deadline: datetime | None = None

        now = datetime.now(tz=UTC)

        for req in requirements:
            total_required += req.count
            given = role_counts.get(req.role, 0)
            total_received += min(given, req.count)

            if given < req.count:
                pending_roles.append(req.role)
                if req.sla_hours is not None:
                    deadline = now + timedelta(hours=req.sla_hours)
                    if earliest_deadline is None or deadline < earliest_deadline:
                        earliest_deadline = deadline

        return ApprovalStatus(
            complete=len(pending_roles) == 0,
            pending_roles=pending_roles,
            sla_deadline=earliest_deadline,
            approvals_received=total_received,
            approvals_required=total_required,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _matches(conditions: dict[str, Any], attrs: dict[str, Any]) -> bool:
        """Check whether all conditions match the given attributes.

        A condition value can be:
        - A string: exact match.
        - A list: the attribute must be in the list.
        - ``"*"``: matches any non-empty value.
        """
        for key, expected in conditions.items():
            actual = attrs.get(key)
            if actual is None:
                return False
            if expected == "*":
                continue
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True


def _tightest_sla(a: int | None, b: int | None) -> int | None:
    """Return the tighter (shorter) SLA, treating None as no constraint."""
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)

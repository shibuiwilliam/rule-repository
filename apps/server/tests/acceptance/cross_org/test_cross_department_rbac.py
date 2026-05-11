"""Acceptance test: Cross-department rule visibility.

Validates CLAUDE.md §13 rule 19: Department RBAC is non-bypassable.
Every API endpoint that returns or mutates rules must apply department
visibility.

Scenario:
    - Finance user (SUBSCRIBER in finance, no capacity in legal)
    - Can view public rules and finance rules
    - Can view but NOT edit legal rules (cross-department READ allowed)
    - Cannot edit restricted-department rules they have no capacity in
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rulerepo_server.domain.department import Capacity
from rulerepo_server.services.departments.authz import (
    can_approve,
    can_edit,
    can_view,
    reset_policies,
)


@pytest.fixture(autouse=True)
def _reset_authz_policies():
    """Ensure default policies for each test."""
    reset_policies()
    yield
    reset_policies()


class _FakeCapacityRow:
    """Mimics a CapacityAssignmentModel row for mocking."""

    def __init__(self, department_id: str, capacity: str) -> None:
        self.department_id = department_id
        self.capacity = capacity
        self.user_id = "test-user"


def _mock_session_with_assignments(assignments: list[tuple[str, str]]) -> AsyncMock:
    """Create a mock session that returns the given capacity assignments.

    The policy-based authz loads ALL of a user's assignments in one
    query (``scalars().all()``), so we mock that shape.
    """
    session = AsyncMock()

    mock_models = [_FakeCapacityRow(dept, cap) for dept, cap in assignments]

    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = mock_models
    result.scalars.return_value = scalars_mock
    session.execute.return_value = result

    return session


class TestCrossDepartmentRbac:
    """Cross-department rule visibility acceptance test."""

    async def test_public_rules_visible_to_everyone(self) -> None:
        """Rules in the 'public' pseudo-department are visible to any user."""
        session = _mock_session_with_assignments([])
        assert await can_view(session, user_id="anyone", rule_department_id="public") is True

    async def test_finance_user_cannot_edit_legal_rules(self) -> None:
        """A finance SUBSCRIBER cannot edit rules owned by legal."""
        session = _mock_session_with_assignments([("finance", "subscriber")])
        result = await can_edit(session, user_id="finance-user", rule_department_id="legal")
        assert result is False

    async def test_finance_user_can_read_legal_rules(self) -> None:
        """A finance SUBSCRIBER CAN read rules owned by legal (cross-dept READ)."""
        session = _mock_session_with_assignments([("finance", "subscriber")])
        result = await can_view(session, user_id="finance-user", rule_department_id="legal")
        assert result is True

    async def test_owner_can_edit_own_department(self) -> None:
        """An OWNER in finance can edit finance rules."""
        session = _mock_session_with_assignments([("finance", "owner")])
        result = await can_edit(session, user_id="finance-owner", rule_department_id="finance")
        assert result is True

    async def test_reviewer_can_edit_own_department(self) -> None:
        """A REVIEWER in finance can edit finance rules."""
        session = _mock_session_with_assignments([("finance", "reviewer")])
        result = await can_edit(session, user_id="finance-reviewer", rule_department_id="finance")
        assert result is True

    async def test_subscriber_cannot_edit(self) -> None:
        """A SUBSCRIBER cannot edit even in their own department."""
        session = _mock_session_with_assignments([("finance", "subscriber")])
        result = await can_edit(session, user_id="finance-sub", rule_department_id="finance")
        assert result is False

    async def test_subscriber_can_view(self) -> None:
        """A SUBSCRIBER can view rules in their department."""
        session = _mock_session_with_assignments([("finance", "subscriber")])
        result = await can_view(session, user_id="finance-sub", rule_department_id="finance")
        assert result is True

    async def test_no_capacity_cannot_view_restricted(self) -> None:
        """A user with no capacity assignments cannot view non-public rules."""
        session = _mock_session_with_assignments([])
        result = await can_view(session, user_id="outsider", rule_department_id="legal")
        assert result is False

    async def test_only_owner_can_approve(self) -> None:
        """Only OWNER capacity can approve rules."""
        session_reviewer = _mock_session_with_assignments([("legal", "reviewer")])
        assert await can_approve(session_reviewer, user_id="reviewer", rule_department_id="legal") is False

        session_owner = _mock_session_with_assignments([("legal", "owner")])
        assert await can_approve(session_owner, user_id="owner", rule_department_id="legal") is True

    def test_capacity_hierarchy(self) -> None:
        """Capacity enum values follow the expected hierarchy."""
        from rulerepo_server.domain.department import capacity_rank

        assert capacity_rank(Capacity.OWNER) > capacity_rank(Capacity.REVIEWER)
        assert capacity_rank(Capacity.REVIEWER) > capacity_rank(Capacity.AUDITOR)
        assert capacity_rank(Capacity.AUDITOR) > capacity_rank(Capacity.SUBSCRIBER)

"""Unit tests for the Department and Capacity model.

Tests domain types, service logic with mocked DB session, and resolution helpers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rulerepo_server.domain.department import (
    Capacity,
    CapacityAssignment,
    Department,
    DepartmentType,
    RuleOwnership,
    capacity_rank,
)

# ---------------------------------------------------------------------------
# Domain type tests
# ---------------------------------------------------------------------------


class TestDepartmentType:
    def test_values(self) -> None:
        assert DepartmentType.LEGAL == "legal"
        assert DepartmentType.HR == "hr"
        assert DepartmentType.FINANCE == "finance"
        assert DepartmentType.SALES == "sales"
        assert DepartmentType.MARKETING == "marketing"
        assert DepartmentType.IT == "it"
        assert DepartmentType.OPERATIONS == "operations"
        assert DepartmentType.RND == "rnd"
        assert DepartmentType.EXECUTIVE == "executive"
        assert DepartmentType.CUSTOM == "custom"

    def test_from_string(self) -> None:
        assert DepartmentType("legal") == DepartmentType.LEGAL


class TestCapacity:
    def test_values(self) -> None:
        assert Capacity.OWNER == "owner"
        assert Capacity.REVIEWER == "reviewer"
        assert Capacity.SUBSCRIBER == "subscriber"
        assert Capacity.AUDITOR == "auditor"

    def test_from_string(self) -> None:
        assert Capacity("owner") == Capacity.OWNER

    def test_capacity_rank_ordering(self) -> None:
        assert capacity_rank(Capacity.OWNER) > capacity_rank(Capacity.REVIEWER)
        assert capacity_rank(Capacity.REVIEWER) > capacity_rank(Capacity.AUDITOR)
        assert capacity_rank(Capacity.AUDITOR) > capacity_rank(Capacity.SUBSCRIBER)


class TestDepartment:
    def test_creation(self) -> None:
        dept = Department(
            id="dept-1",
            name="Legal",
            type=DepartmentType.LEGAL,
            parent_id=None,
            head="user-1",
            cost_center="CC-100",
            locale="en",
        )
        assert dept.id == "dept-1"
        assert dept.name == "Legal"
        assert dept.type == DepartmentType.LEGAL
        assert dept.parent_id is None
        assert dept.head == "user-1"
        assert dept.cost_center == "CC-100"
        assert dept.locale == "en"

    def test_frozen(self) -> None:
        dept = Department(id="dept-1", name="Legal", type=DepartmentType.LEGAL)
        with pytest.raises(AttributeError):
            dept.name = "Changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        dept = Department(id="dept-2", name="HR", type=DepartmentType.HR)
        assert dept.parent_id is None
        assert dept.head == ""
        assert dept.cost_center is None
        assert dept.locale is None


class TestRuleOwnership:
    def test_creation(self) -> None:
        ownership = RuleOwnership(
            rule_id="rule-1",
            owner_department_id="dept-1",
            delegated_to=["user-a", "user-b"],
        )
        assert ownership.rule_id == "rule-1"
        assert ownership.owner_department_id == "dept-1"
        assert ownership.delegated_to == ["user-a", "user-b"]

    def test_default_delegation(self) -> None:
        ownership = RuleOwnership(rule_id="rule-1", owner_department_id="dept-1")
        assert ownership.delegated_to == []


class TestCapacityAssignment:
    def test_creation(self) -> None:
        assignment = CapacityAssignment(
            department_id="dept-1",
            user_id="user-1",
            capacity=Capacity.REVIEWER,
            rule_filter={"scope": "engineering"},
        )
        assert assignment.department_id == "dept-1"
        assert assignment.user_id == "user-1"
        assert assignment.capacity == Capacity.REVIEWER
        assert assignment.rule_filter == {"scope": "engineering"}

    def test_default_filter(self) -> None:
        assignment = CapacityAssignment(
            department_id="dept-1",
            user_id="user-1",
            capacity=Capacity.SUBSCRIBER,
        )
        assert assignment.rule_filter is None


# ---------------------------------------------------------------------------
# Service tests with mocked session
# ---------------------------------------------------------------------------


class TestDepartmentServiceResolvers:
    """Test the resolution helpers using mocked DB queries."""

    @pytest.fixture()
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def service(self, mock_session: AsyncMock):
        from rulerepo_server.services.departments.service import DepartmentService

        return DepartmentService(mock_session)

    @pytest.mark.asyncio
    async def test_resolve_owner_no_ownership(self, service, mock_session) -> None:
        """When no ownership exists, resolve_owner returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.resolve_owner("nonexistent-rule")
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_approvers_no_ownership(self, service, mock_session) -> None:
        """When no ownership exists, resolve_approvers returns empty list."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.resolve_approvers("nonexistent-rule")
        assert result == []

    @pytest.mark.asyncio
    async def test_resolve_audience_no_ownership(self, service, mock_session) -> None:
        """When no ownership exists, resolve_audience returns empty list."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.resolve_audience("nonexistent-rule", Capacity.SUBSCRIBER)
        assert result == []

    @pytest.mark.asyncio
    async def test_effective_capacity_no_ownership(self, service, mock_session) -> None:
        """When no ownership exists, effective_capacity returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.effective_capacity("user-1", "nonexistent-rule")
        assert result is None

    @pytest.mark.asyncio
    async def test_effective_capacity_picks_highest(self, service, mock_session) -> None:
        """effective_capacity returns the highest-ranked capacity."""
        # Mock ownership lookup
        ownership_model = MagicMock()
        ownership_model.rule_id = "rule-1"
        ownership_model.owner_department_id = "dept-1"
        ownership_model.delegated_to = []

        # Mock capacity assignments - two assignments
        assignment_reviewer = MagicMock()
        assignment_reviewer.capacity = "reviewer"
        assignment_subscriber = MagicMock()
        assignment_subscriber.capacity = "subscriber"

        call_count = 0

        def mock_execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # First call: ownership lookup
                result.scalar_one_or_none.return_value = ownership_model
            else:
                # Second call: capacity assignments
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [assignment_reviewer, assignment_subscriber]
                result.scalars.return_value = scalars_mock
            return result

        mock_session.execute = AsyncMock(side_effect=mock_execute_side_effect)

        result = await service.effective_capacity("user-1", "rule-1")
        assert result == Capacity.REVIEWER

    @pytest.mark.asyncio
    async def test_assign_capacity_department_not_found(self, service, mock_session) -> None:
        """assign_capacity raises NotFoundError when department does not exist."""
        from rulerepo_server.core.errors import NotFoundError

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await service.assign_capacity("nonexistent-dept", "user-1", Capacity.REVIEWER)

    @pytest.mark.asyncio
    async def test_set_rule_ownership_department_not_found(self, service, mock_session) -> None:
        """set_rule_ownership raises NotFoundError when department does not exist."""
        from rulerepo_server.core.errors import NotFoundError

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await service.set_rule_ownership("rule-1", "nonexistent-dept")

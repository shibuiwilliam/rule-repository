"""Tests for department ABAC authorization (IMPROVEMENT.md Proposal 10).

Covers:
- Default policy set semantics
- Cross-department READ permissions
- Same-department capacity-based permissions
- Policy customization
- check_permission integration with mocked DB
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rulerepo_server.domain.department import (
    _ANY_DEPT,
    _SAME_DEPT,
    Action,
    Capacity,
    DepartmentPolicy,
    Principal,
    default_policies,
)
from rulerepo_server.services.departments.authz import (
    _principal_matches,
    check_permission,
    get_policies,
    get_policies_for_department,
    reset_policies,
    set_policies,
)


@pytest.fixture(autouse=True)
def _reset_policy_store():
    """Reset policies to defaults before each test."""
    reset_policies()
    yield
    reset_policies()


# ---------------------------------------------------------------------------
# Default policy set
# ---------------------------------------------------------------------------


class TestDefaultPolicies:
    def test_has_all_actions(self) -> None:
        policies = default_policies()
        actions_covered = {p.action for p in policies}
        assert actions_covered == set(Action)

    def test_owner_can_do_everything(self) -> None:
        """Same-department OWNER should appear in every action's principals."""
        policies = default_policies()
        owner_principal = Principal(department=_SAME_DEPT, capacity=Capacity.OWNER)
        for p in policies:
            assert owner_principal in p.allowed_principals, f"OWNER not allowed for {p.action}"

    def test_reviewer_can_read_edit_and_evaluate(self) -> None:
        policies = default_policies()
        reviewer = Principal(department=_SAME_DEPT, capacity=Capacity.REVIEWER)
        for p in policies:
            if p.action in (Action.READ, Action.EDIT, Action.EVALUATE):
                assert reviewer in p.allowed_principals
            else:
                assert reviewer not in p.allowed_principals, f"REVIEWER should not be in {p.action}"

    def test_subscriber_can_only_read(self) -> None:
        policies = default_policies()
        subscriber = Principal(department=_SAME_DEPT, capacity=Capacity.SUBSCRIBER)
        for p in policies:
            if p.action == Action.READ:
                assert subscriber in p.allowed_principals
            else:
                assert subscriber not in p.allowed_principals

    def test_auditor_can_read_and_evaluate(self) -> None:
        policies = default_policies()
        auditor = Principal(department=_SAME_DEPT, capacity=Capacity.AUDITOR)
        for p in policies:
            if p.action in (Action.READ, Action.EVALUATE):
                assert auditor in p.allowed_principals
            else:
                assert auditor not in p.allowed_principals

    def test_cross_department_read_allowed(self) -> None:
        """Any capacity in any department should grant READ."""
        policies = default_policies()
        read_policies = [p for p in policies if p.action == Action.READ]
        assert len(read_policies) == 1
        read_policy = read_policies[0]

        # Check that cross-department principals exist for all capacities
        for cap in Capacity:
            cross_dept = Principal(department=_ANY_DEPT, capacity=cap)
            assert cross_dept in read_policy.allowed_principals

    def test_cross_department_edit_denied(self) -> None:
        """No cross-department principals should exist for EDIT."""
        policies = default_policies()
        edit_policies = [p for p in policies if p.action == Action.EDIT]
        for p in edit_policies:
            for principal in p.allowed_principals:
                assert principal.department != _ANY_DEPT


# ---------------------------------------------------------------------------
# Principal matching
# ---------------------------------------------------------------------------


class TestPrincipalMatches:
    def test_same_dept_match(self) -> None:
        principal = Principal(department=_SAME_DEPT, capacity=Capacity.OWNER)
        user_caps = {"legal": Capacity.OWNER}
        assert _principal_matches(principal, "legal", user_caps)

    def test_same_dept_wrong_capacity(self) -> None:
        principal = Principal(department=_SAME_DEPT, capacity=Capacity.OWNER)
        user_caps = {"legal": Capacity.REVIEWER}
        assert not _principal_matches(principal, "legal", user_caps)

    def test_same_dept_no_assignment(self) -> None:
        principal = Principal(department=_SAME_DEPT, capacity=Capacity.OWNER)
        user_caps = {"engineering": Capacity.OWNER}
        assert not _principal_matches(principal, "legal", user_caps)

    def test_any_dept_match(self) -> None:
        principal = Principal(department=_ANY_DEPT, capacity=Capacity.SUBSCRIBER)
        user_caps = {"engineering": Capacity.SUBSCRIBER}
        assert _principal_matches(principal, "legal", user_caps)

    def test_any_dept_wrong_capacity(self) -> None:
        principal = Principal(department=_ANY_DEPT, capacity=Capacity.OWNER)
        user_caps = {"engineering": Capacity.SUBSCRIBER}
        assert not _principal_matches(principal, "engineering", user_caps)

    def test_specific_dept_match(self) -> None:
        principal = Principal(department="legal", capacity=Capacity.REVIEWER)
        user_caps = {"legal": Capacity.REVIEWER}
        assert _principal_matches(principal, "hr", user_caps)

    def test_specific_dept_no_assignment(self) -> None:
        principal = Principal(department="legal", capacity=Capacity.REVIEWER)
        user_caps = {"engineering": Capacity.REVIEWER}
        assert not _principal_matches(principal, "hr", user_caps)


# ---------------------------------------------------------------------------
# check_permission with mocked DB
# ---------------------------------------------------------------------------


def _mock_session_with_assignments(assignments: list[tuple[str, str]]) -> AsyncMock:
    """Create a mock session returning the given (department_id, capacity) pairs."""
    session = AsyncMock()

    mock_models = []
    for dept_id, cap in assignments:
        m = MagicMock()
        m.department_id = dept_id
        m.capacity = cap
        mock_models.append(m)

    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = mock_models
    result.scalars.return_value = scalars_mock
    session.execute.return_value = result

    return session


class TestCheckPermission:
    """Integration tests for check_permission with mocked DB."""

    async def test_same_dept_owner_can_edit(self) -> None:
        session = _mock_session_with_assignments([("legal", "owner")])
        assert await check_permission(session, "user1", "legal", Action.EDIT)

    async def test_same_dept_owner_can_approve(self) -> None:
        session = _mock_session_with_assignments([("legal", "owner")])
        assert await check_permission(session, "user1", "legal", Action.APPROVE)

    async def test_same_dept_reviewer_cannot_approve(self) -> None:
        session = _mock_session_with_assignments([("legal", "reviewer")])
        assert not await check_permission(session, "user1", "legal", Action.APPROVE)

    async def test_same_dept_reviewer_can_read(self) -> None:
        session = _mock_session_with_assignments([("legal", "reviewer")])
        assert await check_permission(session, "user1", "legal", Action.READ)

    async def test_same_dept_reviewer_can_evaluate(self) -> None:
        session = _mock_session_with_assignments([("legal", "reviewer")])
        assert await check_permission(session, "user1", "legal", Action.EVALUATE)

    async def test_same_dept_subscriber_cannot_edit(self) -> None:
        session = _mock_session_with_assignments([("legal", "subscriber")])
        assert not await check_permission(session, "user1", "legal", Action.EDIT)

    async def test_cross_dept_can_read(self) -> None:
        """Engineering SUBSCRIBER can READ Legal rules."""
        session = _mock_session_with_assignments([("engineering", "subscriber")])
        assert await check_permission(session, "user1", "legal", Action.READ)

    async def test_cross_dept_cannot_edit(self) -> None:
        """Engineering OWNER cannot EDIT Legal rules."""
        session = _mock_session_with_assignments([("engineering", "owner")])
        assert not await check_permission(session, "user1", "legal", Action.EDIT)

    async def test_cross_dept_cannot_approve(self) -> None:
        """Engineering OWNER cannot APPROVE Legal rules."""
        session = _mock_session_with_assignments([("engineering", "owner")])
        assert not await check_permission(session, "user1", "legal", Action.APPROVE)

    async def test_public_dept_read_always_allowed(self) -> None:
        """Public department is always readable even with no assignments."""
        session = _mock_session_with_assignments([])
        assert await check_permission(session, "user1", "public", Action.READ)

    async def test_public_dept_edit_denied(self) -> None:
        """Public department cannot be edited."""
        session = _mock_session_with_assignments([("public", "owner")])
        assert not await check_permission(session, "user1", "public", Action.EDIT)

    async def test_no_assignments_denied(self) -> None:
        """A user with no capacity assignments is denied everything."""
        session = _mock_session_with_assignments([])
        assert not await check_permission(session, "user1", "legal", Action.READ)
        assert not await check_permission(session, "user1", "legal", Action.EDIT)

    async def test_multiple_assignments(self) -> None:
        """User with capacities in multiple departments."""
        session = _mock_session_with_assignments(
            [
                ("legal", "subscriber"),
                ("engineering", "owner"),
            ]
        )
        # Can read legal (cross-dept)
        assert await check_permission(session, "user1", "legal", Action.READ)
        # Can also read legal (same-dept subscriber)
        assert await check_permission(session, "user1", "legal", Action.READ)
        # Cannot edit legal
        assert not await check_permission(session, "user1", "legal", Action.EDIT)
        # Can edit engineering (same-dept owner)
        assert await check_permission(session, "user1", "engineering", Action.EDIT)

    async def test_auditor_can_evaluate_not_edit(self) -> None:
        session = _mock_session_with_assignments([("legal", "auditor")])
        assert await check_permission(session, "user1", "legal", Action.EVALUATE)
        assert not await check_permission(session, "user1", "legal", Action.EDIT)


# ---------------------------------------------------------------------------
# Backward-compatible wrappers
# ---------------------------------------------------------------------------


class TestBackwardCompatWrappers:
    async def test_can_view_same_dept(self) -> None:
        from rulerepo_server.services.departments.authz import can_view

        session = _mock_session_with_assignments([("legal", "subscriber")])
        assert await can_view(session, "user1", "legal")

    async def test_can_view_cross_dept(self) -> None:
        from rulerepo_server.services.departments.authz import can_view

        session = _mock_session_with_assignments([("engineering", "subscriber")])
        assert await can_view(session, "user1", "legal")

    async def test_can_edit_same_dept_owner(self) -> None:
        from rulerepo_server.services.departments.authz import can_edit

        session = _mock_session_with_assignments([("legal", "owner")])
        assert await can_edit(session, "user1", "legal")

    async def test_can_edit_cross_dept_denied(self) -> None:
        from rulerepo_server.services.departments.authz import can_edit

        session = _mock_session_with_assignments([("engineering", "owner")])
        assert not await can_edit(session, "user1", "legal")

    async def test_can_approve_owner_only(self) -> None:
        from rulerepo_server.services.departments.authz import can_approve

        session = _mock_session_with_assignments([("legal", "owner")])
        assert await can_approve(session, "user1", "legal")

        session2 = _mock_session_with_assignments([("legal", "reviewer")])
        assert not await can_approve(session2, "user1", "legal")

    async def test_can_view_public(self) -> None:
        from rulerepo_server.services.departments.authz import can_view

        session = _mock_session_with_assignments([])
        assert await can_view(session, "user1", "public")


# ---------------------------------------------------------------------------
# Policy customization
# ---------------------------------------------------------------------------


class TestPolicyCustomization:
    def test_set_policies(self) -> None:
        custom = [
            DepartmentPolicy(
                owner_department="legal",
                action=Action.EDIT,
                allowed_principals=[
                    Principal(department="legal", capacity=Capacity.REVIEWER),
                ],
            ),
        ]
        set_policies(custom)
        assert get_policies() == custom

    def test_get_policies_for_department_filters(self) -> None:
        custom = [
            DepartmentPolicy(owner_department="legal", action=Action.READ, allowed_principals=[]),
            DepartmentPolicy(owner_department="hr", action=Action.READ, allowed_principals=[]),
            DepartmentPolicy(owner_department=_ANY_DEPT, action=Action.READ, allowed_principals=[]),
        ]
        set_policies(custom)
        legal_policies = get_policies_for_department("legal")
        # Should match "legal" + wildcard
        assert len(legal_policies) == 2

    async def test_custom_policy_grants_cross_dept_edit(self) -> None:
        """Custom policy: Legal REVIEWER can EDIT HR rules."""
        custom = default_policies() + [
            DepartmentPolicy(
                owner_department="hr",
                action=Action.EDIT,
                allowed_principals=[
                    Principal(department="legal", capacity=Capacity.REVIEWER),
                ],
            ),
        ]
        set_policies(custom)

        session = _mock_session_with_assignments([("legal", "reviewer")])
        assert await check_permission(session, "user1", "hr", Action.EDIT)

    async def test_custom_policy_does_not_affect_other_departments(self) -> None:
        """Custom HR policy doesn't change Finance permissions."""
        custom = default_policies() + [
            DepartmentPolicy(
                owner_department="hr",
                action=Action.EDIT,
                allowed_principals=[
                    Principal(department="finance", capacity=Capacity.AUDITOR),
                ],
            ),
        ]
        set_policies(custom)

        session = _mock_session_with_assignments([("finance", "auditor")])
        # HR edit: allowed by custom policy
        assert await check_permission(session, "user1", "hr", Action.EDIT)
        # Legal edit: not allowed (auditor can't edit by default)
        assert not await check_permission(session, "user1", "legal", Action.EDIT)


# ---------------------------------------------------------------------------
# Scenario: IMPROVEMENT.md requirements
# ---------------------------------------------------------------------------


class TestImprovementMDScenarios:
    """Test the exact scenarios from IMPROVEMENT.md Proposal 10."""

    async def test_engineering_can_read_legal_rules_but_not_edit(self) -> None:
        """Engineering department can READ Legal rules but not EDIT them."""
        session = _mock_session_with_assignments([("engineering", "owner")])
        assert await check_permission(session, "eng-user", "legal", Action.READ)
        assert not await check_permission(session, "eng-user", "legal", Action.EDIT)

    async def test_only_legal_owner_can_approve_legal_rules(self) -> None:
        """Only Legal OWNER can APPROVE Legal rules."""
        # Legal OWNER: yes
        session = _mock_session_with_assignments([("legal", "owner")])
        assert await check_permission(session, "legal-owner", "legal", Action.APPROVE)

        # Legal REVIEWER: no
        session2 = _mock_session_with_assignments([("legal", "reviewer")])
        assert not await check_permission(session2, "legal-reviewer", "legal", Action.APPROVE)

        # Engineering OWNER: no
        session3 = _mock_session_with_assignments([("engineering", "owner")])
        assert not await check_permission(session3, "eng-owner", "legal", Action.APPROVE)

    async def test_cross_department_read_all_capacities(self) -> None:
        """Any capacity in any department grants READ to any department's rules."""
        for cap in Capacity:
            session = _mock_session_with_assignments([("finance", cap.value)])
            assert await check_permission(session, "fin-user", "legal", Action.READ), (
                f"Finance {cap} should be able to READ Legal rules"
            )

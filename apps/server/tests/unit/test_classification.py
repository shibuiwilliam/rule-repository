"""Unit tests for Classification and Multi-Tenancy (Stream C).

Tests domain types, session context helper, ES classification filter,
and PII field-path redaction.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from rulerepo_server.core.db_context import AuthenticatedUser, with_user_context
from rulerepo_server.core.pii.redactor import redact_pii
from rulerepo_server.domain.classification import (
    Classification,
    classification_rank,
    clearance_sufficient,
)
from rulerepo_server.services.classification.es_filter import classification_filter

# ---------------------------------------------------------------------------
# Classification enum tests
# ---------------------------------------------------------------------------


class TestClassificationEnum:
    def test_values(self) -> None:
        assert Classification.PUBLIC == "public"
        assert Classification.INTERNAL == "internal"
        assert Classification.CONFIDENTIAL == "confidential"
        assert Classification.RESTRICTED == "restricted"

    def test_from_string(self) -> None:
        assert Classification("public") == Classification.PUBLIC
        assert Classification("restricted") == Classification.RESTRICTED

    def test_ordering(self) -> None:
        """Classification ranks follow PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED."""
        assert classification_rank(Classification.PUBLIC) < classification_rank(Classification.INTERNAL)
        assert classification_rank(Classification.INTERNAL) < classification_rank(Classification.CONFIDENTIAL)
        assert classification_rank(Classification.CONFIDENTIAL) < classification_rank(Classification.RESTRICTED)

    def test_all_members(self) -> None:
        members = list(Classification)
        assert len(members) == 4


class TestClearanceSufficient:
    def test_same_level(self) -> None:
        for cls in Classification:
            assert clearance_sufficient(cls, cls) is True

    def test_higher_clearance(self) -> None:
        assert clearance_sufficient(Classification.RESTRICTED, Classification.PUBLIC) is True
        assert clearance_sufficient(Classification.CONFIDENTIAL, Classification.INTERNAL) is True

    def test_lower_clearance(self) -> None:
        assert clearance_sufficient(Classification.PUBLIC, Classification.INTERNAL) is False
        assert clearance_sufficient(Classification.INTERNAL, Classification.CONFIDENTIAL) is False
        assert clearance_sufficient(Classification.CONFIDENTIAL, Classification.RESTRICTED) is False


# ---------------------------------------------------------------------------
# AuthenticatedUser tests
# ---------------------------------------------------------------------------


class TestAuthenticatedUser:
    def test_creation(self) -> None:
        user = AuthenticatedUser(
            id="user-1",
            clearance=Classification.CONFIDENTIAL,
            department_ids=["dept-a", "dept-b"],
        )
        assert user.id == "user-1"
        assert user.clearance == Classification.CONFIDENTIAL
        assert user.department_ids == ["dept-a", "dept-b"]

    def test_defaults(self) -> None:
        user = AuthenticatedUser(id="user-2", clearance=Classification.PUBLIC)
        assert user.department_ids == []

    def test_frozen(self) -> None:
        user = AuthenticatedUser(id="user-3", clearance=Classification.INTERNAL)
        with pytest.raises(AttributeError):
            user.id = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# with_user_context tests (mocked session)
# ---------------------------------------------------------------------------


class TestWithUserContext:
    @pytest.mark.asyncio
    async def test_sets_session_variables(self) -> None:
        """Verify that the correct SET LOCAL statements are issued."""
        session = AsyncMock()

        user = AuthenticatedUser(
            id="user-42",
            clearance=Classification.CONFIDENTIAL,
            department_ids=["dept-1", "dept-2"],
        )

        await with_user_context(session, user)

        assert session.execute.call_count == 3
        calls = session.execute.call_args_list

        # Check first call: SET LOCAL app.user_id
        first_call_text = calls[0].args[0].text
        first_call_params = calls[0].args[1]
        assert "app.user_id" in first_call_text
        assert first_call_params == {"user_id": "user-42"}

        # Check second call: SET LOCAL app.user_departments
        second_call_text = calls[1].args[0].text
        second_call_params = calls[1].args[1]
        assert "app.user_departments" in second_call_text
        assert second_call_params == {"departments": "dept-1,dept-2"}

        # Check third call: SET LOCAL app.user_clearance
        third_call_text = calls[2].args[0].text
        third_call_params = calls[2].args[1]
        assert "app.user_clearance" in third_call_text
        assert third_call_params == {"clearance": "confidential"}

    @pytest.mark.asyncio
    async def test_empty_departments(self) -> None:
        """Departments CSV should be empty string when no departments."""
        session = AsyncMock()
        user = AuthenticatedUser(id="user-1", clearance=Classification.PUBLIC)

        await with_user_context(session, user)

        second_call_params = session.execute.call_args_list[1].args[1]
        assert second_call_params == {"departments": ""}

    @pytest.mark.asyncio
    async def test_uses_parameterized_queries(self) -> None:
        """Ensure we use parameterized queries, not f-strings."""
        session = AsyncMock()
        # Attempt SQL injection in user id
        user = AuthenticatedUser(
            id="'; DROP TABLE rules; --",
            clearance=Classification.PUBLIC,
        )

        await with_user_context(session, user)

        # The SQL text should contain :user_id placeholder, not the injected value
        first_call_text = session.execute.call_args_list[0].args[0].text
        assert ":user_id" in first_call_text
        # The injected value should be in the params dict, safely escaped by SQLAlchemy
        first_call_params = session.execute.call_args_list[0].args[1]
        assert first_call_params["user_id"] == "'; DROP TABLE rules; --"


# ---------------------------------------------------------------------------
# ES classification_filter tests
# ---------------------------------------------------------------------------


class TestClassificationFilter:
    def test_public_clearance(self) -> None:
        """PUBLIC clearance user should only see PUBLIC and INTERNAL."""
        user = AuthenticatedUser(id="u1", clearance=Classification.PUBLIC)
        result = classification_filter(user)

        should = result["bool"]["should"]
        classification_values = _extract_classification_terms(should)
        assert "public" in classification_values
        assert "internal" in classification_values
        assert "confidential" not in classification_values
        assert "restricted" not in classification_values

    def test_internal_clearance(self) -> None:
        """INTERNAL clearance user should see PUBLIC and INTERNAL."""
        user = AuthenticatedUser(id="u1", clearance=Classification.INTERNAL)
        result = classification_filter(user)

        should = result["bool"]["should"]
        classification_values = _extract_classification_terms(should)
        assert "public" in classification_values
        assert "internal" in classification_values
        assert "confidential" not in classification_values

    def test_confidential_clearance(self) -> None:
        """CONFIDENTIAL clearance user should see PUBLIC, INTERNAL, CONFIDENTIAL."""
        user = AuthenticatedUser(
            id="u1",
            clearance=Classification.CONFIDENTIAL,
            department_ids=["dept-1"],
        )
        result = classification_filter(user)

        should = result["bool"]["should"]
        classification_values = _extract_classification_terms(should)
        assert "public" in classification_values
        assert "internal" in classification_values
        assert "confidential" in classification_values
        assert "restricted" not in classification_values

    def test_restricted_clearance(self) -> None:
        """RESTRICTED clearance user should see all classification levels."""
        user = AuthenticatedUser(
            id="u1",
            clearance=Classification.RESTRICTED,
            department_ids=["dept-1"],
        )
        result = classification_filter(user)

        should = result["bool"]["should"]
        classification_values = _extract_classification_terms(should)
        assert "public" in classification_values
        assert "internal" in classification_values
        assert "confidential" in classification_values
        assert "restricted" in classification_values

    def test_confidential_with_department_filter(self) -> None:
        """CONFIDENTIAL clauses should include department membership filter."""
        user = AuthenticatedUser(
            id="u1",
            clearance=Classification.CONFIDENTIAL,
            department_ids=["dept-a", "dept-b"],
        )
        result = classification_filter(user)

        should = result["bool"]["should"]
        # Find the confidential clause - it should be a bool with must clauses
        confidential_clauses = [
            c
            for c in should
            if "bool" in c
            and any(m.get("term", {}).get("classification") == "confidential" for m in c["bool"].get("must", []))
        ]
        assert len(confidential_clauses) == 1
        must_clauses = confidential_clauses[0]["bool"]["must"]
        dept_filter = [m for m in must_clauses if "terms" in m]
        assert len(dept_filter) == 1
        assert dept_filter[0]["terms"]["owner_department_id"] == ["dept-a", "dept-b"]

    def test_minimum_should_match(self) -> None:
        """Filter must require at least one clause to match."""
        user = AuthenticatedUser(id="u1", clearance=Classification.PUBLIC)
        result = classification_filter(user)
        assert result["bool"]["minimum_should_match"] == 1

    def test_high_clearance_sees_all_low_clearance_restricted(self) -> None:
        """Verify both directions: high clearance sees all, low is restricted."""
        # High clearance
        high_user = AuthenticatedUser(
            id="admin",
            clearance=Classification.RESTRICTED,
            department_ids=["dept-1"],
        )
        high_result = classification_filter(high_user)
        high_classifications = _extract_classification_terms(high_result["bool"]["should"])

        # Low clearance
        low_user = AuthenticatedUser(id="viewer", clearance=Classification.PUBLIC)
        low_result = classification_filter(low_user)
        low_classifications = _extract_classification_terms(low_result["bool"]["should"])

        # High sees everything
        assert len(high_classifications) == 4
        # Low sees only public and internal
        assert len(low_classifications) == 2
        assert "confidential" not in low_classifications
        assert "restricted" not in low_classifications


def _extract_classification_terms(should: list[dict]) -> set[str]:
    """Helper to extract classification values from should clauses."""
    values: set[str] = set()
    for clause in should:
        if "term" in clause:
            val = clause["term"].get("classification")
            if val:
                values.add(val)
        elif "bool" in clause:
            for must_clause in clause["bool"].get("must", []):
                if "term" in must_clause:
                    val = must_clause["term"].get("classification")
                    if val:
                        values.add(val)
    return values


# ---------------------------------------------------------------------------
# PII redaction tests
# ---------------------------------------------------------------------------


class TestPiiRedaction:
    def test_simple_field(self) -> None:
        data = {"name": "John Doe", "ssn": "123-45-6789"}
        result = redact_pii(data, ["ssn"])
        assert result["ssn"] == "[REDACTED]"
        assert result["name"] == "John Doe"

    def test_nested_field(self) -> None:
        data = {"employee": {"name": "Jane", "ssn": "987-65-4321"}}
        result = redact_pii(data, ["employee.ssn"])
        assert result["employee"]["ssn"] == "[REDACTED]"
        assert result["employee"]["name"] == "Jane"

    def test_deeply_nested_field(self) -> None:
        data = {"a": {"b": {"c": {"secret": "value"}}}}
        result = redact_pii(data, ["a.b.c.secret"])
        assert result["a"]["b"]["c"]["secret"] == "[REDACTED]"

    def test_missing_field_is_noop(self) -> None:
        data = {"name": "John"}
        result = redact_pii(data, ["nonexistent"])
        assert result == {"name": "John"}

    def test_missing_intermediate_is_noop(self) -> None:
        data = {"name": "John"}
        result = redact_pii(data, ["a.b.c"])
        assert result == {"name": "John"}

    def test_multiple_fields(self) -> None:
        data = {
            "employee_id": "E001",
            "ssn": "123-45-6789",
            "overtime_hours": 50,
        }
        result = redact_pii(data, ["employee_id", "ssn"])
        assert result["employee_id"] == "[REDACTED]"
        assert result["ssn"] == "[REDACTED]"
        assert result["overtime_hours"] == 50

    def test_does_not_modify_original(self) -> None:
        data = {"ssn": "123-45-6789"}
        result = redact_pii(data, ["ssn"])
        assert data["ssn"] == "123-45-6789"
        assert result["ssn"] == "[REDACTED]"

    def test_empty_pii_fields(self) -> None:
        data = {"name": "John", "age": 30}
        result = redact_pii(data, [])
        assert result == data

    def test_non_dict_intermediate(self) -> None:
        """If an intermediate value is not a dict, skip gracefully."""
        data = {"a": "string_value"}
        result = redact_pii(data, ["a.b.c"])
        assert result == {"a": "string_value"}

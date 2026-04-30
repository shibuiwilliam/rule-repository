"""Unit tests for Pydantic schemas — validation at API boundaries."""

import pytest
from pydantic import ValidationError

from rulerepo_server.schemas.intent import IntentRequest
from rulerepo_server.schemas.rule import RuleCreate, RuleUpdate
from rulerepo_server.schemas.search import SearchQuery


class TestRuleCreate:
    def test_minimal(self) -> None:
        rule = RuleCreate(statement="Test rule")
        assert rule.statement == "Test rule"
        assert rule.modality.value == "MUST"
        assert rule.severity.value == "MEDIUM"

    def test_full(self) -> None:
        rule = RuleCreate(
            statement="Overtime must not exceed 45 hours per month",
            modality="MUST_NOT",
            severity="HIGH",
            scope=["hr/attendance"],
            tags=["overtime", "labor-law"],
            rationale="Labor Standards Act Article 36",
        )
        assert rule.modality.value == "MUST_NOT"
        assert rule.scope == ["hr/attendance"]

    def test_empty_statement_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RuleCreate(statement="")

    def test_long_statement_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RuleCreate(statement="x" * 10001)


class TestRuleUpdate:
    def test_all_optional(self) -> None:
        update = RuleUpdate()
        assert update.statement is None
        assert update.modality is None

    def test_partial(self) -> None:
        update = RuleUpdate(severity="CRITICAL", revision_note="Escalated")
        assert update.severity.value == "CRITICAL"
        assert update.revision_note == "Escalated"


class TestSearchQuery:
    def test_defaults(self) -> None:
        q = SearchQuery(query="overtime")
        assert q.page == 1
        assert q.page_size == 20

    def test_with_filters(self) -> None:
        q = SearchQuery(query="test", modality="MUST", severity="HIGH")
        assert q.modality.value == "MUST"

    def test_empty_query_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SearchQuery(query="")


class TestIntentRequest:
    def test_basic(self) -> None:
        req = IntentRequest(query="What are the rules for overtime?")
        assert req.context is None

    def test_with_context(self) -> None:
        req = IntentRequest(
            query="Is this compliant?",
            context={"employee_id": "E001", "hours": 50},
        )
        assert req.context["hours"] == 50

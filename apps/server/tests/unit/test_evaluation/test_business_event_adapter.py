"""Tests for the business_event evaluation domain adapter."""

from __future__ import annotations

import pytest

from rulerepo_server.domain.evaluation import EvaluationContext
from rulerepo_server.domain.subject import Subject, SubjectFilter
from rulerepo_server.services.evaluation.adapters.base import EvaluationDomainAdapter
from rulerepo_server.services.evaluation.adapters.business_event.adapter import (
    BusinessEventAdapter,
)


class TestBusinessEventAdapterProtocol:
    """Verify that BusinessEventAdapter implements EvaluationDomainAdapter."""

    def test_implements_protocol(self) -> None:
        adapter = BusinessEventAdapter()
        assert isinstance(adapter, EvaluationDomainAdapter)

    def test_domain_attribute(self) -> None:
        adapter = BusinessEventAdapter()
        assert adapter.domain == "business_event"


class TestBusinessEventAdapterParse:
    """Test BusinessEventAdapter.parse()."""

    @pytest.mark.asyncio
    async def test_parse_basic_event(self) -> None:
        adapter = BusinessEventAdapter()
        payload = {
            "event_type": "hr/overtime",
            "facts": {"hours_worked": 50, "month": "2025-01"},
            "description": "Employee worked 50 hours overtime",
            "actor": "hr-system",
        }
        ctx = await adapter.parse(payload)
        assert isinstance(ctx, EvaluationContext)
        assert ctx.facts["event_type"] == "hr/overtime"
        assert ctx.facts["hours_worked"] == 50
        assert ctx.actor == "hr-system"
        assert ctx.narrative == "Employee worked 50 hours overtime"

    @pytest.mark.asyncio
    async def test_parse_with_subject(self) -> None:
        adapter = BusinessEventAdapter()
        payload = {
            "event_type": "hr/attendance",
            "subject": {
                "organization_unit": "engineering",
                "role": "developer",
                "employment_type": "full-time",
                "location": "tokyo",
                "seniority_level": 3,
                "department": "platform",
            },
            "facts": {"late_days": 5},
        }
        ctx = await adapter.parse(payload)
        assert ctx.facts["subject_organization_unit"] == "engineering"
        assert ctx.facts["subject_role"] == "developer"
        assert ctx.facts["subject_employment_type"] == "full-time"
        assert ctx.facts["subject_location"] == "tokyo"
        assert ctx.facts["subject_seniority_level"] == 3
        assert ctx.facts["subject_department"] == "platform"

    @pytest.mark.asyncio
    async def test_parse_minimal_payload(self) -> None:
        adapter = BusinessEventAdapter()
        payload = {"event_type": "finance/expense"}
        ctx = await adapter.parse(payload)
        assert ctx.facts["event_type"] == "finance/expense"
        assert "Business event: finance/expense" in ctx.narrative

    @pytest.mark.asyncio
    async def test_parse_empty_payload(self) -> None:
        adapter = BusinessEventAdapter()
        ctx = await adapter.parse({})
        assert ctx.facts["event_type"] == "unknown"
        assert ctx.narrative == "Business event: unknown"


class TestBusinessEventAdapterResolveScopes:
    """Test BusinessEventAdapter.resolve_scopes()."""

    def test_resolve_hr_overtime(self) -> None:
        adapter = BusinessEventAdapter()
        scopes = adapter.resolve_scopes({"event_type": "hr/overtime"})
        assert "hr/overtime" in scopes

    def test_resolve_finance_expense(self) -> None:
        adapter = BusinessEventAdapter()
        scopes = adapter.resolve_scopes({"event_type": "finance/expense"})
        assert "finance/expense" in scopes

    def test_resolve_with_department(self) -> None:
        adapter = BusinessEventAdapter()
        scopes = adapter.resolve_scopes(
            {
                "event_type": "hr/leave",
                "subject": {"department": "Engineering"},
            }
        )
        assert "hr/leave" in scopes
        assert "department/engineering" in scopes

    def test_resolve_unknown_event_type(self) -> None:
        adapter = BusinessEventAdapter()
        scopes = adapter.resolve_scopes({"event_type": "custom/something"})
        assert scopes == ["business/general"]

    def test_resolve_empty_payload(self) -> None:
        adapter = BusinessEventAdapter()
        scopes = adapter.resolve_scopes({})
        assert scopes == ["business/general"]

    def test_resolve_generic_hr(self) -> None:
        adapter = BusinessEventAdapter()
        scopes = adapter.resolve_scopes({"event_type": "hr"})
        assert "hr/general" in scopes


class TestBusinessEventAdapterPromptFragments:
    """Test BusinessEventAdapter.get_prompt_fragments()."""

    def test_returns_required_keys(self) -> None:
        adapter = BusinessEventAdapter()
        fragments = adapter.get_prompt_fragments()
        assert "domain_intro" in fragments
        assert "context_format" in fragments
        assert isinstance(fragments["domain_intro"], str)
        assert isinstance(fragments["context_format"], str)
        assert len(fragments["domain_intro"]) > 0
        assert len(fragments["context_format"]) > 0


class TestSubjectFilter:
    """Test SubjectFilter.matches()."""

    def test_empty_filter_matches_any(self) -> None:
        f = SubjectFilter()
        s = Subject(organization_unit="eng", role="dev")
        assert f.matches(s)

    def test_exact_match(self) -> None:
        f = SubjectFilter(organization_unit="engineering", role="developer")
        s = Subject(organization_unit="engineering", role="developer")
        assert f.matches(s)

    def test_case_insensitive(self) -> None:
        f = SubjectFilter(organization_unit="Engineering")
        s = Subject(organization_unit="engineering")
        assert f.matches(s)

    def test_partial_filter(self) -> None:
        f = SubjectFilter(department="hr")
        s = Subject(organization_unit="corp", role="manager", department="hr")
        assert f.matches(s)

    def test_mismatch(self) -> None:
        f = SubjectFilter(department="finance")
        s = Subject(department="hr")
        assert not f.matches(s)

    def test_filter_field_set_but_subject_field_none(self) -> None:
        f = SubjectFilter(location="tokyo")
        s = Subject(organization_unit="eng")
        assert not f.matches(s)

    def test_all_fields_match(self) -> None:
        f = SubjectFilter(
            organization_unit="corp",
            role="analyst",
            employment_type="full-time",
            location="tokyo",
            department="finance",
        )
        s = Subject(
            organization_unit="corp",
            role="analyst",
            employment_type="full-time",
            location="tokyo",
            seniority_level=5,
            department="finance",
        )
        assert f.matches(s)

    def test_one_field_mismatch(self) -> None:
        f = SubjectFilter(
            organization_unit="corp",
            role="analyst",
            department="finance",
        )
        s = Subject(
            organization_unit="corp",
            role="analyst",
            department="hr",
        )
        assert not f.matches(s)

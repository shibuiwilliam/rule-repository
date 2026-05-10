"""Tests for subject_kind filtering in rule_selector.

Verifies that select_rules filters by applicable_subject_types
when a subject_type parameter is provided, using the new SubjectKind values.

Rules with None/empty applicable_subject_types are treated as universal
(applicable to all subject types), not code-only.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rulerepo_server.domain.evaluation import EvaluationContext
from rulerepo_server.services.evaluation.rule_selector import select_rules


def _make_rule(
    rule_id: str = "r1",
    statement: str = "Test rule",
    modality: str = "MUST",
    severity: str = "HIGH",
    status: str = "EFFECTIVE",
    scope: list | None = None,
    tags: list | None = None,
    applicable_subject_types: list | None = None,
    **kwargs,
):
    """Create a mock RuleModel for testing."""
    rule = MagicMock()
    rule.id = rule_id
    rule.statement = statement
    rule.modality = modality
    rule.severity = severity
    rule.status = status
    rule.scope = scope or ["engineering"]
    rule.tags = tags or []
    rule.applicable_subject_types = applicable_subject_types
    rule.effective_period = {}
    rule.rationale = ""
    rule.context = ""
    rule.preconditions = []
    rule.exceptions = []
    rule.following_examples = []
    rule.violation_examples = []
    rule.maturity_level = "proven"
    for k, v in kwargs.items():
        setattr(rule, k, v)
    return rule


def _mock_session(rules: list):
    """Create a mock async session returning the given rules."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = rules
    mock_session.execute = AsyncMock(return_value=mock_result)
    return mock_session


@pytest.mark.asyncio
async def test_subject_type_filter_narrows_rules():
    """Rules not matching the subject_kind are excluded."""
    code_rule = _make_rule("r1", applicable_subject_types=["code_diff"])
    event_rule = _make_rule("r2", applicable_subject_types=["event"], scope=["hr"])
    both_rule = _make_rule("r3", applicable_subject_types=["code_diff", "event"])

    session = _mock_session([code_rule, event_rule, both_rule])
    ctx = EvaluationContext()

    # Filter for event — should exclude the code-only rule
    results = await select_rules(session, ctx, subject_type="event", severity_min="LOW")
    result_ids = {r["id"] for r in results}
    assert "r2" in result_ids  # event rule
    assert "r3" in result_ids  # both types
    assert "r1" not in result_ids  # code_diff only


@pytest.mark.asyncio
async def test_no_subject_type_returns_all():
    """Without subject_type filter, all rules pass through."""
    code_rule = _make_rule("r1", applicable_subject_types=["code_diff"])
    event_rule = _make_rule("r2", applicable_subject_types=["event"])

    session = _mock_session([code_rule, event_rule])
    ctx = EvaluationContext()

    # No subject_type — both rules should pass
    results = await select_rules(session, ctx, subject_type=None, severity_min="LOW")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_universal_rule_returned_for_any_subject_type():
    """Rules with applicable_subject_types=None are universal — returned for any subject type."""
    universal_rule = _make_rule("r1", applicable_subject_types=None)

    session = _mock_session([universal_rule])
    ctx = EvaluationContext()

    # Universal rule should be returned for clause_set
    results = await select_rules(session, ctx, subject_type="clause_set", severity_min="LOW")
    assert len(results) == 1
    assert results[0]["id"] == "r1"

    # Universal rule should be returned for transaction
    session = _mock_session([universal_rule])
    results = await select_rules(session, ctx, subject_type="transaction", severity_min="LOW")
    assert len(results) == 1

    # Universal rule should be returned for event
    session = _mock_session([universal_rule])
    results = await select_rules(session, ctx, subject_type="event", severity_min="LOW")
    assert len(results) == 1

    # Universal rule should be returned for code_diff too
    session = _mock_session([universal_rule])
    results = await select_rules(session, ctx, subject_type="code_diff", severity_min="LOW")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_code_only_rule_not_returned_for_transaction():
    """A rule explicitly marked code_diff only is NOT returned for transaction evaluation."""
    code_only = _make_rule("r1", applicable_subject_types=["code_diff"])

    session = _mock_session([code_only])
    ctx = EvaluationContext()

    results = await select_rules(session, ctx, subject_type="transaction", severity_min="LOW")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_multi_subject_rule_returned_for_both():
    """A rule with multiple subject types is returned for each."""
    multi_rule = _make_rule("r1", applicable_subject_types=["transaction", "code_diff"])

    session = _mock_session([multi_rule])
    ctx = EvaluationContext()

    # Should match transaction
    results = await select_rules(session, ctx, subject_type="transaction", severity_min="LOW")
    assert len(results) == 1

    # Should match code_diff
    session = _mock_session([multi_rule])
    results = await select_rules(session, ctx, subject_type="code_diff", severity_min="LOW")
    assert len(results) == 1

    # Should NOT match event
    session = _mock_session([multi_rule])
    results = await select_rules(session, ctx, subject_type="event", severity_min="LOW")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_empty_list_subject_types_treated_as_universal():
    """Rules with applicable_subject_types=[] are also universal."""
    rule_empty = _make_rule("r1", applicable_subject_types=[])

    session = _mock_session([rule_empty])
    ctx = EvaluationContext()

    # Empty list → universal (falsy in Python, so `or ALL_SUBJECT_TYPES` kicks in)
    results = await select_rules(session, ctx, subject_type="clause_set", severity_min="LOW")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_mixed_universal_and_specific_rules():
    """Filtering correctly separates universal from specific rules."""
    universal = _make_rule("r1", applicable_subject_types=None, scope=["compliance"])
    code_only = _make_rule("r2", applicable_subject_types=["code_diff"], scope=["engineering"])
    legal_only = _make_rule("r3", applicable_subject_types=["clause_set"], scope=["legal"])
    hr_transaction = _make_rule("r4", applicable_subject_types=["transaction", "event"], scope=["hr"])

    session = _mock_session([universal, code_only, legal_only, hr_transaction])
    ctx = EvaluationContext()

    # clause_set: universal + legal_only
    results = await select_rules(session, ctx, subject_type="clause_set", severity_min="LOW")
    result_ids = {r["id"] for r in results}
    assert result_ids == {"r1", "r3"}

    # transaction: universal + hr_transaction
    session = _mock_session([universal, code_only, legal_only, hr_transaction])
    results = await select_rules(session, ctx, subject_type="transaction", severity_min="LOW")
    result_ids = {r["id"] for r in results}
    assert result_ids == {"r1", "r4"}

    # code_diff: universal + code_only
    session = _mock_session([universal, code_only, legal_only, hr_transaction])
    results = await select_rules(session, ctx, subject_type="code_diff", severity_min="LOW")
    result_ids = {r["id"] for r in results}
    assert result_ids == {"r1", "r2"}

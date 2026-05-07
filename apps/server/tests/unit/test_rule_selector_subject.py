"""Tests for subject_type filtering in rule_selector.

Phase 7b: Verifies that select_rules filters by applicable_subject_types
when a subject_type parameter is provided.
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
    rule.applicable_subject_types = applicable_subject_types or ["code_change"]
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


@pytest.mark.asyncio
async def test_subject_type_filter_narrows_rules():
    """Rules not matching the subject_type are excluded."""
    code_rule = _make_rule("r1", applicable_subject_types=["code_change"])
    hr_rule = _make_rule("r2", applicable_subject_types=["hr_event"], scope=["hr"])
    both_rule = _make_rule("r3", applicable_subject_types=["code_change", "hr_event"])

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [code_rule, hr_rule, both_rule]
    mock_session.execute = AsyncMock(return_value=mock_result)

    ctx = EvaluationContext()

    # Filter for hr_event — should exclude the code-only rule
    results = await select_rules(mock_session, ctx, subject_type="hr_event", severity_min="LOW")
    result_ids = {r["id"] for r in results}
    assert "r2" in result_ids  # hr_event rule
    assert "r3" in result_ids  # both types
    assert "r1" not in result_ids  # code_change only


@pytest.mark.asyncio
async def test_no_subject_type_returns_all():
    """Without subject_type filter, all rules pass through."""
    code_rule = _make_rule("r1", applicable_subject_types=["code_change"])
    hr_rule = _make_rule("r2", applicable_subject_types=["hr_event"])

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [code_rule, hr_rule]
    mock_session.execute = AsyncMock(return_value=mock_result)

    ctx = EvaluationContext()

    # No subject_type — both rules should pass
    results = await select_rules(mock_session, ctx, subject_type=None, severity_min="LOW")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_subject_type_filter_with_missing_field():
    """Rules without applicable_subject_types default to ['code_change']."""
    rule_no_field = _make_rule("r1")
    # Simulate a rule that doesn't have the field yet
    rule_no_field.applicable_subject_types = None

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [rule_no_field]
    mock_session.execute = AsyncMock(return_value=mock_result)

    ctx = EvaluationContext()

    # code_change should match the default
    results = await select_rules(mock_session, ctx, subject_type="code_change", severity_min="LOW")
    assert len(results) == 1

    # hr_event should not match the default
    results = await select_rules(mock_session, ctx, subject_type="hr_event", severity_min="LOW")
    assert len(results) == 0

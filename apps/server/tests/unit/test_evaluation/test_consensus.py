"""Unit tests for consensus voting (Tier 1.4).

Tests cover:
- Consensus agreed (both DENY) for CRITICAL rules
- Consensus disagreed (DENY vs ALLOW) → NEEDS_CONFIRMATION
- Non-CRITICAL rules bypass consensus
- Non-DENY verdicts bypass consensus
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from rulerepo_server.services.evaluation.consensus import (
    ConsensusResult,
    check_consensus,
)


def _critical_rule(rule_id: str = "rule-1") -> dict:
    return {"id": rule_id, "severity": "CRITICAL", "statement": "No secrets in code"}


def _non_critical_rule(rule_id: str = "rule-2", severity: str = "HIGH") -> dict:
    return {"id": rule_id, "severity": severity, "statement": "Use type hints"}


class TestConsensusAgreed:
    """Both evaluations return DENY → consensus agreed, original verdict kept."""

    @pytest.mark.asyncio
    async def test_both_deny_returns_deny(self) -> None:
        evaluate_fn = AsyncMock(return_value={"verdict": "DENY", "reasoning": "Second opinion: secrets found"})
        result = await check_consensus(
            rule=_critical_rule(),
            first_verdict="DENY",
            first_reasoning="Secrets detected in diff",
            evaluate_fn=evaluate_fn,
            context={"diff": "some diff"},
        )
        assert isinstance(result, ConsensusResult)
        assert result.final_verdict == "DENY"
        assert result.consensus_agreed is True
        assert result.first_verdict == "DENY"
        assert result.second_verdict == "DENY"
        evaluate_fn.assert_awaited_once_with(rule=_critical_rule(), context={"diff": "some diff"})

    @pytest.mark.asyncio
    async def test_reasoning_is_from_first_evaluation(self) -> None:
        evaluate_fn = AsyncMock(return_value={"verdict": "DENY", "reasoning": "Second opinion agrees"})
        result = await check_consensus(
            rule=_critical_rule(),
            first_verdict="DENY",
            first_reasoning="Original reasoning",
            evaluate_fn=evaluate_fn,
            context={},
        )
        assert result.reasoning == "Original reasoning"


class TestConsensusDisagreed:
    """Evaluations disagree → NEEDS_CONFIRMATION with disagreement flag."""

    @pytest.mark.asyncio
    async def test_deny_vs_allow_returns_needs_confirmation(self) -> None:
        evaluate_fn = AsyncMock(return_value={"verdict": "ALLOW", "reasoning": "No issues found"})
        result = await check_consensus(
            rule=_critical_rule(),
            first_verdict="DENY",
            first_reasoning="Secrets detected",
            evaluate_fn=evaluate_fn,
            context={"diff": "some diff"},
        )
        assert result.final_verdict == "NEEDS_CONFIRMATION"
        assert result.consensus_agreed is False
        assert result.first_verdict == "DENY"
        assert result.second_verdict == "ALLOW"
        assert "Consensus disagreement" in result.reasoning

    @pytest.mark.asyncio
    async def test_deny_vs_needs_confirmation_returns_needs_confirmation(self) -> None:
        evaluate_fn = AsyncMock(return_value={"verdict": "NEEDS_CONFIRMATION", "reasoning": "Unclear"})
        result = await check_consensus(
            rule=_critical_rule(),
            first_verdict="DENY",
            first_reasoning="Might be a secret",
            evaluate_fn=evaluate_fn,
            context={},
        )
        assert result.final_verdict == "NEEDS_CONFIRMATION"
        assert result.consensus_agreed is False
        assert result.second_verdict == "NEEDS_CONFIRMATION"


class TestNonCriticalBypass:
    """Non-CRITICAL severity rules skip consensus entirely."""

    @pytest.mark.asyncio
    async def test_high_severity_bypasses_consensus(self) -> None:
        evaluate_fn = AsyncMock()
        result = await check_consensus(
            rule=_non_critical_rule(severity="HIGH"),
            first_verdict="DENY",
            first_reasoning="Violation found",
            evaluate_fn=evaluate_fn,
            context={},
        )
        assert result.final_verdict == "DENY"
        assert result.consensus_agreed is True
        assert result.second_verdict is None
        evaluate_fn.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_medium_severity_bypasses_consensus(self) -> None:
        evaluate_fn = AsyncMock()
        result = await check_consensus(
            rule=_non_critical_rule(severity="MEDIUM"),
            first_verdict="DENY",
            first_reasoning="Violation found",
            evaluate_fn=evaluate_fn,
            context={},
        )
        assert result.final_verdict == "DENY"
        assert result.consensus_agreed is True
        assert result.second_verdict is None
        evaluate_fn.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_low_severity_bypasses_consensus(self) -> None:
        evaluate_fn = AsyncMock()
        result = await check_consensus(
            rule=_non_critical_rule(severity="LOW"),
            first_verdict="DENY",
            first_reasoning="Minor issue",
            evaluate_fn=evaluate_fn,
            context={},
        )
        assert result.final_verdict == "DENY"
        assert result.consensus_agreed is True
        assert result.second_verdict is None
        evaluate_fn.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_severity_bypasses_consensus(self) -> None:
        evaluate_fn = AsyncMock()
        result = await check_consensus(
            rule={"id": "rule-x", "statement": "Some rule"},
            first_verdict="DENY",
            first_reasoning="Issue",
            evaluate_fn=evaluate_fn,
            context={},
        )
        assert result.final_verdict == "DENY"
        assert result.second_verdict is None
        evaluate_fn.assert_not_awaited()


class TestNonDenyBypass:
    """Non-DENY verdicts skip consensus even for CRITICAL rules."""

    @pytest.mark.asyncio
    async def test_allow_verdict_bypasses_consensus(self) -> None:
        evaluate_fn = AsyncMock()
        result = await check_consensus(
            rule=_critical_rule(),
            first_verdict="ALLOW",
            first_reasoning="All clear",
            evaluate_fn=evaluate_fn,
            context={},
        )
        assert result.final_verdict == "ALLOW"
        assert result.consensus_agreed is True
        assert result.second_verdict is None
        evaluate_fn.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_needs_confirmation_bypasses_consensus(self) -> None:
        evaluate_fn = AsyncMock()
        result = await check_consensus(
            rule=_critical_rule(),
            first_verdict="NEEDS_CONFIRMATION",
            first_reasoning="Unclear input",
            evaluate_fn=evaluate_fn,
            context={},
        )
        assert result.final_verdict == "NEEDS_CONFIRMATION"
        assert result.consensus_agreed is True
        assert result.second_verdict is None
        evaluate_fn.assert_not_awaited()


class TestCaseInsensitivity:
    """Severity and verdict matching should be case-insensitive."""

    @pytest.mark.asyncio
    async def test_lowercase_critical_deny_triggers_consensus(self) -> None:
        evaluate_fn = AsyncMock(return_value={"verdict": "DENY", "reasoning": "Confirmed"})
        result = await check_consensus(
            rule={"id": "r1", "severity": "critical", "statement": "Test"},
            first_verdict="deny",
            first_reasoning="Issue found",
            evaluate_fn=evaluate_fn,
            context={},
        )
        assert result.consensus_agreed is True
        assert result.first_verdict == "deny"
        assert result.second_verdict == "DENY"
        evaluate_fn.assert_awaited_once()

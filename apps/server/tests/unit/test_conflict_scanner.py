"""Unit tests for the Continuous Conflict Detector worker.

Tests cover the pure helper functions (scope overlap, similarity,
conflict detection) and the core scanning logic with mocked DB models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rulerepo_server.workers.conflict_scanner import (
    MAX_LLM_CANDIDATES,
    _scan_conflicts_with_session,
    compute_scope_overlap,
    compute_statement_similarity,
    is_contradictory_pair,
    is_potential_conflict,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeRule:
    """Minimal stand-in for RuleModel used in tests."""

    id: str = ""
    project_id: str = "00000000-0000-0000-0000-000000000001"
    statement: str = ""
    modality: str = "MUST"
    severity: str = "MEDIUM"
    status: str = "EFFECTIVE"
    scope: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# compute_scope_overlap
# ---------------------------------------------------------------------------


class TestComputeScopeOverlap:
    """Tests for the scope overlap pre-filter."""

    def test_no_overlap(self) -> None:
        assert compute_scope_overlap(["a", "b"], ["c", "d"]) == set()

    def test_full_overlap(self) -> None:
        assert compute_scope_overlap(["a", "b"], ["a", "b"]) == {"a", "b"}

    def test_partial_overlap(self) -> None:
        assert compute_scope_overlap(["a", "b", "c"], ["b", "c", "d"]) == {"b", "c"}

    def test_empty_left(self) -> None:
        assert compute_scope_overlap([], ["a"]) == set()

    def test_empty_right(self) -> None:
        assert compute_scope_overlap(["a"], []) == set()

    def test_both_empty(self) -> None:
        assert compute_scope_overlap([], []) == set()

    def test_single_shared_element(self) -> None:
        result = compute_scope_overlap(
            ["engineering/python", "security"],
            ["engineering/python", "legal"],
        )
        assert result == {"engineering/python"}


# ---------------------------------------------------------------------------
# compute_statement_similarity
# ---------------------------------------------------------------------------


class TestComputeStatementSimilarity:
    """Tests for statement similarity computation."""

    def test_identical_statements(self) -> None:
        assert compute_statement_similarity("foo bar", "foo bar") == 1.0

    def test_completely_different(self) -> None:
        sim = compute_statement_similarity("aaa", "zzz")
        assert sim < 0.2

    def test_case_insensitive(self) -> None:
        assert compute_statement_similarity("Hello World", "hello world") == 1.0

    def test_similar_statements(self) -> None:
        sim = compute_statement_similarity(
            "All functions must have type hints",
            "All functions must not have type hints",
        )
        assert sim > 0.5


# ---------------------------------------------------------------------------
# is_contradictory_pair
# ---------------------------------------------------------------------------


class TestIsContradictoryPair:
    """Tests for modality contradiction detection."""

    def test_must_vs_must_not(self) -> None:
        assert is_contradictory_pair("MUST", "MUST_NOT") is True

    def test_must_not_vs_must(self) -> None:
        assert is_contradictory_pair("MUST_NOT", "MUST") is True

    def test_must_vs_should(self) -> None:
        assert is_contradictory_pair("MUST", "SHOULD") is False

    def test_should_vs_may(self) -> None:
        assert is_contradictory_pair("SHOULD", "MAY") is False

    def test_same_modality(self) -> None:
        assert is_contradictory_pair("MUST", "MUST") is False


# ---------------------------------------------------------------------------
# is_potential_conflict
# ---------------------------------------------------------------------------


class TestIsPotentialConflict:
    """Tests for the combined conflict detection heuristic."""

    def test_conflict_detected(self) -> None:
        """Two rules with overlapping scope, contradictory modalities,
        and similar statements should be flagged."""
        assert is_potential_conflict(
            scope_a=["engineering/python"],
            scope_b=["engineering/python"],
            modality_a="MUST",
            modality_b="MUST_NOT",
            statement_a="All functions must have type hints",
            statement_b="All functions must not have type hints",
        )

    def test_no_scope_overlap(self) -> None:
        """No conflict if scopes do not overlap."""
        assert not is_potential_conflict(
            scope_a=["engineering/python"],
            scope_b=["legal/contracts"],
            modality_a="MUST",
            modality_b="MUST_NOT",
            statement_a="All functions must have type hints",
            statement_b="All functions must not have type hints",
        )

    def test_same_modality(self) -> None:
        """No conflict if modalities are not contradictory."""
        assert not is_potential_conflict(
            scope_a=["engineering/python"],
            scope_b=["engineering/python"],
            modality_a="MUST",
            modality_b="MUST",
            statement_a="All functions must have type hints",
            statement_b="All functions must have type hints",
        )

    def test_low_similarity(self) -> None:
        """No conflict if statements are too dissimilar."""
        assert not is_potential_conflict(
            scope_a=["engineering/python"],
            scope_b=["engineering/python"],
            modality_a="MUST",
            modality_b="MUST_NOT",
            statement_a="Use snake_case for variable names",
            statement_b="Deploy via Docker Compose only",
        )

    def test_custom_similarity_threshold(self) -> None:
        """Verify custom threshold is respected."""
        # These have some similarity but below a very high threshold
        result = is_potential_conflict(
            scope_a=["engineering/python"],
            scope_b=["engineering/python"],
            modality_a="MUST",
            modality_b="MUST_NOT",
            statement_a="All functions must have type hints",
            statement_b="All functions must not have type hints",
            similarity_threshold=0.99,
        )
        assert not result


# ---------------------------------------------------------------------------
# _scan_conflicts_with_session (integration with mocked session)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scanner_finds_conflicts() -> None:
    """Scanner should create a proposal for a contradictory pair."""
    rule_a = FakeRule(
        id=str(uuid4()),
        statement="All API endpoints must use authentication",
        modality="MUST",
        scope=["engineering/api"],
    )
    rule_b = FakeRule(
        id=str(uuid4()),
        statement="All API endpoints must not use authentication",
        modality="MUST_NOT",
        scope=["engineering/api"],
    )

    # Mock the session's execute to return our fake rules
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [rule_a, rule_b]
    mock_result.scalars.return_value = mock_scalars

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    with patch(
        "rulerepo_server.adapters.postgres.models.ProposalModel",
        new=_fake_proposal_model_class(),
    ):
        await _scan_conflicts_with_session(session)

    # A proposal should have been added to the session
    session.add.assert_called_once()
    proposal = session.add.call_args[0][0]
    assert "conflict" in proposal.title.lower()
    assert proposal.proposal_type == "resolve_conflict"
    assert proposal.author_id == "system:conflict_scanner"
    assert len(proposal.target_rule_ids) == 2


@pytest.mark.asyncio
async def test_scanner_skips_non_contradictory() -> None:
    """Scanner should not create proposals for non-contradictory pairs."""
    rule_a = FakeRule(
        id=str(uuid4()),
        statement="All API endpoints must use authentication",
        modality="MUST",
        scope=["engineering/api"],
    )
    rule_b = FakeRule(
        id=str(uuid4()),
        statement="All API endpoints should use rate limiting",
        modality="SHOULD",
        scope=["engineering/api"],
    )

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [rule_a, rule_b]
    mock_result.scalars.return_value = mock_scalars

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    await _scan_conflicts_with_session(session)

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_scanner_skips_no_scope_overlap() -> None:
    """Scanner should not flag rules with disjoint scopes."""
    rule_a = FakeRule(
        id=str(uuid4()),
        statement="All functions must have type hints",
        modality="MUST",
        scope=["engineering/python"],
    )
    rule_b = FakeRule(
        id=str(uuid4()),
        statement="All functions must not have type hints",
        modality="MUST_NOT",
        scope=["legal/contracts"],
    )

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [rule_a, rule_b]
    mock_result.scalars.return_value = mock_scalars

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    await _scan_conflicts_with_session(session)

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_scanner_fewer_than_two_rules() -> None:
    """Scanner should gracefully skip when fewer than 2 rules exist."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [FakeRule(id=str(uuid4()), statement="Only one rule")]
    mock_result.scalars.return_value = mock_scalars

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    await _scan_conflicts_with_session(session)

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_scanner_respects_candidate_limit() -> None:
    """Scanner should stop collecting candidates at MAX_LLM_CANDIDATES."""
    # Create enough rules that the combination count exceeds the limit.
    # With N rules sharing scope, we get N*(N-1)/2 pairs.
    # We need > MAX_LLM_CANDIDATES pairs, so N ~ 21 gives 210 pairs.
    n_rules = 21
    rules = [
        FakeRule(
            id=str(uuid4()),
            statement=f"Rule number {i}",
            modality="MUST" if i % 2 == 0 else "MUST_NOT",
            scope=["shared/scope"],
        )
        for i in range(n_rules)
    ]

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = rules
    mock_result.scalars.return_value = mock_scalars

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    with patch(
        "rulerepo_server.adapters.postgres.models.ProposalModel",
        new=_fake_proposal_model_class(),
    ):
        await _scan_conflicts_with_session(session)

    # The number of proposals created must not exceed MAX_LLM_CANDIDATES
    assert session.add.call_count <= MAX_LLM_CANDIDATES


# ---------------------------------------------------------------------------
# Helpers for mocking the ProposalModel import inside the function
# ---------------------------------------------------------------------------


def _fake_proposal_model_class() -> type:
    """Return a minimal stand-in for ProposalModel."""

    class _FakeProposal:
        def __init__(self, **kwargs: object) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    return _FakeProposal

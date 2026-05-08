"""Tests for the clause-level verdict aggregator.

Covers clause grouping, contract-level verdict derivation, and risk scoring.
"""

from __future__ import annotations

from rulerepo_server.domain.evaluation import (
    ContractClauseRemediation,
    RuleVerdict,
    Verdict,
)
from rulerepo_server.services.evaluation.clause_aggregator import (
    aggregate_clause_verdicts,
)


def _make_verdict(
    rule_id: str,
    verdict: Verdict,
    *,
    clause_id: str = "",
    confidence: float = 0.9,
    reasoning: str = "test",
) -> RuleVerdict:
    """Helper to create a RuleVerdict with optional clause remediation."""
    remediations = []
    if clause_id:
        remediations.append(
            ContractClauseRemediation(
                type="clause_revision",
                description="test remediation",
                clause_id=clause_id,
                revised_text="revised text",
                auto_applicable=False,
            )
        )
    return RuleVerdict(
        rule_id=rule_id,
        rule_statement="test rule",
        verdict=verdict,
        confidence=confidence,
        reasoning=reasoning,
        remediations=remediations,
    )


class TestClauseAggregator:
    """Tests for aggregate_clause_verdicts()."""

    def test_all_allow(self) -> None:
        verdicts = [
            _make_verdict("r1", Verdict.ALLOW, clause_id="art1"),
            _make_verdict("r2", Verdict.ALLOW, clause_id="art2"),
        ]
        result = aggregate_clause_verdicts(verdicts)

        assert result.contract_verdict == Verdict.ALLOW
        assert len(result.clause_verdict_map) == 2
        assert len(result.critical_clause_ids) == 0
        assert len(result.warning_clause_ids) == 0

    def test_deny_propagates_to_contract(self) -> None:
        verdicts = [
            _make_verdict("r1", Verdict.ALLOW, clause_id="art1"),
            _make_verdict("r2", Verdict.DENY, clause_id="art2"),
        ]
        result = aggregate_clause_verdicts(verdicts)

        assert result.contract_verdict == Verdict.DENY
        assert "art2" in result.critical_clause_ids
        assert result.clause_risk_scores["art2"] == 1.0

    def test_needs_confirmation_propagates(self) -> None:
        verdicts = [
            _make_verdict("r1", Verdict.ALLOW, clause_id="art1"),
            _make_verdict("r2", Verdict.NEEDS_CONFIRMATION, clause_id="art2"),
        ]
        result = aggregate_clause_verdicts(verdicts)

        assert result.contract_verdict == Verdict.NEEDS_CONFIRMATION
        assert "art2" in result.warning_clause_ids

    def test_deny_overrides_needs_confirmation(self) -> None:
        verdicts = [
            _make_verdict("r1", Verdict.NEEDS_CONFIRMATION, clause_id="art1"),
            _make_verdict("r2", Verdict.DENY, clause_id="art2"),
        ]
        result = aggregate_clause_verdicts(verdicts)

        assert result.contract_verdict == Verdict.DENY

    def test_multiple_verdicts_per_clause(self) -> None:
        verdicts = [
            _make_verdict("r1", Verdict.ALLOW, clause_id="art1"),
            _make_verdict("r2", Verdict.DENY, clause_id="art1"),
            _make_verdict("r3", Verdict.ALLOW, clause_id="art1"),
        ]
        result = aggregate_clause_verdicts(verdicts)

        assert result.contract_verdict == Verdict.DENY
        assert len(result.clause_verdict_map["art1"]) == 3
        assert "art1" in result.critical_clause_ids

    def test_risk_scores(self) -> None:
        verdicts = [
            _make_verdict("r1", Verdict.ALLOW, clause_id="art1"),
            _make_verdict("r2", Verdict.DENY, clause_id="art2"),
            _make_verdict("r3", Verdict.NEEDS_CONFIRMATION, clause_id="art3"),
        ]
        result = aggregate_clause_verdicts(verdicts)

        assert result.clause_risk_scores["art1"] == 0.0
        assert result.clause_risk_scores["art2"] == 1.0
        assert result.clause_risk_scores["art3"] == 0.5

    def test_empty_verdicts(self) -> None:
        result = aggregate_clause_verdicts([])

        assert result.contract_verdict == Verdict.ALLOW
        assert len(result.clause_verdict_map) == 0

    def test_unknown_clause_id_fallback(self) -> None:
        """Verdicts without clause_id in remediations fall back to 'unknown'."""
        verdicts = [
            RuleVerdict(
                rule_id="r1",
                rule_statement="test",
                verdict=Verdict.ALLOW,
                confidence=0.9,
                reasoning="no clause info",
            )
        ]
        result = aggregate_clause_verdicts(verdicts)

        assert "unknown" in result.clause_verdict_map

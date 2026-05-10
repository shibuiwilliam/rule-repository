"""Tests for domain-aware effectiveness scoring in health_scorer.

Verifies that the effectiveness dimension correctly handles different
rule domains: code (volume-based), legal (precision-based), transaction
(override-rate-based), and generic (balanced).
"""

from __future__ import annotations

from datetime import UTC, datetime

from rulerepo_server.services.intelligence.health_scorer import (
    classify_rule_status,
    compute_effectiveness,
    compute_health_score,
)


class TestComputeEffectiveness:
    """Tests for the compute_effectiveness function."""

    def test_code_rule_zero_evaluations_scores_zero(self):
        """Code rules with no evaluations score 0 (unchanged behavior)."""
        rule = {"applicable_subject_types": ["code_diff"], "modality": "MUST"}
        score = compute_effectiveness(rule, evaluation_count_90d=0)
        assert score == 0.0

    def test_code_rule_five_evaluations_scores_100(self):
        """Code rules with 5+ evaluations score 100."""
        rule = {"applicable_subject_types": ["code_diff"], "modality": "MUST"}
        score = compute_effectiveness(rule, evaluation_count_90d=5)
        assert score == 100.0

    def test_code_rule_two_evaluations_scores_40(self):
        """Code rules scale linearly: 2 evals * 20 = 40."""
        rule = {"applicable_subject_types": ["code_diff"], "modality": "MUST"}
        score = compute_effectiveness(rule, evaluation_count_90d=2)
        assert score == 40.0

    def test_legal_rule_no_evaluations_scores_50(self):
        """Legal rules with no evaluations score neutral (50)."""
        rule = {"applicable_subject_types": ["clause_set"], "modality": "MUST"}
        score = compute_effectiveness(rule, evaluation_count_90d=0)
        assert score == 50.0

    def test_legal_rule_correct_deny_rate_scores_high(self):
        """Legal rule with 2 evaluations and 1 DENY near expected rate scores well."""
        rule = {
            "applicable_subject_types": ["clause_set"],
            "modality": "SHOULD",  # expected deny rate = 0.1
            "expected_deny_rate": 0.5,  # explicit override
        }
        # 2 evals, 1 deny → actual rate 0.5, expected 0.5 → deviation 0 → score 100
        score = compute_effectiveness(rule, evaluation_count_90d=2, deny_count_90d=1)
        assert score == 100.0

    def test_legal_rule_wrong_deny_rate_scores_low(self):
        """Legal rule with deny rate far from expected scores poorly."""
        rule = {
            "applicable_subject_types": ["document"],
            "modality": "MUST",  # expected deny rate = 0.01
        }
        # 10 evals, 8 deny → actual rate 0.8, expected 0.01 → deviation 0.79
        score = compute_effectiveness(rule, evaluation_count_90d=10, deny_count_90d=8)
        assert score < 30.0

    def test_transaction_rule_no_evaluations_scores_50(self):
        """Transaction rules with no evaluations score neutral (50)."""
        rule = {"applicable_subject_types": ["transaction"], "modality": "MUST"}
        score = compute_effectiveness(rule, evaluation_count_90d=0)
        assert score == 50.0

    def test_transaction_rule_no_overrides_scores_100(self):
        """Transaction rule with denials but no overrides scores 100."""
        rule = {"applicable_subject_types": ["transaction"], "modality": "MUST"}
        score = compute_effectiveness(rule, evaluation_count_90d=50, deny_count_90d=10, override_count_90d=0)
        assert score == 100.0

    def test_transaction_rule_high_override_rate_scores_low(self):
        """Finance rule with 50 evaluations and 40 overrides of 50 denials scores low."""
        rule = {"applicable_subject_types": ["transaction"], "modality": "MUST"}
        score = compute_effectiveness(rule, evaluation_count_90d=50, deny_count_90d=50, override_count_90d=40)
        # override_rate = 40/50 = 0.8 → score = 100 - 80 = 20
        assert score == 20.0

    def test_event_rule_same_as_transaction(self):
        """Event rules use the same logic as transaction rules."""
        rule = {"applicable_subject_types": ["event"], "modality": "MUST"}
        score = compute_effectiveness(rule, evaluation_count_90d=20, deny_count_90d=5, override_count_90d=1)
        # override_rate = 1/5 = 0.2 → score = 100 - 20 = 80
        assert score == 80.0

    def test_generic_rule_no_evaluations_scores_50(self):
        """Generic rules with no evaluations score neutral (50)."""
        rule = {"applicable_subject_types": [], "modality": "MUST"}
        score = compute_effectiveness(rule, evaluation_count_90d=0)
        assert score == 50.0

    def test_generic_rule_with_evaluations(self):
        """Generic rules scale at 33 per eval."""
        rule = {"applicable_subject_types": [], "modality": "MUST"}
        score = compute_effectiveness(rule, evaluation_count_90d=2)
        assert score == 66.0

    def test_none_subject_types_treated_as_generic(self):
        """Rules with None applicable_subject_types use generic formula."""
        rule = {"modality": "MUST"}  # No applicable_subject_types key
        score = compute_effectiveness(rule, evaluation_count_90d=0)
        assert score == 50.0

    def test_transaction_rule_zero_denials(self):
        """Transaction rule that never denied scores 70 (permissive but not wrong)."""
        rule = {"applicable_subject_types": ["transaction"], "modality": "MUST"}
        score = compute_effectiveness(rule, evaluation_count_90d=20, deny_count_90d=0, override_count_90d=0)
        assert score == 70.0


class TestClassifyRuleStatus:
    """Tests for the classify_rule_status function."""

    def test_dormant_rule(self):
        """Rule with no evaluations and active > 90 days is dormant."""
        rule = {"applicable_subject_types": ["transaction"]}
        status = classify_rule_status(rule, evaluation_count_90d=0, days_active=100)
        assert status == "dormant"

    def test_not_dormant_if_recently_created(self):
        """Rule with no evaluations but active < 90 days is not dormant."""
        rule = {"applicable_subject_types": ["transaction"]}
        status = classify_rule_status(rule, evaluation_count_90d=0, days_active=30)
        assert status is None

    def test_ineffective_rule(self):
        """Rule with >50% override rate is ineffective."""
        rule = {"applicable_subject_types": ["transaction"]}
        status = classify_rule_status(rule, evaluation_count_90d=20, deny_count_90d=10, override_count_90d=6)
        assert status == "ineffective"

    def test_not_ineffective_if_low_overrides(self):
        """Rule with <50% override rate is not ineffective."""
        rule = {"applicable_subject_types": ["transaction"]}
        status = classify_rule_status(rule, evaluation_count_90d=20, deny_count_90d=10, override_count_90d=4)
        assert status is None

    def test_over_broad_rule(self):
        """Rule that fires frequently with >95% ALLOW rate is over-broad."""
        rule = {"applicable_subject_types": ["code_diff"]}
        status = classify_rule_status(rule, evaluation_count_90d=100, allow_count_90d=97, deny_count_90d=3)
        assert status == "over_broad"

    def test_not_over_broad_if_low_volume(self):
        """Rule with <10 evaluations can't be classified as over-broad."""
        rule = {"applicable_subject_types": ["code_diff"]}
        status = classify_rule_status(rule, evaluation_count_90d=5, allow_count_90d=5, deny_count_90d=0)
        assert status is None


class TestComputeHealthScoreEffectiveness:
    """Tests that compute_health_score integrates the new effectiveness dimension."""

    def test_backward_compatible_test_coverage_field(self):
        """Result includes test_coverage as alias for effectiveness."""
        rule = {
            "statement": "Test rule with enough text here",
            "applicable_subject_types": ["code_diff"],
            "modality": "MUST",
            "updated_at": datetime.now(tz=UTC),
        }
        result = compute_health_score(rule, evaluation_count_90d=3)
        assert "effectiveness" in result
        assert "test_coverage" in result
        assert result["test_coverage"] == result["effectiveness"]

    def test_legal_rule_not_penalized_for_low_eval_count(self):
        """Legal rule with only 2 evaluations is not penalized like code rules would be."""
        rule = {
            "statement": "Contract must include liability cap clause",
            "applicable_subject_types": ["clause_set"],
            "modality": "MUST",
            "expected_deny_rate": 0.5,
            "updated_at": datetime.now(tz=UTC),
        }
        # 2 evals, 1 deny → perfect alignment with expected rate
        result = compute_health_score(rule, evaluation_count_90d=2, deny_count_90d=1, owner_active=True)
        assert result["effectiveness"] == 100.0

    def test_new_rule_neutral_effectiveness(self):
        """A new generic rule with no evaluations scores 50 effectiveness."""
        rule = {
            "statement": "All employees must complete onboarding",
            "modality": "MUST",
            "updated_at": datetime.now(tz=UTC),
        }
        result = compute_health_score(rule, evaluation_count_90d=0)
        assert result["effectiveness"] == 50.0

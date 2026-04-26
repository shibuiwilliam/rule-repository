"""Unit tests for intelligence health scorer and recommender."""

from datetime import datetime, timedelta, timezone

from rulerepo_server.services.intelligence.health_scorer import (
    compute_completeness,
    compute_freshness,
    compute_health_score,
)
from rulerepo_server.services.intelligence.recommender import generate_recommendations


class TestComputeCompleteness:
    def test_full_rule(self) -> None:
        rule = {
            "statement": "All deployments must go through staging first",
            "rationale": "Prevents bugs in production",
            "scope": ["engineering"],
            "modality": "MUST",
            "tags": ["deployment"],
            "source_refs": [{"document_id": "doc1"}],
            "governance": {"owner": "eng-lead"},
        }
        score, issues = compute_completeness(rule)
        assert score == 100.0
        assert len(issues) == 0

    def test_empty_rule(self) -> None:
        rule: dict = {"statement": "x"}
        score, issues = compute_completeness(rule)
        assert score < 50
        assert len(issues) > 0

    def test_partial_rule(self) -> None:
        rule = {
            "statement": "Engineers must write tests for all APIs",
            "rationale": "Catch regressions early",
            "modality": "MUST",
        }
        score, issues = compute_completeness(rule)
        assert 30 < score < 70


class TestComputeFreshness:
    def test_recently_updated(self) -> None:
        now = datetime.now(tz=timezone.utc)
        rule = {"updated_at": now - timedelta(days=5)}
        assert compute_freshness(rule, now=now) == 100.0

    def test_old_rule(self) -> None:
        now = datetime.now(tz=timezone.utc)
        rule = {"updated_at": now - timedelta(days=400)}
        assert compute_freshness(rule, now=now) == 0.0

    def test_mid_age_rule(self) -> None:
        now = datetime.now(tz=timezone.utc)
        rule = {"updated_at": now - timedelta(days=180)}
        score = compute_freshness(rule, now=now)
        assert 0 < score < 100

    def test_missing_date(self) -> None:
        assert compute_freshness({}) == 0.0


class TestComputeHealthScore:
    def test_healthy_rule(self) -> None:
        rule = {
            "statement": "All code must be reviewed before merging",
            "rationale": "Quality assurance",
            "scope": ["engineering"],
            "modality": "MUST",
            "tags": ["code-review"],
            "source_refs": [{"document_id": "doc1"}],
            "governance": {"owner": "tech-lead"},
            "updated_at": datetime.now(tz=timezone.utc),
        }
        result = compute_health_score(rule, evaluation_count_90d=15, owner_active=True)
        assert result["overall_score"] > 60
        assert len(result["issues"]) == 0

    def test_dormant_rule(self) -> None:
        rule = {
            "statement": "Unused rule with no evaluations",
            "updated_at": datetime.now(tz=timezone.utc) - timedelta(days=200),
        }
        result = compute_health_score(rule, evaluation_count_90d=0)
        all_issues = " ".join(result["issues"]).lower()
        assert "evaluated" in all_issues or "dormant" in all_issues


class TestRecommender:
    def test_dormant_rule_gets_retire_suggestion(self) -> None:
        rule = {"id": "abc", "modality": "MUST"}
        health = {"completeness": 80, "clarity": 70}
        analytics = {"total_evaluations": 0}
        recs = generate_recommendations(rule, health, analytics)
        assert any(r["type"] == "retire" for r in recs)

    def test_ambiguous_rule_gets_clarify_suggestion(self) -> None:
        rule = {"id": "abc", "modality": "MUST"}
        health = {"completeness": 80}
        analytics = {"total_evaluations": 20, "needs_confirmation_rate": 0.4, "deny_rate": 0.1, "allow_rate": 0.5}
        recs = generate_recommendations(rule, health, analytics)
        assert any(r["type"] == "clarify" for r in recs)

    def test_should_rule_with_full_compliance_gets_strengthen(self) -> None:
        rule = {"id": "abc", "modality": "SHOULD"}
        health = {"completeness": 80}
        analytics = {"total_evaluations": 15, "allow_rate": 1.0, "deny_rate": 0, "needs_confirmation_rate": 0}
        recs = generate_recommendations(rule, health, analytics)
        assert any(r["type"] == "strengthen" for r in recs)

    def test_no_recommendations_for_healthy_rule(self) -> None:
        rule = {"id": "abc", "modality": "MUST"}
        health = {"completeness": 90}
        analytics = {"total_evaluations": 10, "allow_rate": 0.8, "deny_rate": 0.1, "needs_confirmation_rate": 0.1}
        recs = generate_recommendations(rule, health, analytics)
        assert len(recs) == 0

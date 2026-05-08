"""Tests for verdict drift detection (RR-024)."""

from __future__ import annotations

from rulerepo_server.services.intelligence.drift_detector import (
    DriftDetector,
    VerdictHistory,
)


class TestDriftDetector:
    def test_no_drift_with_consistent_verdicts(self) -> None:
        detector = DriftDetector(window_size=5)
        for _ in range(20):
            alert = detector.record_verdict("rule-1", "ALLOW")
        assert alert is None

    def test_detects_drift_when_verdict_changes(self) -> None:
        detector = DriftDetector(window_size=5, alert_threshold=0.3)
        # First 10: all ALLOW
        for _ in range(10):
            detector.record_verdict("rule-1", "ALLOW")
        # Next 10: all DENY
        for _ in range(10):
            detector.record_verdict("rule-1", "DENY")
        # Should have detected drift at some point during the transition
        alerts = detector.get_alerts(rule_id="rule-1")
        assert len(alerts) > 0
        assert any(a.drift_score > 0.3 for a in alerts)

    def test_no_alert_below_window(self) -> None:
        detector = DriftDetector(window_size=50)
        for _ in range(10):
            alert = detector.record_verdict("rule-1", "ALLOW")
        assert alert is None

    def test_get_history(self) -> None:
        detector = DriftDetector(window_size=5)
        detector.record_verdict("rule-1", "ALLOW")
        detector.record_verdict("rule-1", "DENY")
        history = detector.get_history("rule-1")
        assert len(history.verdicts) == 2

    def test_separate_rule_histories(self) -> None:
        detector = DriftDetector(window_size=5)
        detector.record_verdict("rule-1", "ALLOW")
        detector.record_verdict("rule-2", "DENY")
        assert len(detector.get_history("rule-1").verdicts) == 1
        assert len(detector.get_history("rule-2").verdicts) == 1

    def test_get_alerts_unfiltered(self) -> None:
        detector = DriftDetector(window_size=5, alert_threshold=0.3)
        for _ in range(10):
            detector.record_verdict("rule-1", "ALLOW")
        for _ in range(10):
            detector.record_verdict("rule-1", "DENY")
        alerts = detector.get_alerts()
        assert len(alerts) >= 1

    def test_get_alerts_filtered_by_rule(self) -> None:
        detector = DriftDetector(window_size=5, alert_threshold=0.3)
        for _ in range(10):
            detector.record_verdict("rule-1", "ALLOW")
        for _ in range(10):
            detector.record_verdict("rule-1", "DENY")
        assert len(detector.get_alerts(rule_id="rule-1")) >= 1
        assert len(detector.get_alerts(rule_id="rule-2")) == 0

    def test_history_window_trimming(self) -> None:
        detector = DriftDetector(window_size=5)
        for i in range(200):
            detector.record_verdict("rule-1", "ALLOW")
        # History should be trimmed to at most window_size * 2
        history = detector.get_history("rule-1")
        assert len(history.verdicts) <= 10

    def test_verdict_history_dataclass(self) -> None:
        vh = VerdictHistory(rule_id="r1")
        assert vh.rule_id == "r1"
        assert vh.verdicts == []

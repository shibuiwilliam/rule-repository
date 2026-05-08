"""Verdict drift detection — alerts when the same rule+input produces different verdicts (RR-024).

Monitors verdict stability over time. When a rule that previously
produced ALLOW starts producing DENY (or vice versa) on semantically
similar inputs, this indicates model drift requiring investigation.

See IMPROVEMENT.md §10.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DriftAlert:
    """Alert raised when verdict distribution shifts beyond the threshold."""

    rule_id: str
    previous_verdict: str
    current_verdict: str
    drift_score: float  # 0-1, how significant the drift is
    sample_count: int
    detected_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass
class VerdictHistory:
    """Recorded verdict history for a single rule."""

    rule_id: str
    verdicts: list[tuple[str, datetime]] = field(default_factory=list)


class DriftDetector:
    """Tracks verdict history per rule and detects distribution shifts.

    Uses a sliding-window approach: compares the verdict distribution in
    the older half of the window against the newer half. When the total
    variation distance exceeds *alert_threshold*, a DriftAlert is raised.

    Args:
        window_size: Minimum number of verdicts before drift detection activates.
        alert_threshold: Total-variation distance threshold in [0, 1].
    """

    def __init__(self, window_size: int = 50, alert_threshold: float = 0.3) -> None:
        self._window_size = window_size
        self._alert_threshold = alert_threshold
        self._history: dict[str, list[tuple[str, datetime]]] = {}
        self._alerts: list[DriftAlert] = []

    def record_verdict(self, rule_id: str, verdict: str) -> DriftAlert | None:
        """Record a verdict and check for drift.

        Args:
            rule_id: The rule that was evaluated.
            verdict: The verdict label produced by the evaluation.

        Returns:
            A DriftAlert if drift was detected, otherwise None.
        """
        now = datetime.now(tz=UTC)
        if rule_id not in self._history:
            self._history[rule_id] = []

        history = self._history[rule_id]
        history.append((verdict, now))

        # Keep only the window
        if len(history) > self._window_size * 2:
            history[:] = history[-self._window_size * 2 :]

        # Need at least window_size samples to detect drift
        if len(history) < self._window_size:
            return None

        # Compare recent window vs older window
        mid = len(history) // 2
        old_window = history[:mid]
        new_window = history[mid:]

        old_dist = self._compute_distribution(old_window)
        new_dist = self._compute_distribution(new_window)

        drift_score = self._compute_drift_score(old_dist, new_dist)

        if drift_score > self._alert_threshold:
            # Find the dominant shift
            old_dominant = max(old_dist, key=old_dist.get) if old_dist else "UNKNOWN"
            new_dominant = max(new_dist, key=new_dist.get) if new_dist else "UNKNOWN"

            alert = DriftAlert(
                rule_id=rule_id,
                previous_verdict=old_dominant,
                current_verdict=new_dominant,
                drift_score=drift_score,
                sample_count=len(history),
            )
            self._alerts.append(alert)

            logger.warning(
                "verdict_drift_detected",
                rule_id=rule_id,
                drift_score=drift_score,
                old_dominant=old_dominant,
                new_dominant=new_dominant,
            )
            return alert

        return None

    @staticmethod
    def _compute_distribution(
        window: list[tuple[str, datetime]],
    ) -> dict[str, float]:
        """Return the relative frequency of each verdict in the window."""
        if not window:
            return {}
        counts: dict[str, int] = {}
        for verdict, _ in window:
            counts[verdict] = counts.get(verdict, 0) + 1
        total = len(window)
        return {v: c / total for v, c in counts.items()}

    @staticmethod
    def _compute_drift_score(old_dist: dict[str, float], new_dist: dict[str, float]) -> float:
        """Compute the total variation distance between two distributions.

        Returns a value in [0, 1] where 0 means identical distributions
        and 1 means completely disjoint support.
        """
        all_verdicts = set(old_dist) | set(new_dist)
        if not all_verdicts:
            return 0.0

        total_diff = 0.0
        for v in all_verdicts:
            old_p = old_dist.get(v, 0.0)
            new_p = new_dist.get(v, 0.0)
            total_diff += abs(old_p - new_p)

        return total_diff / 2.0  # Normalize to 0-1

    def get_alerts(self, *, rule_id: str | None = None) -> list[DriftAlert]:
        """Return recorded drift alerts, optionally filtered by rule_id."""
        if rule_id:
            return [a for a in self._alerts if a.rule_id == rule_id]
        return list(self._alerts)

    def get_history(self, rule_id: str) -> VerdictHistory:
        """Return the verdict history for a given rule."""
        verdicts = self._history.get(rule_id, [])
        return VerdictHistory(rule_id=rule_id, verdicts=verdicts)

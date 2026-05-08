"""Drift detector — compares two HarnessReports to detect quality regressions.

Usage:
    detector = DriftDetector(threshold=0.02)
    alerts = detector.compare(baseline_report, candidate_report)
    for alert in alerts:
        if alert.is_regression:
            print(f"REGRESSION: {alert.domain} {alert.metric} dropped {alert.delta:.4f}")
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import HarnessReport


@dataclass(frozen=True)
class DriftAlert:
    """A detected metric change between two harness runs.

    Attributes:
        domain: Domain where the drift was detected, or "overall".
        metric: Name of the metric (e.g., "f1", "precision", "recall").
        old_value: Value in the baseline report.
        new_value: Value in the candidate report.
        delta: new_value - old_value (negative means regression).
        threshold: The configured regression threshold.
        is_regression: True if the drop exceeds the threshold.
    """

    domain: str
    metric: str
    old_value: float
    new_value: float
    delta: float
    threshold: float
    is_regression: bool


class DriftDetector:
    """Compares two HarnessReports and detects quality regressions.

    Args:
        threshold: Minimum F1/precision/recall drop to flag as regression.
            Default is 0.02 (2 percentage points).
    """

    def __init__(self, threshold: float = 0.02) -> None:
        self._threshold = threshold

    def compare(
        self,
        baseline: HarnessReport,
        candidate: HarnessReport,
    ) -> list[DriftAlert]:
        """Compare baseline and candidate reports for regressions.

        Checks F1, precision, and recall for each domain, plus overall F1.

        Args:
            baseline: The reference report (typically from the last stable run).
            candidate: The new report to compare against baseline.

        Returns:
            List of DriftAlert instances for all detected metric changes.
            Only metrics that changed are included.
        """
        alerts: list[DriftAlert] = []

        baseline_domains = {d.domain: d for d in baseline.domains}
        candidate_domains = {d.domain: d for d in candidate.domains}

        all_domains = sorted(set(baseline_domains.keys()) | set(candidate_domains.keys()))

        for domain in all_domains:
            base = baseline_domains.get(domain)
            cand = candidate_domains.get(domain)

            if base is None or cand is None:
                # Domain added or removed — not a regression, but noteworthy
                continue

            for metric in ("f1", "precision", "recall"):
                old_val = getattr(base, metric)
                new_val = getattr(cand, metric)
                delta = new_val - old_val

                if abs(delta) < 1e-9:
                    continue

                alerts.append(
                    DriftAlert(
                        domain=domain,
                        metric=metric,
                        old_value=old_val,
                        new_value=new_val,
                        delta=round(delta, 6),
                        threshold=self._threshold,
                        is_regression=delta < -self._threshold,
                    )
                )

            # Average latency drift (flag if >20% increase)
            if base.avg_latency_ms > 0:
                latency_ratio = cand.avg_latency_ms / base.avg_latency_ms
                if latency_ratio > 1.2 or latency_ratio < 0.8:
                    delta = cand.avg_latency_ms - base.avg_latency_ms
                    alerts.append(
                        DriftAlert(
                            domain=domain,
                            metric="avg_latency_ms",
                            old_value=base.avg_latency_ms,
                            new_value=cand.avg_latency_ms,
                            delta=round(delta, 2),
                            threshold=base.avg_latency_ms * 0.2,
                            is_regression=latency_ratio > 1.2,
                        )
                    )

        # Overall F1
        overall_delta = candidate.overall_f1 - baseline.overall_f1
        if abs(overall_delta) > 1e-9:
            alerts.append(
                DriftAlert(
                    domain="overall",
                    metric="f1",
                    old_value=baseline.overall_f1,
                    new_value=candidate.overall_f1,
                    delta=round(overall_delta, 6),
                    threshold=self._threshold,
                    is_regression=overall_delta < -self._threshold,
                )
            )

        return alerts

    def has_regressions(
        self,
        baseline: HarnessReport,
        candidate: HarnessReport,
    ) -> bool:
        """Quick check: does the candidate have any regressions vs baseline?

        Args:
            baseline: The reference report.
            candidate: The new report.

        Returns:
            True if any DriftAlert has is_regression=True.
        """
        alerts = self.compare(baseline, candidate)
        return any(a.is_regression for a in alerts)

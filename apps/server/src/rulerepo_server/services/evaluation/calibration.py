"""Verdict confidence calibration using conformal prediction (RR-022).

LLM-reported confidence is often poorly calibrated. This module uses
conformal prediction to provide calibrated confidence intervals with
guaranteed coverage rates.

See IMPROVEMENT.md §6.3.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CalibrationResult:
    """Result of calibrating a verdict's confidence score."""

    raw_confidence: float
    calibrated_confidence: float
    prediction_set: list[str]  # verdicts that can't be excluded at the given confidence level
    coverage_guarantee: float  # e.g., 0.90 means 90% coverage


class ConformalCalibrator:
    """Calibrates verdict confidence using split conformal prediction.

    Maintains a calibration set of historical (predicted, actual) pairs
    and computes nonconformity scores to generate prediction sets with
    guaranteed coverage.
    """

    def __init__(self, target_coverage: float = 0.90) -> None:
        self.target_coverage = target_coverage
        self._calibration_data: list[tuple[str, float, str]] = []
        # (predicted_verdict, raw_confidence, actual_verdict)
        self._threshold: float | None = None

    def add_calibration_point(self, predicted: str, confidence: float, actual: str) -> None:
        """Add a calibration data point from a verified evaluation."""
        self._calibration_data.append((predicted, confidence, actual))
        self._threshold = None  # invalidate cached threshold

    def _compute_threshold(self) -> float:
        """Compute the conformal threshold from calibration data."""
        if not self._calibration_data:
            return 0.5  # uninformed prior

        # Nonconformity scores: 1 - confidence when correct, confidence when wrong
        scores: list[float] = []
        for predicted, confidence, actual in self._calibration_data:
            if predicted == actual:
                scores.append(1.0 - confidence)
            else:
                scores.append(confidence)

        scores.sort()
        n = len(scores)
        # Quantile index for desired coverage
        q = math.ceil((n + 1) * self.target_coverage) - 1
        q = min(q, n - 1)

        return scores[q]

    @property
    def threshold(self) -> float:
        """Return the cached conformal threshold, recomputing if invalidated."""
        if self._threshold is None:
            self._threshold = self._compute_threshold()
        return self._threshold

    def calibrate(self, verdict: str, raw_confidence: float) -> CalibrationResult:
        """Calibrate a verdict's confidence and generate a prediction set.

        The prediction set includes all verdicts whose nonconformity
        score is below the threshold, providing guaranteed coverage.

        Args:
            verdict: The predicted verdict label.
            raw_confidence: The raw LLM-reported confidence in [0, 1].

        Returns:
            A CalibrationResult with calibrated confidence and prediction set.
        """
        all_verdicts = ["ALLOW", "DENY", "NEEDS_CONFIRMATION"]
        threshold = self.threshold

        # Build prediction set
        prediction_set: list[str] = []
        for v in all_verdicts:
            score = 1.0 - raw_confidence if v == verdict else raw_confidence

            if score <= threshold:
                prediction_set.append(v)

        # If prediction set is empty, include at least the predicted verdict
        if not prediction_set:
            prediction_set = [verdict]

        # Calibrated confidence = 1 - (size of prediction set / total verdicts)
        calibrated = 1.0 - (len(prediction_set) - 1) / len(all_verdicts)
        calibrated = max(0.0, min(1.0, calibrated))

        logger.debug(
            "confidence_calibrated",
            raw=raw_confidence,
            calibrated=calibrated,
            prediction_set=prediction_set,
            threshold=threshold,
        )

        return CalibrationResult(
            raw_confidence=raw_confidence,
            calibrated_confidence=calibrated,
            prediction_set=prediction_set,
            coverage_guarantee=self.target_coverage,
        )

    @property
    def calibration_size(self) -> int:
        """Return the number of calibration data points."""
        return len(self._calibration_data)

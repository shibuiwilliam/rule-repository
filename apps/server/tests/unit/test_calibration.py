"""Tests for conformal prediction calibration (RR-022)."""

from __future__ import annotations

from rulerepo_server.services.evaluation.calibration import (
    CalibrationResult,
    ConformalCalibrator,
)


class TestConformalCalibrator:
    def test_empty_calibration_returns_default_threshold(self) -> None:
        cal = ConformalCalibrator()
        assert cal.threshold == 0.5

    def test_calibrate_high_confidence(self) -> None:
        cal = ConformalCalibrator(target_coverage=0.90)
        result = cal.calibrate("ALLOW", 0.95)
        assert result.raw_confidence == 0.95
        assert "ALLOW" in result.prediction_set

    def test_calibrate_low_confidence_expands_set(self) -> None:
        cal = ConformalCalibrator(target_coverage=0.90)
        result = cal.calibrate("DENY", 0.3)
        assert len(result.prediction_set) >= 1

    def test_add_calibration_points(self) -> None:
        cal = ConformalCalibrator()
        cal.add_calibration_point("ALLOW", 0.9, "ALLOW")
        cal.add_calibration_point("DENY", 0.8, "DENY")
        cal.add_calibration_point("ALLOW", 0.7, "DENY")  # wrong prediction
        assert cal.calibration_size == 3

    def test_calibration_with_data(self) -> None:
        cal = ConformalCalibrator(target_coverage=0.90)
        # Add well-calibrated data
        for _ in range(10):
            cal.add_calibration_point("ALLOW", 0.9, "ALLOW")
        cal.add_calibration_point("DENY", 0.8, "DENY")

        result = cal.calibrate("ALLOW", 0.9)
        assert result.calibrated_confidence > 0
        assert result.coverage_guarantee == 0.90

    def test_calibration_result_fields(self) -> None:
        result = CalibrationResult(
            raw_confidence=0.8,
            calibrated_confidence=0.67,
            prediction_set=["ALLOW", "NEEDS_CONFIRMATION"],
            coverage_guarantee=0.90,
        )
        assert result.raw_confidence == 0.8
        assert result.calibrated_confidence == 0.67
        assert len(result.prediction_set) == 2

    def test_threshold_invalidated_on_new_data(self) -> None:
        cal = ConformalCalibrator()
        _ = cal.threshold  # compute and cache
        cal.add_calibration_point("ALLOW", 0.9, "ALLOW")
        # Threshold should be recomputed after new data
        assert cal._threshold is None

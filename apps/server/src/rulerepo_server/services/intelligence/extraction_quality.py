"""Extraction quality metrics -- tracks accuracy of LLM-based rule extraction (RR-035).

Measures precision, recall, and F1 of the extraction pipeline by
comparing extracted rules against human-reviewed ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractionMetrics:
    """Aggregate extraction quality metrics."""

    total_extracted: int = 0
    true_positives: int = 0  # correctly extracted, accepted by human
    false_positives: int = 0  # extracted but rejected by human
    false_negatives: int = 0  # missed by extraction, added by human
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0


class ExtractionQualityTracker:
    """Tracks extraction quality over time.

    Records extraction outcomes (accepted, rejected, manually added)
    and computes precision / recall / F1 on demand.
    """

    def __init__(self) -> None:
        self._total_extracted: int = 0
        self._accepted: int = 0
        self._rejected: int = 0
        self._manually_added: int = 0

    def record_extraction(self, extracted_count: int) -> None:
        """Record the number of rules produced by an extraction run."""
        self._total_extracted += extracted_count

    def record_review(self, accepted: int, rejected: int) -> None:
        """Record human review outcomes for extracted rules."""
        self._accepted += accepted
        self._rejected += rejected

    def record_manual_addition(self, count: int = 1) -> None:
        """Record rules added manually (missed by extraction)."""
        self._manually_added += count

    def compute_metrics(self) -> ExtractionMetrics:
        """Compute precision, recall, and F1 from accumulated counts.

        Returns:
            An ExtractionMetrics dataclass with computed scores.
        """
        tp = self._accepted
        fp = self._rejected
        fn = self._manually_added

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        metrics = ExtractionMetrics(
            total_extracted=self._total_extracted,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=round(precision, 3),
            recall=round(recall, 3),
            f1=round(f1, 3),
        )
        logger.info("extraction_quality", **vars(metrics))
        return metrics

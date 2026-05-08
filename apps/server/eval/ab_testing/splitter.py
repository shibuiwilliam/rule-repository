"""A/B testing splitter — assigns golden cases to variants and compares results.

Usage:
    splitter = ABSplitter(split_ratio=0.5, seed=42)
    group_a, group_b = splitter.split(cases)
    # Run group_a with model A, group_b with model B
    result = splitter.compare(report_a, report_b)
    print(f"Winner: {'A' if result.a_is_better else 'B'}, p={result.p_value:.4f}")
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from ..models import DomainReport, GoldenCase


@dataclass(frozen=True)
class ABResult:
    """Result of comparing two variants (control A vs candidate B).

    Attributes:
        domain: Domain compared.
        a_correct: Count of correct verdicts in variant A.
        a_total: Total cases in variant A.
        b_correct: Count of correct verdicts in variant B.
        b_total: Total cases in variant B.
        a_proportion: Proportion correct for A.
        b_proportion: Proportion correct for B.
        z_score: Z-score from a two-proportion z-test.
        p_value: Two-tailed p-value.
        is_significant: Whether the difference is statistically significant
            at the configured alpha level (default 0.05).
        a_is_better: True if A has a higher proportion (and significant).
        a_f1: F1 score for variant A.
        b_f1: F1 score for variant B.
    """

    domain: str
    a_correct: int
    a_total: int
    b_correct: int
    b_total: int
    a_proportion: float
    b_proportion: float
    z_score: float
    p_value: float
    is_significant: bool
    a_is_better: bool
    a_f1: float
    b_f1: float


def _normal_cdf(x: float) -> float:
    """Approximate the standard normal CDF using the error function.

    Uses the relationship: Phi(x) = 0.5 * (1 + erf(x / sqrt(2))).
    """
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _two_proportion_z_test(
    n1: int,
    p1: float,
    n2: int,
    p2: float,
) -> tuple[float, float]:
    """Two-proportion z-test for equality of proportions.

    Args:
        n1: Sample size for group 1.
        p1: Observed proportion for group 1.
        n2: Sample size for group 2.
        p2: Observed proportion for group 2.

    Returns:
        Tuple of (z_score, two_tailed_p_value).
    """
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0

    # Pooled proportion
    p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)

    # Avoid division by zero when pooled proportion is 0 or 1
    if p_pool <= 0 or p_pool >= 1:
        return 0.0, 1.0

    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se < 1e-12:
        return 0.0, 1.0

    z = (p1 - p2) / se
    p_value = 2.0 * (1.0 - _normal_cdf(abs(z)))
    return z, p_value


class ABSplitter:
    """Splits golden cases into two groups and compares variant results.

    Assignment is deterministic: cases are hashed and assigned based on
    whether the hash falls in the A or B bucket. This ensures the same
    case always goes to the same group for a given seed.

    Args:
        split_ratio: Proportion of cases assigned to variant A (default 0.5).
        seed: Seed for deterministic assignment (default 42).
        alpha: Significance level for the z-test (default 0.05).
    """

    def __init__(
        self,
        split_ratio: float = 0.5,
        seed: int = 42,
        alpha: float = 0.05,
    ) -> None:
        if not 0.0 < split_ratio < 1.0:
            raise ValueError("split_ratio must be between 0 and 1 (exclusive)")
        self._split_ratio = split_ratio
        self._seed = seed
        self._alpha = alpha

    def _assign(self, case_id: str) -> str:
        """Deterministically assign a case to variant 'A' or 'B'.

        Args:
            case_id: The unique case identifier.

        Returns:
            'A' or 'B'.
        """
        digest = hashlib.sha256(f"{self._seed}:{case_id}".encode()).hexdigest()
        # Use first 8 hex chars as a fraction of the hash space
        hash_frac = int(digest[:8], 16) / 0xFFFFFFFF
        return "A" if hash_frac < self._split_ratio else "B"

    def split(
        self,
        cases: list[GoldenCase],
    ) -> tuple[list[GoldenCase], list[GoldenCase]]:
        """Split cases into variant A and variant B groups.

        Args:
            cases: All golden cases to split.

        Returns:
            Tuple of (group_a, group_b).
        """
        group_a: list[GoldenCase] = []
        group_b: list[GoldenCase] = []

        for case in cases:
            if self._assign(case.id) == "A":
                group_a.append(case)
            else:
                group_b.append(case)

        return group_a, group_b

    def compare(
        self,
        report_a: DomainReport,
        report_b: DomainReport,
    ) -> ABResult:
        """Compare two variant reports using a two-proportion z-test.

        Args:
            report_a: DomainReport from running variant A.
            report_b: DomainReport from running variant B.

        Returns:
            ABResult with statistical comparison.
        """
        a_total = report_a.total
        b_total = report_b.total
        a_correct = report_a.correct_verdict
        b_correct = report_b.correct_verdict

        a_prop = a_correct / a_total if a_total > 0 else 0.0
        b_prop = b_correct / b_total if b_total > 0 else 0.0

        z_score, p_value = _two_proportion_z_test(a_total, a_prop, b_total, b_prop)

        is_significant = p_value < self._alpha
        a_is_better = is_significant and a_prop > b_prop

        return ABResult(
            domain=report_a.domain,
            a_correct=a_correct,
            a_total=a_total,
            b_correct=b_correct,
            b_total=b_total,
            a_proportion=round(a_prop, 4),
            b_proportion=round(b_prop, 4),
            z_score=round(z_score, 4),
            p_value=round(p_value, 6),
            is_significant=is_significant,
            a_is_better=a_is_better,
            a_f1=report_a.f1,
            b_f1=report_b.f1,
        )

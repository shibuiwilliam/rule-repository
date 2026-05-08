"""Per-domain effectiveness weights (RR-039).

Different domains weigh the three effectiveness metrics differently:
- Engineering: precision 0.4, prevention 0.35, adoption 0.25
- HR: precision 0.2, prevention 0.5, adoption 0.3 (prevention dominates)
- Legal: precision 0.5, prevention 0.3, adoption 0.2 (precision dominates)
- Finance: precision 0.4, prevention 0.4, adoption 0.2
- Sales: precision 0.3, prevention 0.2, adoption 0.5 (adoption matters most)

The composite effectiveness score in ``effectiveness.py`` uses global
constants. This module provides domain-aware weights so each domain
can tune what "effective" means in its context.
"""

from __future__ import annotations

from dataclasses import dataclass

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class EffectivenessWeights:
    """Weights for the three effectiveness metrics.

    All three values should sum to 1.0.

    Attributes:
        precision: Weight for precision (true positive rate).
        prevention: Weight for prevention rate (issue reduction).
        adoption: Weight for agent/user adoption rate.
    """

    precision: float
    prevention: float
    adoption: float

    def compute_score(
        self,
        precision_score: float,
        prevention_score: float,
        adoption_score: float,
    ) -> float:
        """Compute a weighted effectiveness score.

        Args:
            precision_score: Precision metric (0.0-1.0).
            prevention_score: Prevention rate metric (0.0-1.0).
            adoption_score: Adoption metric (0.0-1.0).

        Returns:
            Weighted composite score (0.0-1.0).
        """
        return self.precision * precision_score + self.prevention * prevention_score + self.adoption * adoption_score


DOMAIN_WEIGHTS: dict[str, EffectivenessWeights] = {
    "engineering": EffectivenessWeights(
        precision=0.4,
        prevention=0.35,
        adoption=0.25,
    ),
    "legal": EffectivenessWeights(
        precision=0.5,
        prevention=0.3,
        adoption=0.2,
    ),
    "hr": EffectivenessWeights(
        precision=0.2,
        prevention=0.5,
        adoption=0.3,
    ),
    "finance": EffectivenessWeights(
        precision=0.4,
        prevention=0.4,
        adoption=0.2,
    ),
    "sales": EffectivenessWeights(
        precision=0.3,
        prevention=0.2,
        adoption=0.5,
    ),
    "it_security": EffectivenessWeights(
        precision=0.35,
        prevention=0.45,
        adoption=0.2,
    ),
    "communications": EffectivenessWeights(
        precision=0.3,
        prevention=0.3,
        adoption=0.4,
    ),
    "governance": EffectivenessWeights(
        precision=0.45,
        prevention=0.35,
        adoption=0.2,
    ),
}

DEFAULT_WEIGHTS = EffectivenessWeights(
    precision=0.4,
    prevention=0.35,
    adoption=0.25,
)


def get_weights(domain: str) -> EffectivenessWeights:
    """Get effectiveness weights for a domain.

    Returns domain-specific weights if configured, otherwise defaults
    to the engineering-style weights.

    Args:
        domain: Domain name (e.g. ``"legal"``, ``"hr"``).

    Returns:
        The :class:`EffectivenessWeights` for the given domain.
    """
    weights = DOMAIN_WEIGHTS.get(domain, DEFAULT_WEIGHTS)
    logger.debug("effectiveness_weights", domain=domain, weights=weights)
    return weights

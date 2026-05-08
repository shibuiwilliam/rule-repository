"""Governance policy analyzer — discovers rules from corporate governance policies and board charters."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class GovernancePolicyAnalyzer:
    """Analyzes corporate governance policies and board charters to discover candidate rules.

    Looks for common governance patterns that should be codified:
    - Quorum requirements for board meetings
    - Conflict of interest disclosure obligations
    - Filing deadline requirements
    - ESG reporting commitments
    - Director independence standards
    - Material event disclosure thresholds
    """

    name: str = "governance_policy_analyzer"

    async def analyze(self, source: Any) -> list[dict[str, Any]]:
        """Analyze a governance document and suggest candidate rules.

        Args:
            source: A dict with ``text`` or ``content`` key, or a plain string.

        Returns:
            A list of candidate rule dicts ready for review.
        """
        candidates: list[dict[str, Any]] = []

        if isinstance(source, dict):
            text = source.get("text", source.get("content", ""))
        elif isinstance(source, str):
            text = source
        else:
            return []

        if not text:
            return []

        text_lower = text.lower()

        # Quorum requirements
        if "quorum" in text_lower and "majority" not in text_lower:
            candidates.append(
                {
                    "statement": (
                        "Board meetings MUST have a quorum of at least a majority of "
                        "directors present before any vote can be taken"
                    ),
                    "modality": "MUST",
                    "severity": "CRITICAL",
                    "source": "governance_policy_analysis",
                    "applies_to": "board_minute",
                    "confidence": 0.8,
                }
            )

        # Conflict of interest
        if (
            "conflict" in text_lower
            and "interest" in text_lower
            and "disclose" not in text_lower
            and "declare" not in text_lower
        ):
            candidates.append(
                {
                    "statement": (
                        "Directors MUST disclose any conflict of interest before deliberation on related matters"
                    ),
                    "modality": "MUST",
                    "severity": "CRITICAL",
                    "source": "governance_policy_analysis",
                    "applies_to": "board_minute",
                    "confidence": 0.75,
                }
            )

        # Filing deadlines
        if (
            ("filing" in text_lower or "disclosure" in text_lower)
            and "deadline" not in text_lower
            and "timely" not in text_lower
        ):
            candidates.append(
                {
                    "statement": (
                        "All regulatory filings MUST be submitted within the "
                        "prescribed deadline set by the relevant regulator"
                    ),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "governance_policy_analysis",
                    "applies_to": "disclosure_document",
                    "confidence": 0.7,
                }
            )

        # ESG reporting
        has_esg = "esg" in text_lower or "sustainability" in text_lower
        has_framework = any(fw in text_lower for fw in ["gri", "sasb", "tcfd"])
        if has_esg and not has_framework:
            candidates.append(
                {
                    "statement": (
                        "ESG disclosures SHOULD reference at least one recognized "
                        "reporting framework (GRI, SASB, or TCFD)"
                    ),
                    "modality": "SHOULD",
                    "severity": "MEDIUM",
                    "source": "governance_policy_analysis",
                    "applies_to": "disclosure_document",
                    "confidence": 0.65,
                }
            )

        # Director independence
        if (
            "independent" in text_lower
            and "director" in text_lower
            and "committee" in text_lower
            and "majority" not in text_lower
        ):
            candidates.append(
                {
                    "statement": (
                        "Audit and compensation committees MUST be composed of a majority of independent directors"
                    ),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "governance_policy_analysis",
                    "applies_to": "board_minute",
                    "confidence": 0.7,
                }
            )

        # Material events
        if (
            "material" in text_lower
            and "event" in text_lower
            and "day" not in text_lower
            and "business" not in text_lower
        ):
            candidates.append(
                {
                    "statement": (
                        "Material events MUST be disclosed to the regulator within four (4) business days of occurrence"
                    ),
                    "modality": "MUST",
                    "severity": "CRITICAL",
                    "source": "governance_policy_analysis",
                    "applies_to": "disclosure_document",
                    "confidence": 0.8,
                }
            )

        logger.info(
            "governance_policy_analysis_complete",
            candidates_found=len(candidates),
        )
        return candidates

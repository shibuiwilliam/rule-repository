"""Marketing policy analyzer — discovers candidate rules from sales/marketing policy documents."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class MarketingPolicyAnalyzer:
    """Analyzes marketing and sales policy documents to discover compliance rules.

    Looks for patterns related to:
    - Advertising claim requirements and disclaimers
    - Discount authority and approval thresholds
    - Quote validity and terms requirements
    - Anti-competitive pricing policies
    """

    name: str = "marketing_policy_analyzer"

    async def analyze(self, source: Any) -> list[dict[str, Any]]:
        """Analyze a marketing/sales policy document and suggest candidate rules.

        Args:
            source: Document content as a string or dict with ``text``/``content`` key.

        Returns:
            List of candidate rule dicts with statement, modality, severity, etc.
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

        # Detect missing disclaimer requirements
        has_claims = any(kw in text_lower for kw in ["claim", "guarantee", "proven", "best", "#1", "number one"])
        has_disclaimer_policy = "disclaimer" in text_lower or "disclosure" in text_lower
        if has_claims and not has_disclaimer_policy:
            candidates.append(
                {
                    "statement": (
                        "All advertising claims MUST be accompanied by "
                        "appropriate disclaimers and substantiation references"
                    ),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "marketing_policy_analysis",
                    "applies_to": "ad_copy",
                    "confidence": 0.75,
                }
            )

        # Detect discount authority patterns
        has_discount = "discount" in text_lower or "price reduction" in text_lower
        has_approval = "approval" in text_lower or "authority" in text_lower
        if has_discount and not has_approval:
            candidates.append(
                {
                    "statement": (
                        "Discounts exceeding 15% MUST receive manager-level "
                        "approval before being offered to the customer"
                    ),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "marketing_policy_analysis",
                    "applies_to": "discount_request",
                    "confidence": 0.7,
                }
            )

        # Detect quote validity requirements
        has_quote = "quote" in text_lower or "quotation" in text_lower or "proposal" in text_lower
        has_validity = "validity" in text_lower or "expir" in text_lower or "valid until" in text_lower
        if has_quote and not has_validity:
            candidates.append(
                {
                    "statement": (
                        "All customer quotes MUST include an expiration date no more than 90 days from the issue date"
                    ),
                    "modality": "MUST",
                    "severity": "MEDIUM",
                    "source": "marketing_policy_analysis",
                    "applies_to": "quote",
                    "confidence": 0.8,
                }
            )

        # Detect anti-competitive pricing concerns
        has_competitor = "competitor" in text_lower or "competitive" in text_lower
        has_pricing = "pricing" in text_lower or "price match" in text_lower
        if has_competitor and has_pricing and "anti-competitive" not in text_lower:
            candidates.append(
                {
                    "statement": (
                        "Pricing MUST NOT be set below cost with the intent "
                        "to eliminate competition (predatory pricing)"
                    ),
                    "modality": "MUST_NOT",
                    "severity": "CRITICAL",
                    "source": "marketing_policy_analysis",
                    "applies_to": "quote",
                    "confidence": 0.65,
                }
            )

        # Detect health claim patterns (pharma/supplement advertising)
        has_health = any(kw in text_lower for kw in ["health", "cure", "treat", "prevent", "supplement", "efficacy"])
        has_regulatory = any(kw in text_lower for kw in ["fda", "ftc", "薬機法", "景表法"])
        if has_health and not has_regulatory:
            candidates.append(
                {
                    "statement": (
                        "Health-related advertising claims MUST comply with "
                        "applicable regulatory requirements (FTC, FDA, 薬機法) "
                        "and MUST NOT make unsubstantiated efficacy claims"
                    ),
                    "modality": "MUST",
                    "severity": "CRITICAL",
                    "source": "marketing_policy_analysis",
                    "applies_to": "ad_copy",
                    "confidence": 0.8,
                }
            )

        logger.info(
            "marketing_policy_analysis_complete",
            candidates_found=len(candidates),
        )
        return candidates

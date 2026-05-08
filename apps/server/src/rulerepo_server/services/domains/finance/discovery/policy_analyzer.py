"""Finance policy analyzer — discovers candidate rules from finance policy documents."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class FinancePolicyAnalyzer:
    """Analyzes finance policy documents to discover compliance-relevant patterns.

    Looks for:
    - Approval thresholds (e.g. expenses over $X require VP approval)
    - Segregation of duties requirements
    - Documentation requirements (receipts, competitive bids)
    - Tax rules and withholding obligations
    """

    name: str = "finance_policy_analyzer"

    async def analyze(self, source: Any) -> list[dict[str, Any]]:
        """Analyze a finance policy document and suggest candidate rules.

        Args:
            source: Either a string of text or a dict with ``text``/``content`` key.

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

        # Detect approval threshold patterns
        if "approval" in text_lower and ("threshold" in text_lower or "limit" in text_lower):
            candidates.append(
                {
                    "statement": (
                        "Expenses exceeding the defined threshold MUST receive manager approval before processing"
                    ),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "finance_policy_analysis",
                    "confidence": 0.75,
                }
            )

        # Detect segregation of duties requirements
        if "segregation" in text_lower or ("preparer" in text_lower and "approver" in text_lower):
            candidates.append(
                {
                    "statement": ("The preparer and approver of a financial transaction MUST be different individuals"),
                    "modality": "MUST",
                    "severity": "CRITICAL",
                    "source": "finance_policy_analysis",
                    "confidence": 0.9,
                }
            )

        # Detect receipt/documentation requirements
        has_receipt = "receipt" in text_lower
        has_documentation = "documentation" in text_lower or "supporting document" in text_lower
        if has_receipt or has_documentation:
            candidates.append(
                {
                    "statement": (
                        "All expense claims MUST be accompanied by original receipts or equivalent documentation"
                    ),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "finance_policy_analysis",
                    "confidence": 0.8,
                }
            )

        # Detect competitive bidding requirements
        if "competitive bid" in text_lower or "three quotes" in text_lower or "rfp" in text_lower:
            candidates.append(
                {
                    "statement": (
                        "Purchase orders above the competitive bidding threshold "
                        "MUST include at least three vendor quotes"
                    ),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "finance_policy_analysis",
                    "confidence": 0.8,
                }
            )

        # Detect tax compliance patterns
        has_tax = "tax" in text_lower
        has_registration = "registration" in text_lower or "tin" in text_lower or "vat" in text_lower
        if has_tax and has_registration:
            candidates.append(
                {
                    "statement": ("Invoices MUST include a valid tax registration number for the issuing entity"),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "finance_policy_analysis",
                    "confidence": 0.85,
                }
            )

        logger.info("finance_policy_analysis_complete", candidates_found=len(candidates))
        return candidates

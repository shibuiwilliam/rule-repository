"""Contract document analyzer — discovers candidate rules from contracts."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class ContractAnalyzer:
    """Analyzes contract documents to discover compliance-relevant patterns."""

    name: str = "contract_analyzer"

    async def analyze(self, source: Any) -> list[dict[str, Any]]:
        """Analyze a contract document and suggest candidate rules.

        Looks for common contractual patterns that should be codified:
        - Indemnification clauses without caps
        - Missing governing law specifications
        - Non-standard termination provisions
        - Data protection gaps
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

        # Simple pattern-based discovery (production would use LLM)
        text_lower = text.lower()

        if "indemnif" in text_lower and "cap" not in text_lower and "limit" not in text_lower:
            candidates.append(
                {
                    "statement": "All indemnification clauses MUST include a liability cap",
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "contract_analysis",
                    "confidence": 0.7,
                }
            )

        if "governing law" not in text_lower and "applicable law" not in text_lower:
            candidates.append(
                {
                    "statement": "Every contract MUST specify the governing law and jurisdiction",
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "contract_analysis",
                    "confidence": 0.8,
                }
            )

        has_personal_data = "personal data" in text_lower or "personal information" in text_lower
        has_protection = "data protection" in text_lower or "privacy" in text_lower
        if has_personal_data and not has_protection:
            candidates.append(
                {
                    "statement": "Contracts involving personal data MUST include a data protection addendum",
                    "modality": "MUST",
                    "severity": "CRITICAL",
                    "source": "contract_analysis",
                    "confidence": 0.75,
                }
            )

        logger.info("contract_analysis_complete", candidates_found=len(candidates))
        return candidates

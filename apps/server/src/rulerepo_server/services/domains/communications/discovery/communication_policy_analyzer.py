"""Communication policy analyzer — discovers rules from communications and social media policies."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class CommunicationPolicyAnalyzer:
    """Analyzes communications policy documents to discover candidate rules.

    Scans for patterns related to:
    - External communication restrictions
    - Confidentiality classification requirements
    - Disclaimer mandates
    - Social media policies
    - Data leak prevention triggers
    - Tone and professionalism standards
    """

    name: str = "communication_policy_analyzer"

    async def analyze(self, source: Any) -> list[dict[str, Any]]:
        """Analyze a communications policy document and suggest candidate rules.

        Args:
            source: The policy document content as a string or dict with
                    ``text`` / ``content`` key.

        Returns:
            A list of candidate rule dicts with statement, modality, severity,
            source, and confidence fields.
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

        # External communication restrictions
        has_external = "external" in text_lower or "outside the organization" in text_lower
        has_confidential = "confidential" in text_lower or "restricted" in text_lower
        if has_external and has_confidential:
            candidates.append(
                {
                    "statement": (
                        "Confidential or restricted information MUST NOT be shared "
                        "in external communications without explicit authorization"
                    ),
                    "modality": "MUST_NOT",
                    "severity": "CRITICAL",
                    "source": "communication_policy_analysis",
                    "applies_to": ["email_message", "chat_message"],
                    "confidence": 0.85,
                }
            )

        # Disclaimer requirements
        has_disclaimer = "disclaimer" in text_lower or "legal notice" in text_lower
        if has_disclaimer and has_external:
            candidates.append(
                {
                    "statement": ("All external emails MUST include the approved legal disclaimer"),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "communication_policy_analysis",
                    "applies_to": ["email_message"],
                    "confidence": 0.8,
                }
            )

        # Social media policy
        has_social = (
            "social media" in text_lower
            or "twitter" in text_lower
            or "linkedin" in text_lower
            or "facebook" in text_lower
        )
        if has_social:
            candidates.append(
                {
                    "statement": (
                        "Social media posts referencing the organization "
                        "MUST comply with the approved social media policy"
                    ),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "communication_policy_analysis",
                    "applies_to": ["chat_message"],
                    "confidence": 0.75,
                }
            )

        # Data leak prevention
        has_dlp = (
            "data leak" in text_lower
            or "data loss prevention" in text_lower
            or "unreleased" in text_lower
            or "pre-announcement" in text_lower
        )
        if has_dlp or ("merger" in text_lower and "acquisition" in text_lower):
            candidates.append(
                {
                    "statement": (
                        "Communications MUST NOT reference unreleased products, "
                        "M&A activity, or non-public financial information"
                    ),
                    "modality": "MUST_NOT",
                    "severity": "CRITICAL",
                    "source": "communication_policy_analysis",
                    "applies_to": ["email_message", "chat_message"],
                    "confidence": 0.9,
                }
            )

        # Professionalism / tone requirements
        has_tone = (
            "professional" in text_lower
            or "tone" in text_lower
            or "respectful" in text_lower
            or "harassment" in text_lower
        )
        if has_tone:
            candidates.append(
                {
                    "statement": (
                        "All communications MUST maintain a professional and "
                        "respectful tone appropriate to the audience"
                    ),
                    "modality": "MUST",
                    "severity": "MEDIUM",
                    "source": "communication_policy_analysis",
                    "applies_to": ["email_message", "chat_message"],
                    "confidence": 0.7,
                }
            )

        # PII in communications
        has_pii = "personally identifiable" in text_lower or "pii" in text_lower or "personal data" in text_lower
        has_encryption = "encrypt" in text_lower or "secure" in text_lower
        if has_pii:
            candidates.append(
                {
                    "statement": (
                        "PII MUST NOT be transmitted via email or chat without "
                        "encryption or an approved secure transfer mechanism"
                    ),
                    "modality": "MUST_NOT",
                    "severity": "CRITICAL",
                    "source": "communication_policy_analysis",
                    "applies_to": ["email_message", "chat_message"],
                    "confidence": 0.85 if has_encryption else 0.7,
                }
            )

        logger.info(
            "communication_policy_analysis_complete",
            candidates_found=len(candidates),
        )
        return candidates

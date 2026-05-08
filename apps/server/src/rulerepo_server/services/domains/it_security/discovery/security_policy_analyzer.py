"""Security policy analyzer — discovers candidate rules from security policy documents."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class SecurityPolicyAnalyzer:
    """Analyzes security policy documents to discover compliance-relevant patterns."""

    name: str = "security_policy_analyzer"

    async def analyze(self, source: Any) -> list[dict[str, Any]]:
        """Analyze a security policy document and suggest candidate rules.

        Looks for common security patterns that should be codified:
        - Encryption requirements (at rest and in transit)
        - Access control policies (least privilege, MFA)
        - Network security (segmentation, firewall rules)
        - MFA requirements for privileged access
        - Resource tagging and inventory policies
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

        # Encryption requirements
        has_encryption_mention = "encrypt" in text_lower
        has_at_rest = "at rest" in text_lower or "at-rest" in text_lower
        has_in_transit = "in transit" in text_lower or "in-transit" in text_lower or "tls" in text_lower
        if has_encryption_mention and (has_at_rest or has_in_transit):
            candidates.append(
                {
                    "statement": "All data stores MUST use encryption at rest (AES-256 or equivalent)",
                    "modality": "MUST",
                    "severity": "CRITICAL",
                    "source": "security_policy_analysis",
                    "confidence": 0.85,
                }
            )

        # Access control / least privilege
        has_least_privilege = "least privilege" in text_lower or "minimal access" in text_lower
        if has_least_privilege:
            candidates.append(
                {
                    "statement": "IAM policies MUST follow the principle of least privilege; "
                    "wildcard actions (*) are prohibited in production",
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "security_policy_analysis",
                    "confidence": 0.8,
                }
            )

        # Network security
        has_network = "network" in text_lower or "firewall" in text_lower or "security group" in text_lower
        has_public = "public" in text_lower or "0.0.0.0" in text_lower
        if has_network and has_public:
            candidates.append(
                {
                    "statement": "Security groups MUST NOT allow unrestricted ingress (0.0.0.0/0) "
                    "on non-public-facing services",
                    "modality": "MUST NOT",
                    "severity": "CRITICAL",
                    "source": "security_policy_analysis",
                    "confidence": 0.9,
                }
            )

        # MFA requirements
        has_mfa = "mfa" in text_lower or "multi-factor" in text_lower or "two-factor" in text_lower
        if has_mfa:
            candidates.append(
                {
                    "statement": "All privileged and administrative access MUST require "
                    "multi-factor authentication (MFA)",
                    "modality": "MUST",
                    "severity": "CRITICAL",
                    "source": "security_policy_analysis",
                    "confidence": 0.9,
                }
            )

        # Resource tagging
        has_tagging = "tag" in text_lower and ("resource" in text_lower or "asset" in text_lower)
        if has_tagging:
            candidates.append(
                {
                    "statement": "All cloud resources MUST be tagged with owner, environment, and cost-center labels",
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "security_policy_analysis",
                    "confidence": 0.75,
                }
            )

        logger.info("security_policy_analysis_complete", candidates_found=len(candidates))
        return candidates

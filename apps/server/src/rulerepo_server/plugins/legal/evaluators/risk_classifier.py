"""Risk classifier evaluator — classifies contract clauses by risk level.

Uses deterministic rules to classify contract clauses as high, medium,
or low risk based on known risk indicators, one-sided terms detection,
and deviation from common patterns.

See: CLAUDE.md SS14.3, PROJECT.md SS6.4
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Risk indicator definitions
# ---------------------------------------------------------------------------

_HIGH_RISK_INDICATORS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "unlimited_liability",
        re.compile(r"\b(unlimited\s+liability|無制限[のな]責任|no\s+cap\s+on\s+liability)\b", re.IGNORECASE),
        "Unlimited liability exposure detected",
    ),
    (
        "one_sided_indemnity",
        re.compile(
            r"\b(solely\s+indemnif|one[\s-]?sided\s+indemnit|一方的[なに]補償|"
            r"indemnify.*without\s+reciproc)\b",
            re.IGNORECASE,
        ),
        "One-sided indemnification clause without reciprocal obligation",
    ),
    (
        "auto_renewal_no_notice",
        re.compile(
            r"\b(automatically\s+renew.*without\s+notice|自動更新.*通知なし|"
            r"auto[\s-]?renew(?!.*(?:notice|通知)))\b",
            re.IGNORECASE,
        ),
        "Automatic renewal without required notice period",
    ),
    (
        "excessive_non_compete",
        re.compile(
            r"\b(non[\s-]?compet\w*.*(?:[3-9]|[1-9]\d)\s*years?|"
            r"競業禁止.*(?:[3-9]|[1-9]\d)\s*年)\b",
            re.IGNORECASE,
        ),
        "Non-compete clause exceeding 2 years",
    ),
    (
        "ip_assignment_no_compensation",
        re.compile(
            r"\b(assign\w*\s+(?:all\s+)?(?:IP|intellectual\s+property).*without\s+(?:additional\s+)?compensat|"
            r"知的財産.*(?:無償|対価なし).*譲渡)\b",
            re.IGNORECASE,
        ),
        "IP assignment without compensation",
    ),
    (
        "unfavorable_jurisdiction",
        re.compile(
            r"\b(governing\s+law.*(?:Cayman|BVI|offshore)|"
            r"準拠法.*(?:ケイマン|英領))\b",
            re.IGNORECASE,
        ),
        "Governing law specifies unfavorable or offshore jurisdiction",
    ),
]

_MEDIUM_RISK_INDICATORS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "unclear_termination",
        re.compile(
            r"\b(terminat\w*.*(?:unclear|ambiguous|unspecified)|"
            r"解除.*(?:不明確|曖昧))\b",
            re.IGNORECASE,
        ),
        "Unclear or ambiguous termination terms",
    ),
    (
        "no_penalty_cap",
        re.compile(
            r"\b(penalt\w*.*(?:no\s+(?:cap|limit|maximum))|"
            r"違約金.*(?:上限なし|制限なし))\b",
            re.IGNORECASE,
        ),
        "Missing cap on penalty amounts",
    ),
    (
        "broad_confidentiality",
        re.compile(
            r"\b(all\s+information.*(?:confidential|proprietary)|"
            r"全ての情報.*秘密)\b",
            re.IGNORECASE,
        ),
        "Overly broad definition of confidential information",
    ),
    (
        "short_cure_period",
        re.compile(
            r"\b(cure\s+period.*(?:[1-9]|1[0-3])\s*days?|"
            r"是正期間.*(?:[1-9]|1[0-3])\s*日)\b",
            re.IGNORECASE,
        ),
        "Cure period shorter than 14 days",
    ),
    (
        "unilateral_amendment",
        re.compile(
            r"\b(unilateral\w*\s+(?:amend|modif|change)|"
            r"一方的[にな]変更)\b",
            re.IGNORECASE,
        ),
        "Unilateral right to amend terms",
    ),
    (
        "excessive_indemnity_cap",
        re.compile(
            r"\b(indemnit\w*.*(?:[4-9]|[1-9]\d)\s*(?:times?|x)\s*(?:contract|agreement)\s*value|"
            r"補償.*契約金額の(?:[4-9]|[1-9]\d)倍)\b",
            re.IGNORECASE,
        ),
        "Indemnity cap exceeds 3x contract value",
    ),
]

_LOW_RISK_INDICATORS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "standard_force_majeure",
        re.compile(
            r"\b(force\s+majeure.*(?:mutual|both\s+parties|either\s+party)|"
            r"不可抗力.*(?:双方|両当事者))\b",
            re.IGNORECASE,
        ),
        "Standard force majeure clause with mutual application",
    ),
    (
        "reasonable_notice",
        re.compile(
            r"\b((?:30|60|90)\s*days?\s*(?:prior\s+)?(?:written\s+)?notice|"
            r"(?:30|60|90)\s*日前.*(?:書面)?.*通知)\b",
            re.IGNORECASE,
        ),
        "Reasonable notice period (30-90 days)",
    ),
    (
        "mutual_obligations",
        re.compile(
            r"\b(mutual\w*\s+(?:obligation|responsibilit|indemnif)|"
            r"相互[のな](?:義務|責任|補償))\b",
            re.IGNORECASE,
        ),
        "Mutual/reciprocal obligations",
    ),
    (
        "standard_warranty",
        re.compile(
            r"\b(warrant\w*.*(?:12|twelve)\s*months?|"
            r"保証期間.*(?:12|1年))\b",
            re.IGNORECASE,
        ),
        "Standard warranty period",
    ),
]

# ---------------------------------------------------------------------------
# One-sided term detection
# ---------------------------------------------------------------------------

_PARTY_A_OBLIGATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(party\s+a|甲|licensor|vendor|provider)\s+(?:shall|must|will)\b", re.IGNORECASE),
]

_PARTY_B_OBLIGATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(party\s+b|乙|licensee|customer|recipient)\s+(?:shall|must|will)\b", re.IGNORECASE),
]


def _count_obligations(text: str, patterns: list[re.Pattern[str]]) -> int:
    """Count obligation instances matching given patterns.

    Args:
        text: Clause text.
        patterns: Compiled regex patterns.

    Returns:
        Count of matches.
    """
    count = 0
    for pattern in patterns:
        count += len(pattern.findall(text))
    return count


def _detect_one_sided_terms(text: str) -> dict[str, Any] | None:
    """Detect one-sided obligations between parties.

    Args:
        text: Full clause or document text.

    Returns:
        Dict with imbalance info if detected, else None.
    """
    party_a_count = _count_obligations(text, _PARTY_A_OBLIGATION_PATTERNS)
    party_b_count = _count_obligations(text, _PARTY_B_OBLIGATION_PATTERNS)

    total = party_a_count + party_b_count
    if total < 2:
        return None

    # Significant imbalance: one party has > 3x obligations of the other
    if party_b_count > 0 and party_a_count / max(party_b_count, 1) > 3:
        return {
            "imbalance": "party_a_heavy",
            "party_a_obligations": party_a_count,
            "party_b_obligations": party_b_count,
            "description": "Party A bears disproportionate obligations",
        }
    if party_a_count > 0 and party_b_count / max(party_a_count, 1) > 3:
        return {
            "imbalance": "party_b_heavy",
            "party_a_obligations": party_a_count,
            "party_b_obligations": party_b_count,
            "description": "Party B bears disproportionate obligations",
        }
    return None


class RiskClassifier:
    """Evaluator that classifies contract clauses by risk level.

    Uses deterministic pattern matching to identify high, medium, and
    low risk indicators in contract text. Detects one-sided terms and
    flags deviations from common patterns.

    All remediations are text_rewrite kind and are never auto-applicable,
    as contract modifications require legal review and counterparty consent.
    """

    @property
    def name(self) -> str:
        return "risk_classifier"

    @property
    def domain(self) -> str:
        return "legal"

    @property
    def supported_subject_kinds(self) -> list[str]:
        return ["clause_set", "document"]

    async def evaluate(
        self,
        subject_payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Classify risk level of contract clauses against rules.

        Args:
            subject_payload: Document data containing clause_text or clauses list.
            rules: List of legal rule dicts.
            context: Additional context (jurisdiction, contract_type, ...).

        Returns:
            List of verdict dicts with risk_level, risk_factors, and remediations.
        """
        text = self._extract_text(subject_payload)
        if not text:
            logger.warning("risk_classifier_no_text", payload_keys=list(subject_payload.keys()))
            return []

        logger.info(
            "risk_classification_started",
            text_length=len(text),
            rule_count=len(rules),
        )

        # Classify overall document risk
        risk_factors = self._identify_risk_factors(text)
        overall_risk = self._determine_overall_risk(risk_factors)
        one_sided = _detect_one_sided_terms(text)

        if one_sided:
            risk_factors.append(
                {
                    "indicator": "one_sided_terms",
                    "level": "HIGH",
                    "description": one_sided["description"],
                    "details": one_sided,
                }
            )
            if overall_risk != "HIGH":
                overall_risk = "HIGH"

        # Generate per-rule verdicts
        verdicts: list[dict[str, Any]] = []
        for rule in rules:
            verdict = self._evaluate_rule_against_risk(
                rule=rule,
                text=text,
                risk_factors=risk_factors,
                overall_risk=overall_risk,
                context=context,
            )
            verdicts.append(verdict)

        logger.info(
            "risk_classification_complete",
            overall_risk=overall_risk,
            risk_factor_count=len(risk_factors),
            verdict_count=len(verdicts),
        )

        return verdicts

    def _extract_text(self, payload: dict[str, Any]) -> str:
        """Extract evaluable text from the subject payload.

        Args:
            payload: Subject payload dict.

        Returns:
            Concatenated text for analysis.
        """
        parts: list[str] = []

        if "clause_text" in payload:
            parts.append(payload["clause_text"])
        if "content" in payload:
            parts.append(payload["content"])
        if "clauses" in payload and isinstance(payload["clauses"], list):
            for clause in payload["clauses"]:
                if isinstance(clause, dict) and "text" in clause:
                    parts.append(clause["text"])
                elif isinstance(clause, str):
                    parts.append(clause)

        return "\n\n".join(parts)

    def _identify_risk_factors(self, text: str) -> list[dict[str, Any]]:
        """Identify all risk factors present in the text.

        Args:
            text: Document text.

        Returns:
            List of risk factor dicts.
        """
        factors: list[dict[str, Any]] = []

        for indicator_id, pattern, description in _HIGH_RISK_INDICATORS:
            if pattern.search(text):
                factors.append(
                    {
                        "indicator": indicator_id,
                        "level": "HIGH",
                        "description": description,
                    }
                )

        for indicator_id, pattern, description in _MEDIUM_RISK_INDICATORS:
            if pattern.search(text):
                factors.append(
                    {
                        "indicator": indicator_id,
                        "level": "MEDIUM",
                        "description": description,
                    }
                )

        for indicator_id, pattern, description in _LOW_RISK_INDICATORS:
            if pattern.search(text):
                factors.append(
                    {
                        "indicator": indicator_id,
                        "level": "LOW",
                        "description": description,
                    }
                )

        return factors

    @staticmethod
    def _determine_overall_risk(risk_factors: list[dict[str, Any]]) -> str:
        """Determine overall risk level from individual factors.

        Args:
            risk_factors: List of identified risk factors.

        Returns:
            Overall risk level: 'HIGH', 'MEDIUM', or 'LOW'.
        """
        levels = [f["level"] for f in risk_factors]
        if "HIGH" in levels:
            return "HIGH"
        if "MEDIUM" in levels:
            return "MEDIUM"
        if "LOW" in levels:
            return "LOW"
        return "LOW"

    def _evaluate_rule_against_risk(
        self,
        rule: dict[str, Any],
        text: str,
        risk_factors: list[dict[str, Any]],
        overall_risk: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a single rule considering identified risk factors.

        Args:
            rule: Rule dict.
            text: Document text.
            risk_factors: Identified risk factors.
            overall_risk: Overall document risk level.
            context: Evaluation context.

        Returns:
            Verdict dict.
        """
        rule_id = rule.get("id", "unknown")
        rule_statement = rule.get("statement", "").lower()
        modality = rule.get("modality", "MUST")

        # Check if any high-risk factor relates to this rule
        relevant_factors = self._find_relevant_factors(rule_statement, risk_factors)

        if relevant_factors:
            high_factors = [f for f in relevant_factors if f["level"] == "HIGH"]
            if high_factors:
                verdict = "DENY"
                confidence = 0.9
            else:
                verdict = "WARN" if modality == "SHOULD" else "DENY"
                confidence = 0.75
        else:
            verdict = "ALLOW"
            confidence = 0.8

        result: dict[str, Any] = {
            "rule_id": rule_id,
            "verdict": verdict,
            "confidence": confidence,
            "risk_level": overall_risk,
            "risk_factors": relevant_factors,
            "reasoning": self._build_reasoning(verdict, relevant_factors, rule),
        }

        # Add remediation for non-ALLOW verdicts
        if verdict != "ALLOW" and relevant_factors:
            result["remediation"] = {
                "kind": "text_rewrite",
                "auto_applicable": False,
                "description": self._suggest_remediation(relevant_factors),
                "requires_counterparty_consent": True,
                "payload": {
                    "risk_factors": [f["indicator"] for f in relevant_factors],
                    "suggested_changes": [f["description"] for f in relevant_factors],
                },
            }

        return result

    @staticmethod
    def _find_relevant_factors(
        rule_statement: str,
        risk_factors: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Find risk factors relevant to a specific rule.

        Args:
            rule_statement: Lowercased rule statement text.
            risk_factors: All identified risk factors.

        Returns:
            Subset of risk factors relevant to the rule.
        """
        relevance_keywords: dict[str, list[str]] = {
            "unlimited_liability": ["liability", "cap", "limit", "責任"],
            "one_sided_indemnity": ["indemnif", "compensation", "補償"],
            "auto_renewal_no_notice": ["renewal", "notice", "更新", "通知"],
            "excessive_non_compete": ["non-compete", "compet", "競業"],
            "ip_assignment_no_compensation": ["ip", "intellectual", "知的財産", "譲渡"],
            "unfavorable_jurisdiction": ["jurisdiction", "governing", "準拠法"],
            "unclear_termination": ["terminat", "cancel", "解除"],
            "no_penalty_cap": ["penalty", "cap", "違約金"],
            "broad_confidentiality": ["confidential", "秘密"],
            "short_cure_period": ["cure", "是正", "remedy"],
            "one_sided_terms": ["mutual", "reciprocal", "相互", "balanced"],
            "unilateral_amendment": ["amend", "modif", "変更"],
            "excessive_indemnity_cap": ["indemnit", "cap", "補償"],
        }

        relevant: list[dict[str, Any]] = []
        for factor in risk_factors:
            keywords = relevance_keywords.get(factor["indicator"], [])
            if any(kw in rule_statement for kw in keywords):
                relevant.append(factor)

        # If no keyword match but rule is general, include all high factors
        if not relevant:
            relevant = [f for f in risk_factors if f["level"] == "HIGH"]

        return relevant

    @staticmethod
    def _build_reasoning(
        verdict: str,
        factors: list[dict[str, Any]],
        rule: dict[str, Any],
    ) -> str:
        """Build human-readable reasoning for the verdict.

        Args:
            verdict: The verdict string.
            factors: Relevant risk factors.
            rule: The rule being evaluated.

        Returns:
            Reasoning string.
        """
        if verdict == "ALLOW":
            return f"No risk factors detected that conflict with rule '{rule.get('id', 'unknown')}'."

        factor_descriptions = "; ".join(f["description"] for f in factors)
        return (
            f"Risk classification: {verdict}. "
            f"Detected issues: {factor_descriptions}. "
            f"Rule '{rule.get('id', 'unknown')}' ({rule.get('modality', 'MUST')}) "
            f"requires review before acceptance."
        )

    @staticmethod
    def _suggest_remediation(factors: list[dict[str, Any]]) -> str:
        """Generate remediation suggestion from risk factors.

        Args:
            factors: Relevant risk factors.

        Returns:
            Remediation description.
        """
        suggestions: list[str] = []
        for factor in factors:
            indicator = factor["indicator"]
            if indicator == "unlimited_liability":
                suggestions.append("Add a liability cap (e.g., total fees paid in last 12 months)")
            elif indicator == "one_sided_indemnity":
                suggestions.append("Make indemnification mutual or add reciprocal protections")
            elif indicator == "auto_renewal_no_notice":
                suggestions.append("Add minimum 30-day written notice requirement before renewal")
            elif indicator == "excessive_non_compete":
                suggestions.append("Reduce non-compete duration to 1-2 years maximum")
            elif indicator == "ip_assignment_no_compensation":
                suggestions.append("Add fair compensation for IP assignment or limit scope")
            elif indicator == "unfavorable_jurisdiction":
                suggestions.append("Negotiate governing law to a mutually acceptable jurisdiction")
            elif indicator == "one_sided_terms":
                suggestions.append("Rebalance obligations to be more mutual/reciprocal")
            else:
                suggestions.append(f"Address: {factor['description']}")

        return "; ".join(suggestions)

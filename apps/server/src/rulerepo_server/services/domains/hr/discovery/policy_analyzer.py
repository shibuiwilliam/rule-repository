"""HR policy document analyzer — discovers candidate rules from HR policies."""

from __future__ import annotations

import re
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Patterns indicating mandatory or prohibitive policy language
_OBLIGATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(must|shall|required to|is required)\b", re.IGNORECASE),
    re.compile(r"\b(prohibited|forbidden|not permitted|must not|shall not)\b", re.IGNORECASE),
    re.compile(r"\b(mandatory|obligatory|compulsory)\b", re.IGNORECASE),
]


class PolicyAnalyzer:
    """Analyzes HR policy documents to discover compliance-relevant patterns.

    Uses pattern-based heuristics to identify sentences that express obligations
    or prohibitions suitable for codification as rules. In production, the LLM
    refines these candidates via the extraction pipeline.
    """

    name: str = "policy_analyzer"

    async def analyze(self, source: Any) -> list[dict[str, Any]]:
        """Analyze an HR policy document and suggest candidate rules.

        Looks for common HR policy patterns:
        - Attendance and overtime requirements
        - Leave entitlement and approval procedures
        - Performance evaluation standards
        - Anti-discrimination and harassment provisions
        - Employee data privacy requirements
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

        # Overtime policy detection
        if "overtime" in text_lower:
            if any(kw in text_lower for kw in ("approval", "authorize", "prior")):
                candidates.append(
                    {
                        "statement": (
                            "All overtime work MUST receive prior written approval from the employee's direct manager"
                        ),
                        "modality": "MUST",
                        "severity": "HIGH",
                        "source": "policy_analysis",
                        "applies_to": "attendance_record",
                        "confidence": 0.75,
                    }
                )
            if any(kw in text_lower for kw in ("36 agreement", "monthly limit", "hour limit", "45 hours")):
                candidates.append(
                    {
                        "statement": "Monthly overtime hours MUST NOT exceed the limit specified in the 36 Agreement",
                        "modality": "MUST_NOT",
                        "severity": "CRITICAL",
                        "source": "policy_analysis",
                        "applies_to": "attendance_record",
                        "confidence": 0.85,
                    }
                )

        # Leave policy detection
        if "leave" in text_lower:
            if "balance" in text_lower or "entitlement" in text_lower:
                candidates.append(
                    {
                        "statement": "Leave requests MUST NOT exceed the employee's remaining leave balance",
                        "modality": "MUST_NOT",
                        "severity": "HIGH",
                        "source": "policy_analysis",
                        "applies_to": "leave_request",
                        "confidence": 0.8,
                    }
                )
            if "manager" in text_lower and "approv" in text_lower:
                candidates.append(
                    {
                        "statement": (
                            "All leave requests MUST be approved by the "
                            "employee's direct manager before the leave "
                            "period begins"
                        ),
                        "modality": "MUST",
                        "severity": "HIGH",
                        "source": "policy_analysis",
                        "applies_to": "leave_request",
                        "confidence": 0.8,
                    }
                )

        # Sick leave certificate
        if "sick" in text_lower and ("certificate" in text_lower or "medical" in text_lower):
            candidates.append(
                {
                    "statement": (
                        "Sick leave exceeding the policy threshold MUST be accompanied by a medical certificate"
                    ),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "source": "policy_analysis",
                    "applies_to": "leave_request",
                    "confidence": 0.8,
                }
            )

        # Anti-discrimination and bias
        has_discrimination = "discriminat" in text_lower or "bias" in text_lower
        has_evaluation = "evaluation" in text_lower or "performance review" in text_lower
        if has_discrimination and has_evaluation:
            candidates.append(
                {
                    "statement": (
                        "Performance evaluation comments MUST NOT contain "
                        "language that discriminates based on gender, age, "
                        "race, disability, or other protected characteristics"
                    ),
                    "modality": "MUST_NOT",
                    "severity": "CRITICAL",
                    "source": "policy_analysis",
                    "applies_to": "evaluation_comment",
                    "confidence": 0.85,
                }
            )

        # Evidence-based evaluations
        if has_evaluation and ("evidence" in text_lower or "specific" in text_lower or "objective" in text_lower):
            candidates.append(
                {
                    "statement": (
                        "Performance evaluations MUST include specific, "
                        "evidence-based observations rather than vague "
                        "characterizations"
                    ),
                    "modality": "MUST",
                    "severity": "MEDIUM",
                    "source": "policy_analysis",
                    "applies_to": "evaluation_comment",
                    "confidence": 0.7,
                }
            )

        # Generic obligation extraction via patterns
        sentences = re.split(r"[.;]\s+", text)
        for sentence in sentences:
            for pattern in _OBLIGATION_PATTERNS:
                if pattern.search(sentence) and len(sentence.split()) >= 5:
                    # Avoid duplicating already-detected patterns
                    stmt_lower = sentence.strip().lower()
                    already_covered = any(
                        c["statement"].lower()[:30] in stmt_lower or stmt_lower[:30] in c["statement"].lower()
                        for c in candidates
                    )
                    if not already_covered:
                        candidates.append(
                            {
                                "statement": sentence.strip(),
                                "modality": "MUST" if "not" not in sentence.lower() else "MUST_NOT",
                                "severity": "MEDIUM",
                                "source": "policy_analysis",
                                "confidence": 0.5,
                            }
                        )
                    break  # one match per sentence is enough

        logger.info("hr_policy_analysis_complete", candidates_found=len(candidates))
        return candidates

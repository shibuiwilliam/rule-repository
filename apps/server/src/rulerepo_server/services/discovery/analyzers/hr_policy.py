"""HR policy analyzer — extracts rules from HR handbooks and labor regulations.

Processes employment regulations, attendance policies, leave policies, and
other HR documents. Detects quantitative thresholds (hours, days, amounts),
conditional requirements (if role=X then Y), and Japanese labor law structure
(条/項/号).

Outputs candidate rules with applicable_subject_types=["event", "transaction"]
and department="hr".

See CLAUDE.md §14.11.
"""

from __future__ import annotations

import re

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.discovery.analyzers.base import (
    DiscoveryContext,
    RawPattern,
    SourceAnalyzer,
)

logger = get_logger(__name__)

# File selection: HR-related filenames or paths
_HR_FILE_KEYWORDS = (
    "hr",
    "human_resource",
    "human-resource",
    "attendance",
    "leave",
    "overtime",
    "labor",
    "employment",
    "handbook",
    "employee",
    "payroll",
    "就業規則",
    "勤怠",
    "労務",
    "人事",
    "給与",
    "休暇",
    "有給",
    "残業",
    "36協定",
)

# Sentence splitting
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。])\s+")

# Japanese article structure: 第N条, 第N項, 第N号
_JA_ARTICLE = re.compile(r"第(\d+)条")
_JA_PARAGRAPH = re.compile(r"第(\d+)項")
_JA_ITEM = re.compile(r"第(\d+)号")

# Quantitative threshold patterns (numbers + units)
_THRESHOLD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Hours
    (re.compile(r"(\d+)\s*(?:時間|hours?)\b", re.I), "hours"),
    # Days
    (re.compile(r"(\d+)\s*(?:日間?|days?|営業日)\b", re.I), "days"),
    # Monetary amounts (JPY)
    (
        re.compile(r"(?:¥|￥|JPY\s*)?([\d,]+)\s*(?:円|yen)\b", re.I),
        "jpy",
    ),
    # Monetary amounts (generic with currency prefix)
    (
        re.compile(r"(?:\$|USD\s*|EUR\s*)([\d,]+(?:\.\d+)?)\b", re.I),
        "currency",
    ),
    # Percentages
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|パーセント|percent)\b", re.I), "percent"),
    # Count thresholds
    (re.compile(r"(\d+)\s*(?:回|times?|occurrences?)\b", re.I), "count"),
]

# Conditional requirement patterns
_CONDITIONAL_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"\b(?:の場合|に該当する場合|のときは)", re.I), 0.85),
    (re.compile(r"\b(?:if|when|in\s+the\s+case\s+(?:of|that)|provided\s+that)\b", re.I), 0.80),
    (re.compile(r"\b(?:ただし|但し|ただし書き|except\s+(?:when|that|where))\b", re.I), 0.80),
    (re.compile(r"\b(?:に限り|に限る|only\s+(?:if|when))\b", re.I), 0.80),
]

# Normative patterns — obligations and prohibitions in HR context
_NORMATIVE_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    # Japanese obligations
    (re.compile(r"(?:しなければならない|するものとする|義務とする)", re.I), "MUST", 0.90),
    (re.compile(r"(?:してはならない|禁止する|認めない)", re.I), "MUST_NOT", 0.90),
    (re.compile(r"(?:することができる|認める|許可する)", re.I), "MAY", 0.70),
    (re.compile(r"(?:するよう努める|努めなければならない|推奨する)", re.I), "SHOULD", 0.75),
    (re.compile(r"(?:承認を得なければ|許可を得た上で|届出を行う)", re.I), "MUST", 0.85),
    # English obligations
    (re.compile(r"\b(?:must\s+not|shall\s+not|is\s+prohibited)\b", re.I), "MUST_NOT", 0.90),
    (re.compile(r"\b(?:must|shall|is\s+required)\b", re.I), "MUST", 0.88),
    (re.compile(r"\b(?:should|is\s+recommended|is\s+encouraged)\b", re.I), "SHOULD", 0.78),
    (re.compile(r"\b(?:may|is\s+allowed|is\s+permitted)\b", re.I), "MAY", 0.68),
]

_MIN_SENTENCE_LEN = 15
_MAX_SENTENCE_LEN = 600


class HrPolicyAnalyzer(SourceAnalyzer):
    """Extracts rules from HR handbooks and employment regulations.

    Detects:
    - Quantitative thresholds (work hours, leave days, amounts)
    - Conditional requirements (role/situation-based rules)
    - Japanese labor law structure (条/項/号)
    - Standard obligations, prohibitions, and permissions

    Output patterns use department="hr" and
    applicable_subject_types=["event", "transaction"].
    """

    async def analyze(self, context: DiscoveryContext) -> list[RawPattern]:
        """Analyze HR documents for rule patterns.

        Args:
            context: Discovery context with file paths and contents.

        Returns:
            List of raw patterns extracted from HR documents.
        """
        patterns: list[RawPattern] = []

        for path, content in context.file_contents.items():
            if not self._is_hr_document(path, content):
                continue
            if len(content.strip()) < 30:
                continue

            logger.info("hr_policy_analyzing", path=path, size=len(content))
            file_patterns = self._extract_from_document(path, content)
            patterns.extend(file_patterns)

        logger.info("hr_policy_analysis_complete", pattern_count=len(patterns))
        return patterns

    def _is_hr_document(self, path: str, content: str) -> bool:
        """Check if a file is likely an HR document.

        Args:
            path: File path.
            content: File content.

        Returns:
            True if the file appears to be HR-related.
        """
        lower_path = path.lower()
        if any(kw in lower_path for kw in _HR_FILE_KEYWORDS):
            return True

        # Check content heuristic (first 1000 chars)
        lower_content = content[:1000].lower()
        hr_indicators = (
            "employee",
            "employment",
            "attendance",
            "overtime",
            "leave",
            "vacation",
            "payroll",
            "就業",
            "勤務",
            "従業員",
            "社員",
            "出勤",
            "労働",
        )
        return sum(1 for ind in hr_indicators if ind in lower_content) >= 2

    def _extract_from_document(self, path: str, content: str) -> list[RawPattern]:
        """Extract rule patterns from an HR document.

        Args:
            path: File path for provenance.
            content: Full document text.

        Returns:
            List of patterns found in the document.
        """
        patterns: list[RawPattern] = []
        article_context = ""

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Track Japanese article context
            article_match = _JA_ARTICLE.search(line)
            if article_match:
                article_context = f"第{article_match.group(1)}条"

            # Split into sentences
            sentences = _SENTENCE_SPLIT.split(line)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < _MIN_SENTENCE_LEN or len(sentence) > _MAX_SENTENCE_LEN:
                    continue

                # Detect normative language
                modality, confidence = self._detect_normative(sentence)
                if modality is None:
                    continue

                # Boost confidence if quantitative threshold found
                threshold_info = self._detect_threshold(sentence)
                if threshold_info:
                    confidence = min(confidence + 0.05, 0.95)

                # Boost confidence for conditional requirements
                is_conditional = self._detect_conditional(sentence)
                if is_conditional:
                    confidence = min(confidence + 0.03, 0.95)

                # Build scope
                scope = self._build_scope(path, article_context)

                # Build tags
                tags = ["hr_policy"]
                if threshold_info:
                    tags.append(f"threshold:{threshold_info}")
                if is_conditional:
                    tags.append("conditional")
                if article_context:
                    tags.append(article_context)
                tags.extend(self._infer_hr_tags(sentence))

                patterns.append(
                    RawPattern(
                        statement=sentence,
                        modality=modality,
                        severity=self._infer_severity(modality, sentence),
                        scope=scope,
                        tags=tags,
                        source_type="hr_policy",
                        source_evidence=sentence,
                        confidence=confidence,
                    )
                )

        return patterns

    def _detect_normative(self, sentence: str) -> tuple[str | None, float]:
        """Detect normative language in a sentence.

        Args:
            sentence: Sentence to analyze.

        Returns:
            Tuple of (modality, confidence) or (None, 0.0).
        """
        for pattern, modality, confidence in _NORMATIVE_PATTERNS:
            if pattern.search(sentence):
                return modality, confidence
        return None, 0.0

    def _detect_threshold(self, sentence: str) -> str | None:
        """Detect quantitative thresholds in a sentence.

        Args:
            sentence: Sentence to check.

        Returns:
            Threshold type string or None.
        """
        for pattern, threshold_type in _THRESHOLD_PATTERNS:
            if pattern.search(sentence):
                return threshold_type
        return None

    def _detect_conditional(self, sentence: str) -> bool:
        """Detect conditional requirement language.

        Args:
            sentence: Sentence to check.

        Returns:
            True if conditional language is detected.
        """
        return any(pat.search(sentence) for pat, _ in _CONDITIONAL_PATTERNS)

    def _build_scope(self, path: str, article_context: str) -> list[str]:
        """Build scope tags from file path and article context.

        Args:
            path: Source file path.
            article_context: Current Japanese article reference.

        Returns:
            List of scope strings.
        """
        scopes = ["hr"]
        lower_path = path.lower()

        scope_keywords = {
            "attendance": "hr/attendance",
            "勤怠": "hr/attendance",
            "overtime": "hr/overtime",
            "残業": "hr/overtime",
            "leave": "hr/leave",
            "休暇": "hr/leave",
            "有給": "hr/leave",
            "payroll": "hr/payroll",
            "給与": "hr/payroll",
            "hiring": "hr/hiring",
            "採用": "hr/hiring",
        }

        for keyword, scope in scope_keywords.items():
            if keyword in lower_path:
                scopes.append(scope)
                break

        return scopes

    def _infer_severity(self, modality: str, sentence: str) -> str:
        """Infer severity from modality and sentence content.

        Args:
            modality: Detected modality.
            sentence: The sentence text.

        Returns:
            Severity string.
        """
        critical_keywords = re.compile(
            r"\b(?:労働基準法|36協定|安全衛生|解雇|懲戒|"
            r"labor\s+standards|termination|disciplinary|"
            r"safety|harassment|discrimination|legal)\b",
            re.IGNORECASE,
        )
        if critical_keywords.search(sentence):
            if modality in ("MUST", "MUST_NOT"):
                return "CRITICAL"
            return "HIGH"

        if modality in ("MUST", "MUST_NOT"):
            return "HIGH"
        if modality == "SHOULD":
            return "MEDIUM"
        return "LOW"

    def _infer_hr_tags(self, sentence: str) -> list[str]:
        """Infer HR-specific tags from sentence content.

        Args:
            sentence: The sentence text.

        Returns:
            List of inferred tag strings.
        """
        tags: list[str] = []
        lower = sentence.lower()

        tag_keywords = {
            "overtime": ["overtime", "残業", "時間外"],
            "attendance": ["attendance", "出勤", "勤怠", "欠勤"],
            "leave": ["leave", "休暇", "有給", "育休", "産休", "休職"],
            "payroll": ["salary", "wage", "payroll", "給与", "賃金", "手当"],
            "safety": ["safety", "安全", "衛生", "健康"],
            "conduct": ["conduct", "harassment", "ハラスメント", "服務規律"],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in lower for kw in keywords):
                tags.append(tag)

        return tags

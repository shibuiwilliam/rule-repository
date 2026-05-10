"""Expense guideline analyzer — extracts rules from expense policies.

Processes expense policy documents and approval matrices. Detects:
- Threshold tables (role x amount -> required approval level)
- Category restrictions (prohibited expenses, conditional expenses)
- Documentation requirements (receipt rules, pre-approval requirements)
- Per-diem rates and limits

Outputs candidate rules with applicable_subject_types=["transaction"]
and department="finance".

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

# File selection: expense/finance-related filenames
_EXPENSE_FILE_KEYWORDS = (
    "expense",
    "travel",
    "reimburs",
    "procurement",
    "purchase",
    "approval",
    "budget",
    "経費",
    "旅費",
    "出張",
    "精算",
    "購買",
    "稟議",
    "決裁",
)

# Sentence splitting
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。])\s+")

# Amount patterns — detect monetary thresholds
_AMOUNT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # JPY amounts
    (
        re.compile(
            r"(?:¥|￥|JPY\s*)?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:円|yen)\b",
            re.I,
        ),
        "jpy",
    ),
    # USD/EUR amounts
    (
        re.compile(r"(?:\$|USD\s*|EUR\s*)(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\b", re.I),
        "usd",
    ),
    # Generic numeric with currency context
    (
        re.compile(
            r"(\d{1,3}(?:,\d{3})+)\s*(?:以上|以下|を超え|未満|まで|above|below|exceed|up\s+to)\b",
            re.I,
        ),
        "amount",
    ),
]

# Approval level patterns
_APPROVAL_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    # Japanese approval hierarchy
    (
        re.compile(r"(?:部長|department\s+(?:head|manager))\s*(?:の承認|承認|approval)", re.I),
        "department_head",
        0.85,
    ),
    (
        re.compile(r"(?:課長|section\s+(?:head|manager))\s*(?:の承認|承認|approval)", re.I),
        "section_head",
        0.85,
    ),
    (
        re.compile(r"(?:取締役|director|役員|executive)\s*(?:の承認|承認|approval)", re.I),
        "director",
        0.85,
    ),
    (re.compile(r"(?:CFO|経理部長|finance\s+(?:head|director))", re.I), "cfo", 0.85),
    (
        re.compile(r"(?:上長|上司|manager|supervisor)\s*(?:の承認|承認|approval)", re.I),
        "manager",
        0.80,
    ),
    # English approval patterns (broader matching)
    (re.compile(r"\b(?:requires?\s+(?:\w+\s+)*approval)\b", re.I), "approval_required", 0.85),
    (
        re.compile(r"\b(?:pre-?approv(?:al|ed)|prior\s+(?:authorization|approval))\b", re.I),
        "pre_approval",
        0.88,
    ),
]

# Category restriction patterns
_CATEGORY_PATTERNS: list[tuple[re.Pattern[str], str, str, float]] = [
    # Prohibited categories
    (
        re.compile(r"(?:禁止|不可)|(?:\b(?:prohibited|not\s+(?:allowed|permitted|eligible))\b)", re.I),
        "MUST_NOT",
        "prohibited",
        0.90,
    ),
    (
        re.compile(r"(?:認めない|対象外)|(?:\b(?:ineligible|excluded)\b)", re.I),
        "MUST_NOT",
        "excluded",
        0.85,
    ),
    # Conditional categories
    (
        re.compile(r"(?:事前承認|事前申請)|(?:\b(?:prior\s+approval|advance\s+(?:request|notice))\b)", re.I),
        "MUST",
        "pre_approval",
        0.88,
    ),
    # Documentation requirements — receipt first (more specific)
    (
        re.compile(r"(?:領収書|レシート|証憑)|(?:\b(?:receipt)\b)", re.I),
        "MUST",
        "receipt_required",
        0.85,
    ),
    (
        re.compile(r"(?:添付|提出|証拠書類)|(?:\b(?:attach(?:ed)?|submit(?:ted)?|supporting\s+document)\b)", re.I),
        "MUST",
        "documentation",
        0.80,
    ),
]

# Normative language patterns
_NORMATIVE_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    # Japanese
    (re.compile(r"(?:しなければならない|するものとする|こと$)", re.I), "MUST", 0.88),
    (re.compile(r"(?:してはならない|禁止する|認めない|不可とする)", re.I), "MUST_NOT", 0.90),
    (re.compile(r"(?:することができる|認める)", re.I), "MAY", 0.68),
    (re.compile(r"(?:するよう努める|望ましい|推奨)", re.I), "SHOULD", 0.75),
    # English
    (re.compile(r"\b(?:must\s+not|shall\s+not|is\s+prohibited)\b", re.I), "MUST_NOT", 0.90),
    (re.compile(r"\b(?:must|shall|is\s+required)\b", re.I), "MUST", 0.88),
    (re.compile(r"\b(?:should|is\s+recommended)\b", re.I), "SHOULD", 0.78),
    (re.compile(r"\b(?:may|is\s+allowed)\b", re.I), "MAY", 0.68),
]

_MIN_SENTENCE_LEN = 15
_MAX_SENTENCE_LEN = 600


class ExpenseGuidelineAnalyzer(SourceAnalyzer):
    """Extracts rules from expense policies and approval matrices.

    Detects:
    - Monetary thresholds and approval level requirements
    - Prohibited and conditional expense categories
    - Documentation and receipt requirements
    - Per-diem rates and travel policy rules

    Output patterns use department="finance" and
    applicable_subject_types=["transaction"].
    """

    async def analyze(self, context: DiscoveryContext) -> list[RawPattern]:
        """Analyze expense/finance documents for rule patterns.

        Args:
            context: Discovery context with file paths and contents.

        Returns:
            List of raw patterns extracted from expense documents.
        """
        patterns: list[RawPattern] = []

        for path, content in context.file_contents.items():
            if not self._is_expense_document(path, content):
                continue
            if len(content.strip()) < 30:
                continue

            logger.info("expense_guideline_analyzing", path=path, size=len(content))
            file_patterns = self._extract_from_document(path, content)
            patterns.extend(file_patterns)

        logger.info("expense_guideline_analysis_complete", pattern_count=len(patterns))
        return patterns

    def _is_expense_document(self, path: str, content: str) -> bool:
        """Check if a file is likely an expense/finance document.

        Args:
            path: File path.
            content: File content.

        Returns:
            True if the file appears to be expense-related.
        """
        lower_path = path.lower()
        if any(kw in lower_path for kw in _EXPENSE_FILE_KEYWORDS):
            return True

        # Content heuristic
        lower_content = content[:1000].lower()
        indicators = (
            "expense",
            "reimburs",
            "receipt",
            "approval",
            "経費",
            "精算",
            "領収書",
            "承認",
            "稟議",
        )
        return sum(1 for ind in indicators if ind in lower_content) >= 2

    def _extract_from_document(self, path: str, content: str) -> list[RawPattern]:
        """Extract rule patterns from an expense document.

        Args:
            path: File path for provenance.
            content: Full document text.

        Returns:
            List of patterns found in the document.
        """
        patterns: list[RawPattern] = []

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            sentences = _SENTENCE_SPLIT.split(line)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < _MIN_SENTENCE_LEN or len(sentence) > _MAX_SENTENCE_LEN:
                    continue

                # Try category restriction detection first (higher signal)
                cat_pattern = self._detect_category_restriction(sentence)
                if cat_pattern:
                    patterns.append(cat_pattern)
                    continue

                # Try approval level detection
                approval_pattern = self._detect_approval_requirement(sentence)
                if approval_pattern:
                    patterns.append(approval_pattern)
                    continue

                # Fall back to general normative detection
                modality, confidence = self._detect_normative(sentence)
                if modality is None:
                    continue

                # Detect amounts for extra context
                has_amount = self._has_amount(sentence)
                if has_amount:
                    confidence = min(confidence + 0.05, 0.95)

                tags = ["expense_guideline"]
                tags.extend(self._infer_expense_tags(sentence))

                patterns.append(
                    RawPattern(
                        statement=sentence,
                        modality=modality,
                        severity=self._infer_severity(modality, sentence),
                        scope=["finance/expense"],
                        tags=tags,
                        source_type="expense_guideline",
                        source_evidence=sentence,
                        confidence=confidence,
                    )
                )

        return patterns

    def _detect_category_restriction(self, sentence: str) -> RawPattern | None:
        """Detect expense category restrictions.

        Args:
            sentence: Sentence to analyze.

        Returns:
            RawPattern if a category restriction is found, else None.
        """
        for pattern, modality, category, confidence in _CATEGORY_PATTERNS:
            if pattern.search(sentence):
                tags = ["expense_guideline", f"category:{category}"]
                return RawPattern(
                    statement=sentence,
                    modality=modality,
                    severity="HIGH" if modality == "MUST_NOT" else "MEDIUM",
                    scope=["finance/expense"],
                    tags=tags,
                    source_type="expense_guideline",
                    source_evidence=sentence,
                    confidence=confidence,
                )
        return None

    def _detect_approval_requirement(self, sentence: str) -> RawPattern | None:
        """Detect approval level requirements.

        Args:
            sentence: Sentence to analyze.

        Returns:
            RawPattern if an approval requirement is found, else None.
        """
        for pattern, level, confidence in _APPROVAL_PATTERNS:
            if pattern.search(sentence):
                tags = ["expense_guideline", "approval", f"level:{level}"]
                # Boost if a monetary threshold is also present
                if self._has_amount(sentence):
                    confidence = min(confidence + 0.05, 0.95)
                    tags.append("threshold")
                return RawPattern(
                    statement=sentence,
                    modality="MUST",
                    severity="HIGH",
                    scope=["finance/expense"],
                    tags=tags,
                    source_type="expense_guideline",
                    source_evidence=sentence,
                    confidence=confidence,
                )
        return None

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

    def _has_amount(self, sentence: str) -> bool:
        """Check if a sentence contains a monetary amount.

        Args:
            sentence: Sentence to check.

        Returns:
            True if a monetary amount pattern is found.
        """
        return any(pat.search(sentence) for pat, _ in _AMOUNT_PATTERNS)

    def _infer_severity(self, modality: str, sentence: str) -> str:
        """Infer severity from modality and sentence content.

        Args:
            modality: Detected modality.
            sentence: The sentence text.

        Returns:
            Severity string.
        """
        critical_keywords = re.compile(
            r"\b(?:fraud|不正|横領|embezzlement|bribery|贈賄|"
            r"compliance|コンプライアンス|audit|監査|legal|法令)\b",
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

    def _infer_expense_tags(self, sentence: str) -> list[str]:
        """Infer expense-specific tags from sentence content.

        Args:
            sentence: The sentence text.

        Returns:
            List of inferred tag strings.
        """
        tags: list[str] = []
        lower = sentence.lower()

        tag_keywords = {
            "travel": ["travel", "出張", "旅費", "交通費", "flight", "hotel"],
            "entertainment": ["entertainment", "接待", "交際費", "dining", "meal"],
            "equipment": ["equipment", "備品", "機器", "purchase", "procurement"],
            "receipt": ["receipt", "領収書", "レシート", "証憑"],
            "per_diem": ["per diem", "日当", "per-diem", "daily allowance"],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in lower for kw in keywords):
                tags.append(tag)

        return tags

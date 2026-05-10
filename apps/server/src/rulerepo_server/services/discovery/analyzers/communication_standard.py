"""Communication standard analyzer — extracts rules from brand and comms guidelines.

Processes brand guidelines, communication manuals, email templates, and
style guides. Detects:
- Tone and style rules (formal/informal, prohibited language)
- Required disclaimers and signature conventions
- Channel-specific rules (external vs internal)
- Prohibited and mandatory language patterns

Outputs candidate rules with applicable_subject_types=["creative", "document"]
and department="marketing" or "sales".

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

# File selection: communication/brand-related filenames
_COMMS_FILE_KEYWORDS = (
    "brand",
    "style",
    "guideline",
    "communication",
    "template",
    "tone",
    "voice",
    "writing",
    "editorial",
    "email",
    "messaging",
    "social",
    "media",
    "marketing",
    "pr_",
    "press",
    "ブランド",
    "スタイル",
    "コミュニケーション",
    "文書",
    "メール",
)

# Sentence splitting
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。])\s+")

# Disclaimer / boilerplate patterns
_DISCLAIMER_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"(?:免責事項|免責)|(?:\bdisclaimer\b)", re.I), "disclaimer", 0.88),
    (re.compile(r"(?:機密)|(?:\bconfidential(?:ity)?(?:\s+notice)?\b)", re.I), "confidentiality", 0.85),
    (re.compile(r"(?:署名)|(?:\bsignature\b)\s*(?:block|line|欄)?", re.I), "signature", 0.80),
    (re.compile(r"(?:フッター|注意書き)|(?:\bfooter\b)", re.I), "footer", 0.78),
    (re.compile(r"(?:著作権|©)|(?:\bcopyright\b)", re.I), "copyright", 0.82),
    (re.compile(r"(?:法的通知)|(?:\blegal\s+notice\b)", re.I), "legal_notice", 0.85),
]

# Channel patterns — external vs internal
_CHANNEL_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"\b(?:external|社外|顧客向け|client-facing|public|対外)\b", re.I), "external", 0.82),
    (re.compile(r"\b(?:internal|社内|チーム内|team|intranet)\b", re.I), "internal", 0.80),
    (re.compile(r"\b(?:social\s+media|SNS|ソーシャルメディア|twitter|linkedin)\b", re.I), "social_media", 0.82),
    (re.compile(r"\b(?:press\s+release|プレスリリース|報道)\b", re.I), "press", 0.85),
]

# Tone/style directive patterns
_TONE_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    # Prohibited language
    (re.compile(r"(?:使用禁止|使わない)|(?:\b(?:avoid|do\s+not\s+use|never\s+use)\b)", re.I), "MUST_NOT", 0.85),
    (re.compile(r"(?:禁止表現)|(?:\b(?:prohibited\s+(?:word|term|phrase|language))\b)", re.I), "MUST_NOT", 0.88),
    (re.compile(r"(?:不適切|差別的)|(?:\b(?:inappropriate|offensive)\b)", re.I), "MUST_NOT", 0.85),
    # Required elements
    (re.compile(r"(?:必ず含める|必須)|(?:\b(?:always\s+include|must\s+include)\b)", re.I), "MUST", 0.88),
    (re.compile(r"(?:必要)|(?:\b(?:required\s+(?:in|for)|include\s+(?:the|a|an))\b)", re.I), "MUST", 0.82),
    # Preferred style
    (re.compile(r"(?:推奨|望ましい)|(?:\b(?:prefer(?:red)?|use\s+(?:instead|rather))\b)", re.I), "SHOULD", 0.78),
    (re.compile(r"(?:ベストプラクティス)|(?:\b(?:recommended|best\s+practice)\b)", re.I), "SHOULD", 0.75),
    (re.compile(r"(?:心がける|意識する)|(?:\b(?:try\s+to)\b)", re.I), "SHOULD", 0.72),
    # Permissions
    (re.compile(r"(?:使用可|許容)|(?:\b(?:may\s+use|is\s+acceptable)\b)", re.I), "MAY", 0.68),
]

# Normative patterns for general sentences
_NORMATIVE_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"(?:してはならない|禁止する)|(?:\b(?:must\s+not|shall\s+not)\b)", re.I), "MUST_NOT", 0.90),
    (re.compile(r"(?:しなければならない|ものとする|なければならない)|(?:\b(?:must|shall)\b)", re.I), "MUST", 0.88),
    (re.compile(r"(?:すべき|することが望ましい)|(?:\b(?:should)\b)", re.I), "SHOULD", 0.78),
    (re.compile(r"(?:できる|差し支えない)|(?:\b(?:may)\b)", re.I), "MAY", 0.68),
]

_MIN_SENTENCE_LEN = 15
_MAX_SENTENCE_LEN = 500


class CommunicationStandardAnalyzer(SourceAnalyzer):
    """Extracts rules from brand guidelines and communication manuals.

    Detects:
    - Prohibited and mandatory language patterns
    - Required disclaimers and boilerplate
    - Channel-specific rules (external, internal, social media, press)
    - Tone and style directives

    Output patterns use department="marketing" or "sales" and
    applicable_subject_types=["creative", "document"].
    """

    async def analyze(self, context: DiscoveryContext) -> list[RawPattern]:
        """Analyze communication/brand documents for rule patterns.

        Args:
            context: Discovery context with file paths and contents.

        Returns:
            List of raw patterns extracted from communication documents.
        """
        patterns: list[RawPattern] = []

        for path, content in context.file_contents.items():
            if not self._is_comms_document(path, content):
                continue
            if len(content.strip()) < 30:
                continue

            logger.info("communication_standard_analyzing", path=path, size=len(content))
            file_patterns = self._extract_from_document(path, content)
            patterns.extend(file_patterns)

        logger.info(
            "communication_standard_analysis_complete",
            pattern_count=len(patterns),
        )
        return patterns

    def _is_comms_document(self, path: str, content: str) -> bool:
        """Check if a file is likely a communication/brand document.

        Args:
            path: File path.
            content: File content.

        Returns:
            True if the file appears to be communication-related.
        """
        lower_path = path.lower()
        if any(kw in lower_path for kw in _COMMS_FILE_KEYWORDS):
            return True

        # Content heuristic
        lower_content = content[:1000].lower()
        indicators = (
            "brand",
            "tone",
            "voice",
            "style",
            "guideline",
            "ブランド",
            "トーン",
            "文体",
            "disclaimer",
            "template",
        )
        return sum(1 for ind in indicators if ind in lower_content) >= 2

    def _extract_from_document(self, path: str, content: str) -> list[RawPattern]:
        """Extract rule patterns from a communication document.

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

            # Remove markdown heading markers for analysis
            clean_line = re.sub(r"^#{1,6}\s+", "", line)
            # Remove bullet markers
            clean_line = re.sub(r"^\s*[-*•]\s+", "", clean_line)
            clean_line = re.sub(r"^\s*\d+[.)]\s+", "", clean_line)

            sentences = _SENTENCE_SPLIT.split(clean_line)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < _MIN_SENTENCE_LEN or len(sentence) > _MAX_SENTENCE_LEN:
                    continue

                # Try disclaimer detection first
                disclaimer = self._detect_disclaimer_rule(sentence)
                if disclaimer:
                    patterns.append(disclaimer)
                    continue

                # Try tone/style detection
                tone = self._detect_tone_rule(sentence, path)
                if tone:
                    patterns.append(tone)
                    continue

                # Fall back to general normative detection
                modality, confidence = self._detect_normative(sentence)
                if modality is None:
                    continue

                channel = self._detect_channel(sentence)
                tags = ["communication_standard"]
                if channel:
                    tags.append(f"channel:{channel}")
                tags.extend(self._infer_comms_tags(sentence, path))

                department = self._infer_department(path, sentence)

                patterns.append(
                    RawPattern(
                        statement=sentence,
                        modality=modality,
                        severity=self._infer_severity(modality, sentence),
                        scope=[f"{department}/communications"],
                        tags=tags,
                        source_type="communication_standard",
                        source_evidence=sentence,
                        confidence=confidence,
                    )
                )

        return patterns

    def _detect_disclaimer_rule(self, sentence: str) -> RawPattern | None:
        """Detect disclaimer/boilerplate requirements.

        Args:
            sentence: Sentence to analyze.

        Returns:
            RawPattern if a disclaimer rule is found, else None.
        """
        for pattern, disclaimer_type, confidence in _DISCLAIMER_PATTERNS:
            if pattern.search(sentence):
                # Disclaimers combined with normative language are stronger
                modality = "MUST"
                for norm_pat, norm_mod, _ in _NORMATIVE_PATTERNS:
                    if norm_pat.search(sentence):
                        modality = norm_mod
                        break

                tags = ["communication_standard", "disclaimer", disclaimer_type]
                return RawPattern(
                    statement=sentence,
                    modality=modality,
                    severity="HIGH" if disclaimer_type in ("confidentiality", "legal_notice") else "MEDIUM",
                    scope=["communications/boilerplate"],
                    tags=tags,
                    source_type="communication_standard",
                    source_evidence=sentence,
                    confidence=confidence,
                )
        return None

    def _detect_tone_rule(self, sentence: str, path: str = "") -> RawPattern | None:
        """Detect tone and style directives.

        Args:
            sentence: Sentence to analyze.
            path: Source file path for department inference.

        Returns:
            RawPattern if a tone/style rule is found, else None.
        """
        for pattern, modality, confidence in _TONE_PATTERNS:
            if pattern.search(sentence):
                channel = self._detect_channel(sentence)
                department = self._infer_department(path, sentence)
                tags = ["communication_standard", "tone_style"]
                if channel:
                    tags.append(f"channel:{channel}")

                scope = [f"{department}/communications"]
                if channel:
                    scope.append(f"communications/{channel}")

                return RawPattern(
                    statement=sentence,
                    modality=modality,
                    severity="MEDIUM" if modality in ("MUST", "MUST_NOT") else "LOW",
                    scope=scope,
                    tags=tags,
                    source_type="communication_standard",
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

    def _detect_channel(self, sentence: str) -> str | None:
        """Detect channel context (external, internal, social, press).

        Args:
            sentence: Sentence to check.

        Returns:
            Channel string or None.
        """
        for pattern, channel, _ in _CHANNEL_PATTERNS:
            if pattern.search(sentence):
                return channel
        return None

    def _infer_department(self, path: str, sentence: str) -> str:
        """Infer owning department from file path and sentence.

        Args:
            path: Source file path.
            sentence: The sentence text.

        Returns:
            Department string ("marketing" or "sales").
        """
        lower = (path + " " + sentence).lower()
        if any(kw in lower for kw in ("sales", "営業", "商談", "proposal")):
            return "sales"
        return "marketing"

    def _infer_severity(self, modality: str, sentence: str) -> str:
        """Infer severity from modality and sentence content.

        Args:
            modality: Detected modality.
            sentence: The sentence text.

        Returns:
            Severity string.
        """
        critical_keywords = re.compile(
            r"\b(?:legal|regulatory|compliance|confidential|"
            r"defamation|libel|trademark|copyright|"
            r"法令|法的|商標|著作権)\b",
            re.IGNORECASE,
        )
        if critical_keywords.search(sentence):
            if modality in ("MUST", "MUST_NOT"):
                return "CRITICAL"
            return "HIGH"

        if modality in ("MUST", "MUST_NOT"):
            return "MEDIUM"
        return "LOW"

    def _infer_comms_tags(self, sentence: str, path: str) -> list[str]:
        """Infer communication-specific tags from content.

        Args:
            sentence: The sentence text.
            path: Source file path.

        Returns:
            List of inferred tag strings.
        """
        tags: list[str] = []
        lower = (sentence + " " + path).lower()

        tag_keywords = {
            "email": ["email", "メール", "e-mail"],
            "social_media": ["social", "sns", "twitter", "linkedin", "facebook"],
            "press": ["press", "media", "プレス", "報道"],
            "branding": ["brand", "logo", "ブランド", "ロゴ", "color", "font"],
            "template": ["template", "テンプレート", "定型"],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in lower for kw in keywords):
                tags.append(tag)

        return tags

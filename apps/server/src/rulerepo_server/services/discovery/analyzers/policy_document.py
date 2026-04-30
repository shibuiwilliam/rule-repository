"""Analyzer for general policy documents — HR policies, legal contracts, compliance handbooks.

Unlike the ClaudeMdAnalyzer (which only processes CLAUDE.md/AGENTS.md files),
this analyzer processes ANY text or markdown file and extracts normative
statements from natural-language prose, not just bullet points.

Handles:
- HR policies ("Employees must submit timesheets by Friday")
- Legal contracts ("The contractor shall not disclose confidential information")
- Compliance handbooks ("All transactions above $10,000 must be reported")
- Internal procedures ("Managers should review expense reports within 5 days")
- Safety regulations ("Workers must wear protective equipment at all times")
- Any document containing rules expressed in natural language
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

# Skip files that other analyzers handle
_SKIP_PATTERNS = re.compile(
    r"(CLAUDE|AGENTS).*\.md$"
    r"|\.eslintrc"
    r"|tsconfig\.json$"
    r"|\.prettierrc"
    r"|ruff\.toml$"
    r"|pyproject\.toml$",
    re.IGNORECASE,
)

# Sentence-ending markers
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")

# Normative keyword patterns with modality and base confidence
_NORMATIVE_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    # Prohibitions (strongest signal)
    (
        re.compile(r"\b(?:must\s+not|shall\s+not|is\s+(?:not\s+)?prohibited)\b", re.I),
        "MUST_NOT",
        0.90,
    ),
    (
        re.compile(r"\b(?:never|under\s+no\s+circumstances|strictly\s+forbidden)\b", re.I),
        "MUST_NOT",
        0.88,
    ),
    (
        re.compile(r"\b(?:may\s+not|cannot|is\s+not\s+(?:allowed|permitted))\b", re.I),
        "MUST_NOT",
        0.85,
    ),
    # Obligations
    (re.compile(r"\b(?:must|shall|is\s+required\s+to|are\s+required\s+to)\b", re.I), "MUST", 0.90),
    (re.compile(r"\b(?:is\s+mandatory|are\s+obligated|it\s+is\s+required)\b", re.I), "MUST", 0.85),
    (re.compile(r"\b(?:needs?\s+to|has?\s+to|are\s+expected\s+to)\b", re.I), "MUST", 0.80),
    # Recommendations
    (re.compile(r"\b(?:should\s+not|ought\s+not)\b", re.I), "SHOULD", 0.80),
    (
        re.compile(r"\b(?:should|ought\s+to|is\s+recommended|are\s+encouraged)\b", re.I),
        "SHOULD",
        0.80,
    ),
    (
        re.compile(r"\b(?:it\s+is\s+advisable|best\s+practice|are\s+advised)\b", re.I),
        "SHOULD",
        0.75,
    ),
    (re.compile(r"\b(?:always|at\s+all\s+times|in\s+every\s+case)\b", re.I), "SHOULD", 0.75),
    # Permissions
    (re.compile(r"\b(?:may|is\s+allowed|is\s+permitted|are\s+authorized)\b", re.I), "MAY", 0.70),
    (re.compile(r"\b(?:can|is\s+eligible|at\s+(?:their|your)\s+discretion)\b", re.I), "MAY", 0.65),
]

# Section heading pattern (markdown and plain text)
_HEADING_MD = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_HEADING_CAPS = re.compile(r"^([A-Z][A-Z\s]{5,})$", re.MULTILINE)  # ALL CAPS headings

# Minimum viable sentence length
_MIN_SENTENCE_LEN = 20
_MAX_SENTENCE_LEN = 500


class PolicyDocumentAnalyzer(SourceAnalyzer):
    """Extracts normative statements from general policy documents.

    Processes any text or markdown file that isn't handled by other analyzers.
    Splits content into sentences, detects deontic language (must, shall,
    should, may, etc.), and uses document headings as scope context.

    Supports: HR policies, legal contracts, compliance handbooks, safety
    regulations, internal procedures, and any prose containing rules.
    """

    async def analyze(self, context: DiscoveryContext) -> list[RawPattern]:
        """Analyze all non-code text files for normative statements.

        Args:
            context: Discovery context with file paths and contents.

        Returns:
            List of raw patterns extracted from policy documents.
        """
        patterns: list[RawPattern] = []

        for path, content in context.file_contents.items():
            filename = path.split("/")[-1]

            # Skip files handled by other analyzers
            if _SKIP_PATTERNS.search(filename):
                continue

            # Only process text-like files
            if not self._is_text_file(filename):
                continue

            if len(content.strip()) < 30:
                continue

            logger.info("policy_document_analyzing", path=path, size=len(content))
            file_patterns = self._extract_from_document(path, content)
            patterns.extend(file_patterns)

        logger.info("policy_document_analysis_complete", pattern_count=len(patterns))
        return patterns

    def _is_text_file(self, filename: str) -> bool:
        """Check if a file is a text document by extension.

        Args:
            filename: The filename to check.

        Returns:
            True if the file appears to be a text document.
        """
        text_extensions = (
            ".md",
            ".markdown",
            ".txt",
            ".text",
            ".rst",
            ".adoc",
            ".asciidoc",
            ".org",
            ".html",
            ".htm",
            ".csv",
            ".tsv",
            ".policy",
            ".doc",
            ".docx",  # won't read binary, but won't crash
        )
        lower = filename.lower()
        # Accept known text extensions or files without extension (often text)
        return any(lower.endswith(ext) for ext in text_extensions) or "." not in filename

    def _extract_from_document(self, path: str, content: str) -> list[RawPattern]:
        """Extract normative statements from a document.

        Args:
            path: File path for provenance.
            content: Full document text.

        Returns:
            List of patterns found in the document.
        """
        patterns: list[RawPattern] = []

        # Build section map: track which heading each line falls under
        sections = self._build_section_map(content)

        # Split into sentences
        sentences = self._split_sentences(content)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < _MIN_SENTENCE_LEN or len(sentence) > _MAX_SENTENCE_LEN:
                continue

            modality, confidence = self._detect_normative(sentence)
            if modality is None:
                continue

            # Find which section this sentence belongs to
            scope = self._get_section_scope(sentence, content, sections)

            # Infer domain tags from content
            tags = self._infer_tags(sentence, path)

            patterns.append(
                RawPattern(
                    statement=sentence,
                    modality=modality,
                    severity=self._infer_severity(modality, sentence),
                    scope=scope,
                    tags=tags,
                    source_type="policy_document",
                    source_evidence=sentence,
                    confidence=confidence,
                )
            )

        return patterns

    def _build_section_map(self, content: str) -> list[tuple[int, str]]:
        """Build a map of (character_offset, heading_text) for scope resolution.

        Args:
            content: Full document text.

        Returns:
            Sorted list of (offset, heading_text) tuples.
        """
        sections: list[tuple[int, str]] = []

        for match in _HEADING_MD.finditer(content):
            sections.append((match.start(), match.group(2).strip()))

        for match in _HEADING_CAPS.finditer(content):
            text = match.group(1).strip()
            if len(text) > 3:  # skip very short all-caps words
                sections.append((match.start(), text.title()))

        sections.sort(key=lambda x: x[0])
        return sections

    def _get_section_scope(self, sentence: str, content: str, sections: list[tuple[int, str]]) -> list[str]:
        """Determine which section a sentence falls under.

        Args:
            sentence: The sentence text.
            content: Full document text.
            sections: Sorted section map.

        Returns:
            List of scope strings from the enclosing section.
        """
        pos = content.find(sentence)
        if pos < 0:
            return []

        # Find the most recent heading before this position
        current_section = ""
        for offset, heading in sections:
            if offset > pos:
                break
            current_section = heading

        if current_section:
            return [current_section.lower().replace(" ", "-")]
        return []

    def _split_sentences(self, content: str) -> list[str]:
        """Split content into individual sentences.

        Handles both prose paragraphs and bullet/numbered lists.

        Args:
            content: Full document text.

        Returns:
            List of sentence strings.
        """
        sentences: list[str] = []

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Remove markdown heading markers
            line = re.sub(r"^#{1,6}\s+", "", line)

            # Remove bullet/numbered list markers
            line = re.sub(r"^\s*[-*•]\s+", "", line)
            line = re.sub(r"^\s*\d+[.)]\s+", "", line)
            line = re.sub(r"^\s*[a-z][.)]\s+", "", line)

            if not line:
                continue

            # Split long lines into sentences
            parts = _SENTENCE_SPLIT.split(line)
            sentences.extend(parts)

        return sentences

    def _detect_normative(self, sentence: str) -> tuple[str | None, float]:
        """Detect normative (deontic) language in a sentence.

        Args:
            sentence: The sentence to analyze.

        Returns:
            Tuple of (modality, confidence) or (None, 0.0) if not normative.
        """
        for pattern, modality, confidence in _NORMATIVE_PATTERNS:
            if pattern.search(sentence):
                return modality, confidence
        return None, 0.0

    def _infer_severity(self, modality: str, sentence: str) -> str:
        """Infer severity from modality and sentence content.

        Args:
            modality: Detected modality.
            sentence: The sentence text for keyword analysis.

        Returns:
            Severity string.
        """
        # Check for critical keywords
        critical_keywords = re.compile(
            r"\b(?:safety|security|legal|compliance|regulatory|criminal|liability"
            r"|confidential|breach|violation|termination|immediate)\b",
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

    def _infer_tags(self, sentence: str, path: str) -> list[str]:
        """Infer domain tags from sentence content and file path.

        Args:
            sentence: The sentence text.
            path: Source file path.

        Returns:
            List of inferred tag strings.
        """
        tags: list[str] = ["policy_document"]
        lower = sentence.lower()
        path_lower = path.lower()

        domain_keywords = {
            "hr": ["employee", "staff", "worker", "overtime", "leave", "payroll", "hiring"],
            "legal": ["contract", "agreement", "liability", "indemnif", "clause", "party"],
            "compliance": ["regulat", "audit", "report", "compliance", "standard", "certif"],
            "finance": ["expense", "budget", "payment", "invoice", "procurement", "purchase"],
            "safety": ["safety", "hazard", "protective", "emergency", "incident", "injury"],
            "security": ["password", "access", "encrypt", "confidential", "data protection"],
            "conduct": ["conduct", "behavior", "harassment", "discrimination", "ethics"],
            "operations": ["procedure", "process", "workflow", "approval", "deadline"],
        }

        for tag, keywords in domain_keywords.items():
            if any(kw in lower or kw in path_lower for kw in keywords):
                tags.append(tag)

        return tags

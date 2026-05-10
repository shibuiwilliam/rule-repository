"""Brand guidelines extractor for marketing plugin.

Parses brand guideline documents (text/markdown) and extracts
candidate rules covering prohibited phrases, required disclaimers,
tone/voice requirements, competitor mention restrictions, and
logo/trademark usage constraints.

See: CLAUDE.md SS14.11
"""

from __future__ import annotations

import re
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

LLMCallable = Callable[[str], Coroutine[Any, Any, str]]

logger = structlog.get_logger(__name__)

# Section heading patterns commonly found in brand guidelines
_SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "prohibited": re.compile(
        r"(?i)^#+\s*(prohibited|forbidden|do\s*not\s*use|ng\s*ワード|禁止|使用禁止)",
        re.MULTILINE,
    ),
    "disclaimer": re.compile(
        r"(?i)^#+\s*(disclaimer|required\s*notice|免責|注意書き|必須表記)",
        re.MULTILINE,
    ),
    "tone": re.compile(
        r"(?i)^#+\s*(tone|voice|brand\s*voice|トーン|ボイス|文体)",
        re.MULTILINE,
    ),
    "competitor": re.compile(
        r"(?i)^#+\s*(competitor|competitive|比較|競合|他社)",
        re.MULTILINE,
    ),
    "logo": re.compile(
        r"(?i)^#+\s*(logo|trademark|brand\s*mark|ロゴ|商標|ブランドマーク)",
        re.MULTILINE,
    ),
}

# Patterns for extracting list items from markdown
_LIST_ITEM_PATTERN = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)
_NUMBERED_ITEM_PATTERN = re.compile(r"^\s*\d+[.)]\s+(.+)$", re.MULTILINE)


def _extract_section(content: str, start_match: re.Match[str]) -> str:
    """Extract text from a section heading to the next heading.

    Args:
        content: Full document text.
        start_match: Regex match for the section heading.

    Returns:
        Section body text (excluding the heading itself).
    """
    start_pos = start_match.end()
    next_heading = re.search(r"^#+\s+", content[start_pos:], re.MULTILINE)
    if next_heading:
        return content[start_pos : start_pos + next_heading.start()].strip()
    return content[start_pos:].strip()


def _extract_list_items(section_text: str) -> list[str]:
    """Extract bullet or numbered list items from section text.

    Args:
        section_text: Text within a section.

    Returns:
        List of extracted item strings.
    """
    items: list[str] = []
    for pattern in (_LIST_ITEM_PATTERN, _NUMBERED_ITEM_PATTERN):
        items.extend(m.group(1).strip() for m in pattern.finditer(section_text))
    return items


def _extract_prohibited_phrases(section_text: str) -> list[dict[str, Any]]:
    """Generate MUST_NOT rules from prohibited phrases section.

    Args:
        section_text: The prohibited phrases section body.

    Returns:
        List of candidate rule dicts.
    """
    items = _extract_list_items(section_text)
    rules: list[dict[str, Any]] = []
    for item in items:
        rules.append(
            {
                "statement": f"Marketing content MUST NOT use the phrase or word: '{item}'",
                "modality": "MUST_NOT",
                "severity": "HIGH",
                "scope": ["marketing/brand", "marketing/external"],
                "applicable_subject_types": ["creative", "document"],
                "tags": ["brand-guidelines", "prohibited-phrase"],
                "source_section": "prohibited_phrases",
            }
        )
    return rules


def _extract_disclaimer_rules(section_text: str) -> list[dict[str, Any]]:
    """Generate MUST rules from required disclaimers section.

    Args:
        section_text: The disclaimers section body.

    Returns:
        List of candidate rule dicts.
    """
    items = _extract_list_items(section_text)
    rules: list[dict[str, Any]] = []

    # Try to detect content-type-specific disclaimers (e.g., "For health: ...")
    content_type_pattern = re.compile(r"(?i)(?:for|対象[:\uff1a]?)\s*(\w+)[:\uff1a]\s*(.+)")

    for item in items:
        ct_match = content_type_pattern.match(item)
        if ct_match:
            content_type = ct_match.group(1).strip()
            disclaimer_text = ct_match.group(2).strip()
            statement = f"Marketing content for '{content_type}' MUST include the disclaimer: '{disclaimer_text}'"
        else:
            statement = f"Marketing content MUST include the disclaimer: '{item}'"

        rules.append(
            {
                "statement": statement,
                "modality": "MUST",
                "severity": "HIGH",
                "scope": ["marketing/brand", "marketing/external"],
                "applicable_subject_types": ["creative", "document"],
                "tags": ["brand-guidelines", "required-disclaimer"],
                "source_section": "disclaimers",
            }
        )
    return rules


def _extract_tone_rules(section_text: str) -> list[dict[str, Any]]:
    """Generate SHOULD rules from tone/voice section.

    Args:
        section_text: The tone/voice section body.

    Returns:
        List of candidate rule dicts.
    """
    items = _extract_list_items(section_text)
    rules: list[dict[str, Any]] = []
    for item in items:
        rules.append(
            {
                "statement": f"Marketing content SHOULD follow the tone guideline: '{item}'",
                "modality": "SHOULD",
                "severity": "MEDIUM",
                "scope": ["marketing/brand", "marketing/external"],
                "applicable_subject_types": ["creative", "document"],
                "tags": ["brand-guidelines", "tone-voice"],
                "source_section": "tone_voice",
            }
        )
    return rules


def _extract_competitor_rules(section_text: str) -> list[dict[str, Any]]:
    """Generate MUST_NOT rules from competitor mention restrictions.

    Args:
        section_text: The competitor section body.

    Returns:
        List of candidate rule dicts.
    """
    items = _extract_list_items(section_text)
    rules: list[dict[str, Any]] = []
    for item in items:
        rules.append(
            {
                "statement": (f"Marketing content MUST NOT mention competitor or make comparative claims: '{item}'"),
                "modality": "MUST_NOT",
                "severity": "HIGH",
                "scope": ["marketing/brand", "marketing/external"],
                "applicable_subject_types": ["creative", "document"],
                "tags": ["brand-guidelines", "competitor-restriction"],
                "source_section": "competitor_restrictions",
            }
        )
    return rules


def _extract_logo_rules(section_text: str) -> list[dict[str, Any]]:
    """Generate MUST rules from logo/trademark usage section.

    Args:
        section_text: The logo/trademark section body.

    Returns:
        List of candidate rule dicts.
    """
    items = _extract_list_items(section_text)
    rules: list[dict[str, Any]] = []
    for item in items:
        rules.append(
            {
                "statement": f"Brand assets MUST follow the usage rule: '{item}'",
                "modality": "MUST",
                "severity": "HIGH",
                "scope": ["marketing/brand", "marketing/external"],
                "applicable_subject_types": ["creative", "document"],
                "tags": ["brand-guidelines", "logo-trademark"],
                "source_section": "logo_trademark",
            }
        )
    return rules


class BrandGuidelinesExtractor:
    """Extractor for brand guideline documents.

    Parses markdown/text brand guidelines and produces candidate rules
    covering prohibited phrases, required disclaimers, tone/voice
    requirements, competitor mention restrictions, and logo/trademark
    usage constraints.
    """

    @property
    def name(self) -> str:
        return "brand_guidelines_extractor"

    @property
    def domain(self) -> str:
        return "marketing"

    @property
    def supported_source_types(self) -> list[str]:
        return ["brand_guidelines", "style_guide", "voice_tone_guide"]

    async def extract(
        self,
        content: bytes,
        source_type: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract candidate rules from a brand guidelines document.

        Args:
            content: The document text (markdown or plain text).
            source_type: One of the supported source types.
            metadata: Optional metadata (e.g., brand name, version).

        Returns:
            List of candidate rule dicts ready for review/import.
        """
        text = content.decode("utf-8", errors="replace")
        brand_name = metadata.get("brand_name", "")

        logger.info(
            "brand_guidelines_extraction_started",
            source_type=source_type,
            content_length=len(text),
            brand_name=brand_name,
        )

        candidates: list[dict[str, Any]] = []

        extractors: dict[str, Any] = {
            "prohibited": _extract_prohibited_phrases,
            "disclaimer": _extract_disclaimer_rules,
            "tone": _extract_tone_rules,
            "competitor": _extract_competitor_rules,
            "logo": _extract_logo_rules,
        }

        for section_key, pattern in _SECTION_PATTERNS.items():
            match = pattern.search(text)
            if match:
                section_text = _extract_section(text, match)
                extractor_fn = extractors.get(section_key)
                if extractor_fn:
                    section_rules = extractor_fn(section_text)
                    candidates.extend(section_rules)
                    logger.debug(
                        "brand_section_extracted",
                        section=section_key,
                        rule_count=len(section_rules),
                    )

        # Enrich all candidates with metadata
        for candidate in candidates:
            if brand_name:
                candidate["tags"] = [*candidate.get("tags", []), f"brand:{brand_name}"]
            candidate["extraction_source"] = source_type
            candidate["extraction_metadata"] = metadata

        logger.info(
            "brand_guidelines_extraction_complete",
            total_candidates=len(candidates),
            source_type=source_type,
        )

        return candidates

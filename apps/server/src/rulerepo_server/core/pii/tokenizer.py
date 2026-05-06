"""PII tokenizer — replace PII with stable, reversible placeholders.

CLAUDE.md §9.8 / Tier 1.6: inputs to Gemini pass through this tokenizer which
replaces detected PII with stable placeholders ([PERSON_1], [EMAIL_1], etc.).
The reverse-mapping dict is encrypted and persisted with the evaluation record.
De-tokenization happens locally on the LLM response before persistence.

Supports locales: ``ja`` (Japanese) and ``en`` (English) as configured by
``PII_TOKENIZER_LOCALES``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------
# Each entry: (category_prefix, compiled regex)
# The category prefix is used to build placeholders like [EMAIL_1], [PHONE_2].

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Email — must come before generic word patterns
    (
        "EMAIL",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    # Credit-card-like 16-digit numbers (with optional separators)
    (
        "ID",
        re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    ),
    # IP addresses (v4)
    (
        "IP",
        re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    ),
    # Phone — international / US format
    (
        "PHONE",
        re.compile(
            r"(?<!\d)"  # not preceded by digit
            r"(?:\+\d{1,3}[-.\s]?)?"  # optional country code
            r"(?:\(?\d{1,4}\)?[-.\s]?)?"  # optional area code
            r"\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
            r"(?!\d)"  # not followed by digit
        ),
    ),
    # Phone — Japanese domestic (0X-XXXX-XXXX, 0XX-XXX-XXXX, etc.)
    (
        "PHONE",
        re.compile(r"\b0\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{3,4}\b"),
    ),
    # Japanese full-width katakana names (two or more katakana words separated
    # by a middle dot or space).  This is a *basic* heuristic; real NER would
    # use a model.
    (
        "PERSON",
        re.compile(
            r"[\u30A0-\u30FF\u31F0-\u31FF]+"  # first katakana word
            r"[\u30FB\u3000\s]"  # separator (middle dot or space)
            r"[\u30A0-\u30FF\u31F0-\u31FF]+"  # second katakana word
        ),
    ),
    # Japanese kanji names — two-to-four kanji surname + space/dot + two-to-four
    # kanji given name.  Very rough; avoids matching general kanji text by
    # requiring exactly the right length on each side of the separator.
    (
        "PERSON",
        re.compile(
            r"(?<![一-龥])"  # not preceded by kanji
            r"[一-龥]{2,4}"  # surname
            r"[\s\u3000]"  # separator
            r"[一-龥]{2,4}"  # given name
            r"(?![一-龥])"  # not followed by kanji
        ),
    ),
]


@dataclass(frozen=True, slots=True)
class _Replacement:
    """Internal record of a single PII replacement."""

    category: str
    index: int
    original: str
    placeholder: str


@dataclass(slots=True)
class PiiTokenizer:
    """Stateless PII tokenizer.

    Each call to :meth:`tokenize` is independent: placeholder counters reset.

    Example::

        tokenizer = PiiTokenizer()
        text, mapping = tokenizer.tokenize("Email john@acme.com or jane@acme.com")
        # text == "Email [EMAIL_1] or [EMAIL_2]"
        # mapping == {"[EMAIL_1]": "john@acme.com", "[EMAIL_2]": "jane@acme.com"}
        original = tokenizer.detokenize(text, mapping)
        # original == "Email john@acme.com or jane@acme.com"
    """

    # No instance state needed — the class exists for namespacing and future
    # configuration (e.g. locale selection).
    _placeholder: str = field(default="", init=False, repr=False)

    def tokenize(self, text: str) -> tuple[str, dict[str, str]]:
        """Replace PII in *text* with stable placeholders.

        Args:
            text: Input text potentially containing PII.

        Returns:
            A tuple of ``(tokenized_text, reverse_mapping)`` where
            *reverse_mapping* maps each placeholder back to the original
            value.  The mapping is suitable for persistence (encrypt before
            storing).
        """
        # Collect all matches across all patterns first, then replace from
        # right to left so that earlier indices stay valid.
        matches: list[tuple[int, int, str, str]] = []  # (start, end, category, original)
        seen_spans: list[tuple[int, int]] = []

        for category, pattern in _PATTERNS:
            for m in pattern.finditer(text):
                start, end = m.start(), m.end()
                # Skip overlapping matches (first pattern wins)
                if any(not (end <= s or start >= e) for s, e in seen_spans):
                    continue
                matches.append((start, end, category, m.group()))
                seen_spans.append((start, end))

        # Sort by start position (ascending), then replace right-to-left.
        matches.sort(key=lambda x: x[0])

        # Assign sequential indices per category.
        category_counters: dict[str, int] = {}
        replacements: list[_Replacement] = []
        for start, end, category, original in matches:
            idx = category_counters.get(category, 0) + 1
            category_counters[category] = idx
            placeholder = f"[{category}_{idx}]"
            replacements.append(
                _Replacement(
                    category=category,
                    index=idx,
                    original=original,
                    placeholder=placeholder,
                )
            )

        # Build the reverse mapping.
        reverse_mapping: dict[str, str] = {r.placeholder: r.original for r in replacements}

        # Replace right-to-left to preserve indices.
        result = list(text)
        for (start, end, _cat, _orig), repl in reversed(list(zip(matches, replacements, strict=True))):
            result[start:end] = list(repl.placeholder)

        return "".join(result), reverse_mapping

    def detokenize(self, text: str, mapping: dict[str, str]) -> str:
        """Restore original PII values from placeholders.

        Args:
            text: Tokenized text containing placeholders.
            mapping: The reverse mapping returned by :meth:`tokenize`.

        Returns:
            Text with placeholders replaced by original PII values.
        """
        result = text
        for placeholder, original in mapping.items():
            result = result.replace(placeholder, original)
        return result

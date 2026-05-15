"""Normative sentence detection.

Identifies sentences with normative content (obligations, prohibitions,
permissions) within extracted document sections.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Normative indicator patterns
_MUST_PATTERNS = re.compile(
    r"\b(must|shall|required|mandatory|obligat|prohibited|forbidden)\b",
    re.IGNORECASE,
)
_SHOULD_PATTERNS = re.compile(
    r"\b(should|recommend|advis|prefer|expect)\b",
    re.IGNORECASE,
)
_MAY_PATTERNS = re.compile(
    r"\b(may|can|optional|permit|allow)\b",
    re.IGNORECASE,
)
# Japanese normative patterns
_JA_NORMATIVE_PATTERNS = re.compile(
    r"(なければならない|してはならない|するものとする|しなければならない|できる|することができる|努めなければならない|禁止する|義務|遵守)",
)


@dataclass
class NormativeSentence:
    """A sentence identified as containing normative content."""

    text: str
    section_id: str
    modality_hint: str  # "MUST", "SHOULD", "MAY", "INFO"
    confidence: float  # 0.0 to 1.0
    language: str = "en"


def detect_normative_sentences(
    text: str,
    section_id: str,
    language: str = "en",
) -> list[NormativeSentence]:
    """Detect normative sentences in a text block.

    Uses regex-based heuristics for initial detection.
    LLM refinement is applied in a separate stage.
    """
    results: list[NormativeSentence] = []

    # Split into sentences (simple heuristic)
    sentences = re.split(r"[。\n]", text) if language == "ja" else re.split(r"(?<=[.!?])\s+", text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 10:
            continue

        modality = "INFO"
        confidence = 0.0

        if language == "ja":
            if _JA_NORMATIVE_PATTERNS.search(sentence):
                modality = "MUST"
                confidence = 0.7
        else:
            if _MUST_PATTERNS.search(sentence):
                modality = "MUST"
                confidence = 0.8
            elif _SHOULD_PATTERNS.search(sentence):
                modality = "SHOULD"
                confidence = 0.6
            elif _MAY_PATTERNS.search(sentence):
                modality = "MAY"
                confidence = 0.5

        if confidence > 0:
            results.append(
                NormativeSentence(
                    text=sentence,
                    section_id=section_id,
                    modality_hint=modality,
                    confidence=confidence,
                    language=language,
                )
            )

    return results

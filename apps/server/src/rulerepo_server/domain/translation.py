"""Polyglot rule translations -- multi-language rule management.

See IMPROVEMENT.md RR-020.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

_UTC = UTC


@dataclass
class RuleTranslation:
    """A translation of a rule into another language."""

    id: UUID = field(default_factory=uuid4)
    rule_id: UUID = field(default_factory=uuid4)  # original rule
    language: str = ""  # BCP-47 language tag (e.g., "en", "ja", "de")
    statement: str = ""  # translated statement text
    translator: str = ""  # who/what translated (e.g., "human", "gemini")
    equivalence_score: float = 0.0  # semantic similarity to original (0-1)
    last_verified_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=_UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=_UTC))


@dataclass
class TranslationVerification:
    """Result of verifying a translation's accuracy."""

    translation_id: UUID = field(default_factory=uuid4)
    original_statement: str = ""
    translated_statement: str = ""
    back_translated: str = ""  # translated back to original language
    equivalence_score: float = 0.0
    verified_at: datetime = field(default_factory=lambda: datetime.now(tz=_UTC))
    passed: bool = True  # True if score >= threshold

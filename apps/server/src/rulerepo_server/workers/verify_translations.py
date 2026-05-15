"""Background worker for translation equivalence verification.

Periodically re-runs Gemini equivalence checks on translation pairs
and updates scores. Drops below TRANSLATION_EQUIVALENCE_THRESHOLD
trigger alerts.

See CLAUDE.md §14.8.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_EQUIVALENCE_THRESHOLD = 0.85


@dataclass
class TranslationVerificationResult:
    """Result of verifying equivalence between two rule translations."""

    rule_id: str
    sibling_rule_id: str
    source_language: str
    target_language: str
    equivalence_score: float
    verified_at: datetime
    below_threshold: bool
    explanation: str = ""


async def verify_translation_pair(
    *,
    rule_statement: str,
    rule_language: str,
    sibling_statement: str,
    sibling_language: str,
    rule_id: str = "",
    sibling_rule_id: str = "",
    threshold: float = DEFAULT_EQUIVALENCE_THRESHOLD,
) -> TranslationVerificationResult:
    """Verify semantic equivalence between two rule translations.

    In production, this calls Gemini to score equivalence.
    This stub returns a placeholder score for testing.

    The actual Gemini call would use structured output:
    - Score (0-1) of semantic equivalence
    - Explanation of differences
    - Suggested corrections
    """
    logger.info(
        "verify_translation_pair",
        rule_id=rule_id,
        sibling_rule_id=sibling_rule_id,
        source_lang=rule_language,
        target_lang=sibling_language,
    )

    # Stub: return a high score for non-empty statements
    score = 0.9 if (rule_statement and sibling_statement) else 0.0
    now = datetime.now(UTC)

    return TranslationVerificationResult(
        rule_id=rule_id,
        sibling_rule_id=sibling_rule_id,
        source_language=rule_language,
        target_language=sibling_language,
        equivalence_score=score,
        verified_at=now,
        below_threshold=score < threshold,
        explanation="Stub verification — actual Gemini verification not yet implemented.",
    )


async def verify_all_translations(
    *,
    translation_pairs: list[dict],
    threshold: float = DEFAULT_EQUIVALENCE_THRESHOLD,
) -> list[TranslationVerificationResult]:
    """Verify all translation pairs and return results.

    Called by the daily background job (cron).
    """
    results = []
    for pair in translation_pairs:
        result = await verify_translation_pair(
            rule_statement=pair.get("rule_statement", ""),
            rule_language=pair.get("rule_language", "en"),
            sibling_statement=pair.get("sibling_statement", ""),
            sibling_language=pair.get("sibling_language", "ja"),
            rule_id=pair.get("rule_id", ""),
            sibling_rule_id=pair.get("sibling_rule_id", ""),
            threshold=threshold,
        )
        results.append(result)

    # Log summary
    below = sum(1 for r in results if r.below_threshold)
    logger.info(
        "translation_verification_complete",
        total=len(results),
        below_threshold=below,
        threshold=threshold,
    )

    return results

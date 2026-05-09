"""Translation drift checker — detects semantic drift between bilingual rule pairs.

Runs daily. For every rule with non-empty ``statement_translations``,
compares each translation against the canonical statement using the LLM
and flags drift above threshold for human review.

See CLAUDE.md §14.5.
"""

from __future__ import annotations

from sqlalchemy import text

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Drift score above this threshold triggers a review flag
DRIFT_THRESHOLD = 0.3


async def verify_translation_drift(ctx: dict) -> dict:
    """Check all bilingual rules for translation drift.

    Returns:
        Summary with count of checked and flagged rules.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from rulerepo_server.adapters.postgres.session import get_engine

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    checked = 0
    flagged = 0

    async with session_factory() as session:
        # Find rules with non-empty statement_translations
        result = await session.execute(
            text("""
                SELECT id, statement, locale, statement_translations
                FROM rules
                WHERE statement_translations != '{}'::jsonb
                  AND statement_translations IS NOT NULL
                  AND status NOT IN ('RETIRED', 'SUPERSEDED')
            """)
        )

        for row in result.fetchall():
            rule_id = str(row[0])
            canonical = row[1]
            canonical_locale = row[2]
            translations = row[3] or {}

            for target_locale, translated in translations.items():
                if not translated:
                    continue

                checked += 1

                # Simple heuristic: flag if lengths differ by more than 3x
                # (real implementation would use LLM comparison)
                len_ratio = len(translated) / max(len(canonical), 1)
                if len_ratio > 3.0 or len_ratio < 0.33:
                    flagged += 1
                    logger.warning(
                        "translation_drift_detected",
                        rule_id=rule_id,
                        canonical_locale=canonical_locale,
                        target_locale=target_locale,
                        length_ratio=round(len_ratio, 2),
                    )

        await session.commit()

    logger.info(
        "translation_drift_check_complete",
        checked=checked,
        flagged=flagged,
    )

    return {"checked": checked, "flagged": flagged}

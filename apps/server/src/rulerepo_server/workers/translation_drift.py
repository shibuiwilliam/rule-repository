"""Translation drift checker — detects semantic drift between bilingual rule pairs.

Runs daily.  For every rule with non-empty ``statement_translations``,
compares each translation against the canonical statement using the
PolyglotVerifier and flags drift above threshold for human review.

See CLAUDE.md §9.
"""

from __future__ import annotations

from sqlalchemy import text

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Drift score below this threshold triggers a review flag.
DRIFT_THRESHOLD = 0.85


async def verify_translation_drift(ctx: dict) -> dict:
    """Check all bilingual rules for translation drift.

    Returns:
        Summary with count of checked and flagged rules.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from rulerepo_server.adapters.postgres.session import get_engine
    from rulerepo_server.services.polyglot.verifier import PolyglotVerifier

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    gemini_client = None
    try:
        from rulerepo_server.adapters.gemini.client import get_gemini_client

        gemini_client = get_gemini_client()
    except Exception:
        logger.info("translation_drift_no_gemini", message="Running with heuristic fallback")

    checked = 0
    flagged = 0

    async with session_factory() as session:
        verifier = PolyglotVerifier(session, gemini_client)

        # Find rules with non-empty statement_translations.
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
            canonical_locale = row[2] or "en"
            translations = row[3] or {}

            if not translations:
                continue

            report = await verifier.verify_equivalence(
                rule_id=rule_id,
                primary_statement=canonical,
                primary_language=canonical_locale,
                translations=translations,
            )

            for eq_result in report.results:
                checked += 1
                if eq_result.drift_detected:
                    flagged += 1
                    logger.warning(
                        "translation_drift_detected",
                        rule_id=rule_id,
                        canonical_locale=canonical_locale,
                        target_locale=eq_result.language,
                        score=round(eq_result.score, 2),
                    )

        await session.commit()

    logger.info(
        "translation_drift_check_complete",
        checked=checked,
        flagged=flagged,
    )

    return {"checked": checked, "flagged": flagged}

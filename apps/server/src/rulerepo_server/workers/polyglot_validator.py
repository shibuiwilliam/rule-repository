"""Polyglot rule equivalence validator worker.

Per CLAUDE.md §9: validates that rules sharing an equivalence_id
are semantically equivalent across languages.  Detects polyglot drift
and logs warnings when translations diverge.

Runs weekly (Sunday 6 AM) via arq cron.
"""

from __future__ import annotations

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def validate_polyglot_equivalence(ctx: dict) -> None:
    """Check that polyglot rule groups remain semantically equivalent.

    For each set of rules sharing an equivalence_id:
    1. Fetch all rules in the equivalence group.
    2. Use the PolyglotVerifier to compare translations pairwise.
    3. Log warnings when drift is detected.

    Args:
        ctx: arq worker context dict.
    """
    logger.info("polyglot_validator_started")

    try:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from rulerepo_server.adapters.postgres.models import RuleModel
        from rulerepo_server.core.config import get_settings
        from rulerepo_server.services.polyglot.verifier import PolyglotVerifier

        settings = get_settings()
        engine = create_async_engine(settings.database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        session: AsyncSession = factory()

        gemini_client = None
        try:
            from rulerepo_server.adapters.gemini.client import get_gemini_client

            gemini_client = get_gemini_client()
        except Exception:
            logger.info("polyglot_validator_no_gemini", message="Running with heuristic fallback")

        verifier = PolyglotVerifier(session, gemini_client)

        try:
            # Query active rules that have an equivalence_id set.
            result = await session.execute(
                select(RuleModel).where(
                    RuleModel.status.in_(["APPROVED", "EFFECTIVE"]),
                    RuleModel.equivalence_id.isnot(None),
                )
            )
            rules = list(result.scalars().all())

            # Group by equivalence_id.
            groups: dict[str, list] = {}
            for rule in rules:
                eq_id = rule.equivalence_id
                if eq_id:
                    groups.setdefault(eq_id, []).append(rule)

            drift_count = 0
            groups_checked = 0

            for eq_id, group_rules in groups.items():
                if len(group_rules) < 2:
                    continue

                groups_checked += 1

                # Pick the first rule as primary; others are translations.
                primary = group_rules[0]
                translations = {r.locale: r.statement for r in group_rules[1:]}

                report = await verifier.verify_equivalence(
                    rule_id=str(primary.id),
                    primary_statement=primary.statement,
                    primary_language=primary.locale or "en",
                    translations=translations,
                )

                if report.has_drift:
                    drift_count += 1

            logger.info(
                "polyglot_validator_complete",
                equivalence_groups=len(groups),
                groups_checked=groups_checked,
                drift_detected=drift_count,
            )
        finally:
            await session.close()

    except Exception:
        logger.exception("polyglot_validator_failed")
        raise

    logger.info("polyglot_validator_completed")

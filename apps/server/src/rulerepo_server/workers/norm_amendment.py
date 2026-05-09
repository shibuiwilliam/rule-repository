"""Norm amendment propagation worker — flags downstream rules for review.

Runs when a LAW or REGULATION rule's ``effective_period`` or ``statement``
is updated. Walks the DERIVES_FROM chain downstream and flags every
transitive descendant with ``pending_norm_change_review`` status.

See CLAUDE.md §14.4 and PROJECT.md §5.3.
"""

from __future__ import annotations

from sqlalchemy import text

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def propagate_norm_amendment(ctx: dict) -> dict:
    """Flag all downstream rules when an upstream norm is amended.

    This worker is triggered when a LAW or REGULATION rule's statement
    or effective_period changes. It walks the DERIVES_FROM chain
    downward and sets ``review_status = 'pending_norm_change_review'``
    on every transitive descendant.

    Args:
        ctx: arq worker context. Expected keys:
            - ``rule_id``: str — the amended rule's ID.
            - ``amendment_type``: str — 'statement' or 'effective_period'.

    Returns:
        Summary with count of flagged rules.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from rulerepo_server.adapters.postgres.session import get_engine

    rule_id = ctx.get("rule_id", "")
    amendment_type = ctx.get("amendment_type", "unknown")

    if not rule_id:
        logger.warning("propagate_norm_amendment called without rule_id")
        return {"flagged": 0, "error": "missing rule_id"}

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    flagged = 0

    async with session_factory() as session:
        # Verify the amended rule is LAW or REGULATION tier
        check = await session.execute(
            text("""
                SELECT id, norm_tier, statement
                FROM rules
                WHERE id = :rule_id
            """),
            {"rule_id": rule_id},
        )
        row = check.fetchone()
        if not row:
            logger.warning("Rule %s not found for amendment propagation", rule_id)
            return {"flagged": 0, "error": "rule_not_found"}

        norm_tier = row[1]
        if norm_tier not in ("LAW", "REGULATION"):
            logger.info(
                "Rule %s is tier %s, not LAW/REGULATION — skipping propagation",
                rule_id,
                norm_tier,
            )
            return {"flagged": 0, "skipped": True}

        # Walk DERIVES_FROM chain downstream using a recursive CTE.
        # This finds all transitive descendants of the amended rule.
        result = await session.execute(
            text("""
                WITH RECURSIVE downstream AS (
                    SELECT target_rule_id AS rule_id, 1 AS depth
                    FROM rule_relationships
                    WHERE source_rule_id = :root_id
                      AND relationship_type = 'DERIVES_FROM'
                    UNION ALL
                    SELECT rr.target_rule_id, d.depth + 1
                    FROM rule_relationships rr
                    JOIN downstream d ON rr.source_rule_id = d.rule_id
                    WHERE rr.relationship_type = 'DERIVES_FROM'
                      AND d.depth < 20
                )
                SELECT DISTINCT rule_id FROM downstream
            """),
            {"root_id": rule_id},
        )

        descendant_ids = [r[0] for r in result.fetchall()]

        if not descendant_ids:
            logger.info("Rule %s has no downstream derivatives to flag", rule_id)
            return {"flagged": 0}

        # Flag each downstream rule with pending_norm_change_review
        for desc_id in descendant_ids:
            await session.execute(
                text("""
                    UPDATE rules
                    SET review_status = 'pending_norm_change_review',
                        updated_at = NOW()
                    WHERE id = :rule_id
                      AND (review_status IS NULL
                           OR review_status != 'pending_norm_change_review')
                """),
                {"rule_id": desc_id},
            )
            flagged += 1

        await session.commit()

    logger.info(
        "Amendment propagation complete: rule=%s type=%s flagged=%d",
        rule_id,
        amendment_type,
        flagged,
    )

    return {
        "rule_id": rule_id,
        "amendment_type": amendment_type,
        "flagged": flagged,
        "descendant_ids": descendant_ids,
    }

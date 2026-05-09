"""Norm lineage amendment propagation worker.

When a LAW or REGULATION rule's statement or effective_period changes,
this worker flags all transitive downstream rules with
``pending_norm_change_review`` status.

See CLAUDE.md §14.4.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def propagate_norm_amendment(
    ctx: dict,
    rule_id: str,
    amendment_type: str = "statement_change",
) -> dict:
    """Flag downstream rules when a LAW/REGULATION is amended.

    Args:
        ctx: arq worker context (contains db session factory).
        rule_id: ID of the amended law/regulation rule.
        amendment_type: Type of amendment (statement_change, period_change).

    Returns:
        Summary of flagged rules.
    """
    from rulerepo_server.adapters.postgres.session import get_engine

    engine = get_engine()

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Verify the rule is a LAW or REGULATION
        result = await session.execute(
            text("SELECT norm_tier FROM rules WHERE id = :id"),
            {"id": rule_id},
        )
        row = result.first()
        if not row or row[0] not in ("LAW", "REGULATION"):
            logger.info(
                "propagation_skipped_not_law",
                rule_id=rule_id,
                norm_tier=row[0] if row else None,
            )
            return {"flagged": 0, "reason": "not a LAW or REGULATION"}

        # Walk downstream via DERIVES_FROM and flag each descendant
        flagged_count = await _flag_descendants(session, rule_id)

        await session.commit()

        logger.info(
            "norm_amendment_propagated",
            rule_id=rule_id,
            amendment_type=amendment_type,
            flagged_count=flagged_count,
        )

        return {
            "rule_id": rule_id,
            "amendment_type": amendment_type,
            "flagged": flagged_count,
        }


async def _flag_descendants(session: AsyncSession, rule_id: str) -> int:
    """Recursively flag all downstream rules as pending_norm_change_review."""
    flagged = 0
    queue = [rule_id]
    visited: set[str] = set()

    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)

        # Find children (rules that derive from this one)
        result = await session.execute(
            text("""
                SELECT source_id FROM rule_relationships
                WHERE target_id = :id AND relationship_type = 'DERIVES_FROM'
            """),
            {"id": current_id},
        )
        children = [str(row[0]) for row in result.fetchall()]

        for child_id in children:
            if child_id not in visited:
                # Flag the child rule
                await session.execute(
                    text("""
                        UPDATE rules
                        SET status = 'REVIEW',
                            updated_at = NOW()
                        WHERE id = :id AND status != 'RETIRED'
                    """),
                    {"id": child_id},
                )
                flagged += 1
                queue.append(child_id)

    return flagged

"""Rule effectiveness scoring — measures whether rules actually prevent bad code.

Three metrics:
- Precision: Of DENY verdicts, what % were not overridden by corrections (true positives)?
- Prevention rate: Did corrections decrease after this rule was activated?
- Agent adoption: What % of evaluations pass on the first attempt?

Combined into a composite effectiveness score (0-100).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

PRECISION_WEIGHT = 0.40
PREVENTION_WEIGHT = 0.35
ADOPTION_WEIGHT = 0.25


async def compute_effectiveness(
    session: AsyncSession,
    rule_id: str,
    period_days: int = 90,
) -> dict[str, Any]:
    """Compute effectiveness metrics for a single rule.

    Args:
        session: Async database session.
        rule_id: UUID of the rule.
        period_days: Lookback period for evaluation data.

    Returns:
        Dict with precision, prevention_rate, agent_adoption,
        effectiveness_score, and total_evaluations.
    """
    # 1. Precision: true_positive_count / (true_positive_count + false_positive_count)
    precision_query = text("""
        SELECT
            COALESCE(true_positive_count, 0) AS tp,
            COALESCE(false_positive_count, 0) AS fp
        FROM rules
        WHERE id = CAST(:rule_id AS uuid)
    """)
    precision_result = await session.execute(precision_query, {"rule_id": rule_id})
    precision_row = precision_result.mappings().first()

    tp = precision_row["tp"] if precision_row else 0
    fp = precision_row["fp"] if precision_row else 0
    total_judgments = tp + fp
    precision = round(tp / max(total_judgments, 1), 3) if total_judgments > 0 else 1.0

    # 2. Agent adoption: % of evaluations where verdict was ALLOW
    adoption_query = text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE verdict = 'ALLOW') AS allow_count
        FROM evaluations
        WHERE rule_id = CAST(:rule_id AS uuid)
          AND created_at > NOW() - MAKE_INTERVAL(days => :days)
    """)
    adoption_result = await session.execute(adoption_query, {"rule_id": rule_id, "days": period_days})
    adoption_row = adoption_result.mappings().first()

    total_evals = adoption_row["total"] if adoption_row else 0
    allow_count = adoption_row["allow_count"] if adoption_row else 0
    agent_adoption = round(allow_count / max(total_evals, 1), 3) if total_evals > 0 else 0.0

    # 3. Prevention rate: compare correction frequency before vs after rule creation
    prevention_query = text("""
        WITH rule_info AS (
            SELECT created_at AS rule_created, scope FROM rules
            WHERE id = CAST(:rule_id AS uuid)
        )
        SELECT
            (SELECT COUNT(*) FROM corrections
             WHERE created_at < (SELECT rule_created FROM rule_info)
               AND created_at > (SELECT rule_created FROM rule_info) - MAKE_INTERVAL(days => :days)
            ) AS before_count,
            (SELECT COUNT(*) FROM corrections
             WHERE created_at >= (SELECT rule_created FROM rule_info)
               AND created_at < (SELECT rule_created FROM rule_info) + MAKE_INTERVAL(days => :days)
            ) AS after_count
    """)
    prevention_result = await session.execute(prevention_query, {"rule_id": rule_id, "days": period_days})
    prevention_row = prevention_result.mappings().first()

    before = prevention_row["before_count"] if prevention_row else 0
    after = prevention_row["after_count"] if prevention_row else 0
    prevention_rate = round((before - after) / max(before, 1), 3) if before > 0 else 0.0
    prevention_rate = max(0.0, prevention_rate)  # clamp to 0

    # Composite score (0-100)
    effectiveness_score = round(
        (precision * PRECISION_WEIGHT + prevention_rate * PREVENTION_WEIGHT + agent_adoption * ADOPTION_WEIGHT) * 100,
        1,
    )

    return {
        "precision": precision,
        "prevention_rate": prevention_rate,
        "agent_adoption": agent_adoption,
        "effectiveness_score": effectiveness_score,
        "total_evaluations": total_evals,
        "true_positives": tp,
        "false_positives": fp,
    }

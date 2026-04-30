"""Agent analytics — per-agent performance tracking and compliance metrics.

Per PROJECT_IMPROVEMENT.md §2: tracks which agents produce the most compliant
code, which rules each agent breaks, and compliance trends over time.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def get_agent_list(session: AsyncSession, period_days: int = 30) -> list[dict[str, Any]]:
    """List all agents with evaluation counts and compliance rates.

    Args:
        session: Async database session.
        period_days: Number of days to look back.

    Returns:
        List of agent summary dicts sorted by total evaluations descending.
    """
    query = text("""
        SELECT
            agent_id,
            COUNT(*) AS total_evaluations,
            COUNT(*) FILTER (WHERE verdict = 'ALLOW') AS allow_count,
            COUNT(*) FILTER (WHERE verdict = 'DENY') AS deny_count
        FROM evaluations
        WHERE agent_id IS NOT NULL
          AND created_at > NOW() - MAKE_INTERVAL(days => :days)
        GROUP BY agent_id
        ORDER BY total_evaluations DESC
    """)
    result = await session.execute(query, {"days": period_days})
    rows = result.mappings().all()

    return [
        {
            "agent_id": row["agent_id"],
            "total_evaluations": row["total_evaluations"] or 0,
            "compliance_rate": round((row["allow_count"] or 0) / max(row["total_evaluations"] or 1, 1), 3),
            "deny_count": row["deny_count"] or 0,
        }
        for row in rows
    ]


async def get_agent_detail(session: AsyncSession, agent_id: str, period_days: int = 30) -> dict[str, Any]:
    """Get detailed analytics for a single agent.

    Args:
        session: Async database session.
        agent_id: The agent identifier.
        period_days: Number of days to look back.

    Returns:
        Dict with compliance trend and top violated rules.
    """
    # Compliance trend (daily)
    trend_query = text("""
        SELECT
            DATE(created_at) AS eval_date,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE verdict = 'ALLOW') AS allow_count
        FROM evaluations
        WHERE agent_id = :agent_id
          AND created_at > NOW() - MAKE_INTERVAL(days => :days)
        GROUP BY DATE(created_at)
        ORDER BY eval_date
    """)
    trend_result = await session.execute(trend_query, {"agent_id": agent_id, "days": period_days})
    trend = [
        {
            "date": str(row["eval_date"]),
            "total": row["total"] or 0,
            "allow_count": row["allow_count"] or 0,
            "compliance_rate": round((row["allow_count"] or 0) / max(row["total"] or 1, 1), 3),
        }
        for row in trend_result.mappings().all()
    ]

    # Top violated rules
    violations_query = text("""
        SELECT
            e.rule_id::text AS rule_id,
            COUNT(*) AS violation_count,
            r.statement AS rule_statement
        FROM evaluations e
        LEFT JOIN rules r ON r.id = e.rule_id
        WHERE e.agent_id = :agent_id
          AND e.verdict = 'DENY'
          AND e.created_at > NOW() - MAKE_INTERVAL(days => :days)
        GROUP BY e.rule_id, r.statement
        ORDER BY violation_count DESC
        LIMIT 10
    """)
    violations_result = await session.execute(violations_query, {"agent_id": agent_id, "days": period_days})
    top_violations = [dict(row) for row in violations_result.mappings().all()]

    # Overall stats
    stats_query = text("""
        SELECT
            COUNT(*) AS total_evaluations,
            COUNT(*) FILTER (WHERE verdict = 'ALLOW') AS allow_count
        FROM evaluations
        WHERE agent_id = :agent_id
          AND created_at > NOW() - MAKE_INTERVAL(days => :days)
    """)
    stats_result = await session.execute(stats_query, {"agent_id": agent_id, "days": period_days})
    stats_row = stats_result.mappings().first()
    total = (stats_row["total_evaluations"] or 0) if stats_row else 0
    allow = (stats_row["allow_count"] or 0) if stats_row else 0

    return {
        "agent_id": agent_id,
        "total_evaluations": total,
        "compliance_rate": round(allow / max(total, 1), 3),
        "compliance_trend": trend,
        "top_violations": top_violations,
    }


async def get_agent_top_violations(session: AsyncSession, agent_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get rule IDs this agent violates most frequently.

    Used by rule_selector.py for targeted rule delivery — boosting rules
    that this specific agent historically breaks.

    Args:
        session: Async database session.
        agent_id: The agent identifier.
        limit: Max rules to return.

    Returns:
        List of {rule_id, violation_count} dicts.
    """
    query = text("""
        SELECT
            rule_id::text AS rule_id,
            COUNT(*) AS violation_count
        FROM evaluations
        WHERE agent_id = :agent_id
          AND verdict = 'DENY'
          AND created_at > NOW() - MAKE_INTERVAL(days => 90)
        GROUP BY rule_id
        ORDER BY violation_count DESC
        LIMIT :limit
    """)
    result = await session.execute(query, {"agent_id": agent_id, "limit": limit})
    return [dict(row) for row in result.mappings().all()]

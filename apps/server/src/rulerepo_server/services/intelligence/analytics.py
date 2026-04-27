"""Evaluation analytics — aggregate metrics from the audit log.

Per CLAUDE_ENHANCE.md §4.4: analytics queries run against the audit log.
Do not create a separate analytics table.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def get_corpus_analytics(session: AsyncSession, period_days: int = 30) -> dict[str, Any]:
    """Get corpus-wide evaluation analytics.

    Args:
        session: Async database session.
        period_days: Number of days to aggregate over.

    Returns:
        Dictionary with total evaluations, verdict distribution, etc.
    """
    query = text("""
        SELECT
            COUNT(*) AS total_evaluations,
            COUNT(*) FILTER (WHERE details->>'verdict' = 'ALLOW') AS allow_count,
            COUNT(*) FILTER (WHERE details->>'verdict' = 'DENY') AS deny_count,
            COUNT(*) FILTER (WHERE details->>'verdict' = 'NEEDS_CONFIRMATION') AS confirm_count,
            AVG((details->>'latency_ms')::float) AS avg_latency_ms
        FROM audit_log
        WHERE action IN ('evaluate', 'llm_extraction_call')
          AND timestamp > NOW() - MAKE_INTERVAL(days => :days)
    """)

    result = await session.execute(query, {"days": period_days})
    row = result.mappings().first()

    if not row:
        return {
            "total_evaluations": 0,
            "verdict_distribution": {"ALLOW": 0, "DENY": 0, "NEEDS_CONFIRMATION": 0},
            "avg_latency_ms": 0.0,
        }

    return {
        "total_evaluations": row["total_evaluations"] or 0,
        "verdict_distribution": {
            "ALLOW": row["allow_count"] or 0,
            "DENY": row["deny_count"] or 0,
            "NEEDS_CONFIRMATION": row["confirm_count"] or 0,
        },
        "avg_latency_ms": round(row["avg_latency_ms"] or 0, 1),
    }


async def get_rule_analytics(
    session: AsyncSession, rule_id: str, period_days: int = 30
) -> dict[str, Any]:
    """Get per-rule evaluation analytics.

    Args:
        session: Async database session.
        rule_id: UUID of the rule.
        period_days: Number of days to aggregate over.

    Returns:
        Dictionary with per-rule evaluation metrics.
    """
    query = text("""
        SELECT
            COUNT(*) AS total_evaluations,
            COUNT(*) FILTER (WHERE details->>'verdict' = 'ALLOW') AS allow_count,
            COUNT(*) FILTER (WHERE details->>'verdict' = 'DENY') AS deny_count,
            COUNT(*) FILTER (WHERE details->>'verdict' = 'NEEDS_CONFIRMATION') AS confirm_count,
            AVG((details->>'latency_ms')::float) AS avg_latency_ms
        FROM audit_log
        WHERE resource_id = :rule_id
          AND action IN ('evaluate', 'rule_created', 'rule_updated')
          AND timestamp > NOW() - MAKE_INTERVAL(days => :days)
    """)

    result = await session.execute(query, {"rule_id": rule_id, "days": period_days})
    row = result.mappings().first()

    total = (row["total_evaluations"] or 0) if row else 0
    allow = (row["allow_count"] or 0) if row else 0
    deny = (row["deny_count"] or 0) if row else 0
    confirm = (row["confirm_count"] or 0) if row else 0

    return {
        "rule_id": rule_id,
        "period": f"{period_days}d",
        "total_evaluations": total,
        "evaluations_per_day": round(total / max(period_days, 1), 2),
        "allow_rate": round(allow / max(total, 1), 3),
        "deny_rate": round(deny / max(total, 1), 3),
        "needs_confirmation_rate": round(confirm / max(total, 1), 3),
        "avg_latency_ms": round((row["avg_latency_ms"] or 0) if row else 0, 1),
    }


async def get_cache_stats(session: AsyncSession, period_days: int = 30) -> dict[str, Any]:
    """Get LLM cache hit/miss statistics from the audit log.

    Args:
        session: Async database session.
        period_days: Number of days to aggregate.

    Returns:
        Dictionary with hits, misses, and hit_rate.
    """
    query = text("""
        SELECT
            COUNT(*) FILTER (
                WHERE details->>'cache_hit' = 'true'
            ) AS hits,
            COUNT(*) FILTER (
                WHERE details->>'cache_hit' IS NULL
                   OR details->>'cache_hit' = 'false'
            ) AS misses
        FROM audit_log
        WHERE action = 'evaluate'
          AND timestamp > NOW() - MAKE_INTERVAL(days => :days)
    """)
    result = await session.execute(query, {"days": period_days})
    row = result.mappings().first()

    hits = (row["hits"] or 0) if row else 0
    misses = (row["misses"] or 0) if row else 0
    total = hits + misses

    return {
        "cache_hits": hits,
        "cache_misses": misses,
        "hit_rate": round(hits / max(total, 1), 3),
        "period_days": period_days,
    }


async def get_top_violated_rules(
    session: AsyncSession, period_days: int = 30, limit: int = 10
) -> list[dict[str, Any]]:
    """Get the most frequently violated rules from the audit log.

    Args:
        session: Async database session.
        period_days: Number of days to look back.
        limit: Maximum number of rules to return.

    Returns:
        List of {rule_id, violation_count} dicts, ordered by count.
    """
    query = text("""
        SELECT
            resource_id AS rule_id,
            COUNT(*) AS violation_count
        FROM audit_log
        WHERE action = 'evaluate'
          AND details->>'overall_verdict' = 'DENY'
          AND timestamp > NOW() - MAKE_INTERVAL(days => :days)
        GROUP BY resource_id
        ORDER BY violation_count DESC
        LIMIT :limit
    """)
    result = await session.execute(query, {"days": period_days, "limit": limit})
    return [dict(row) for row in result.mappings().all()]

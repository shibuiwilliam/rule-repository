"""arq worker settings -- background job infrastructure."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def _get_worker_session() -> AsyncSession:
    """Create a standalone async session for worker processes.

    Workers run in a separate process and cannot share the FastAPI
    request-scoped session, so they create their own engine.

    Returns:
        A new AsyncSession instance. Caller must close it.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory()


def _model_to_dict(model: object) -> dict:
    """Convert a RuleModel ORM instance to a plain dict for scoring."""
    return {
        "id": str(model.id),  # type: ignore[attr-defined]
        "statement": model.statement,  # type: ignore[attr-defined]
        "modality": model.modality,  # type: ignore[attr-defined]
        "severity": model.severity,  # type: ignore[attr-defined]
        "status": model.status,  # type: ignore[attr-defined]
        "scope": model.scope,  # type: ignore[attr-defined]
        "tags": model.tags,  # type: ignore[attr-defined]
        "rationale": model.rationale,  # type: ignore[attr-defined]
        "source_refs": model.source_refs,  # type: ignore[attr-defined]
        "governance": model.governance,  # type: ignore[attr-defined]
        "clarity_score": getattr(model, "clarity_score", None),
        "created_at": model.created_at,  # type: ignore[attr-defined]
        "updated_at": model.updated_at,  # type: ignore[attr-defined]
    }


async def compute_health_scores(ctx: dict) -> None:
    """Scheduled: recompute health scores for all active rules.

    For each rule with status APPROVED or EFFECTIVE:
    1. Compute the health score using the deterministic scorer.
    2. Fetch per-rule analytics from the audit log.
    3. Upsert a RuleHealthScoreModel row.
    4. Create alerts for unhealthy or dormant rules.
    """
    from rulerepo_server.adapters.postgres.models import (
        AlertModel,
        RuleHealthScoreModel,
        RuleModel,
    )
    from rulerepo_server.services.intelligence.analytics import get_rule_analytics
    from rulerepo_server.services.intelligence.health_scorer import compute_health_score

    logger.info("compute_health_scores_started")
    session = await _get_worker_session()
    try:
        result = await session.execute(
            select(RuleModel).where(RuleModel.status.in_(["APPROVED", "EFFECTIVE"]))
        )
        rules = list(result.scalars().all())
        logger.info("compute_health_scores_rules_found", count=len(rules))

        for rule in rules:
            rule_dict = _model_to_dict(rule)
            rule_analytics = await get_rule_analytics(session, str(rule.id), period_days=90)
            health = compute_health_score(
                rule_dict,
                evaluation_count_90d=rule_analytics.get("total_evaluations", 0),
            )

            # Upsert health score: delete old row then insert new
            existing = await session.execute(
                select(RuleHealthScoreModel).where(RuleHealthScoreModel.rule_id == rule.id)
            )
            old = existing.scalar_one_or_none()
            if old is not None:
                await session.delete(old)

            score_row = RuleHealthScoreModel(
                id=str(uuid4()),
                rule_id=rule.id,
                overall_score=health["overall_score"],
                completeness=health["completeness"],
                clarity=health["clarity"],
                test_coverage=health["test_coverage"],
                freshness=health["freshness"],
                activity=health["activity"],
                owner_engagement=health["owner_engagement"],
                issues=health.get("issues", []),
                computed_at=datetime.now(tz=UTC),
            )
            session.add(score_row)

            # Alert: health decline
            if health["overall_score"] < 40:
                alert = AlertModel(
                    id=str(uuid4()),
                    alert_type="health_decline",
                    severity="warning",
                    title=f"Rule health critically low ({health['overall_score']})",
                    description=(
                        f"Rule {rule.id} has an overall health score of "
                        f"{health['overall_score']}, which is below the 40-point threshold."
                    ),
                    rule_id=rule.id,
                    status="active",
                )
                session.add(alert)

            # Alert: dormant rule
            if health["activity"] == 0:
                alert = AlertModel(
                    id=str(uuid4()),
                    alert_type="dormant_rule",
                    severity="info",
                    title="Rule has had no evaluations in 90 days",
                    description=(
                        f"Rule {rule.id} has not been evaluated in the last 90 days. "
                        "Consider reviewing whether it is still needed."
                    ),
                    rule_id=rule.id,
                    status="active",
                )
                session.add(alert)

        await session.commit()
        logger.info("compute_health_scores_completed", rules_scored=len(rules))
    except Exception:
        await session.rollback()
        logger.exception("compute_health_scores_failed")
        raise
    finally:
        await session.close()


async def generate_recommendations_task(ctx: dict) -> None:
    """Scheduled: generate improvement recommendations for all active rules.

    Analyzes rule health scores and correction patterns. If a rule has
    a deny rate > 50%, raises a high_deny_rate alert.
    """
    from rulerepo_server.adapters.postgres.models import (
        AlertModel,
        RuleModel,
        RuleRecommendationModel,
    )
    from rulerepo_server.services.intelligence.analytics import get_rule_analytics
    from rulerepo_server.services.intelligence.health_scorer import compute_health_score
    from rulerepo_server.services.intelligence.recommender import generate_recommendations

    logger.info("generate_recommendations_started")
    session = await _get_worker_session()
    try:
        result = await session.execute(
            select(RuleModel).where(RuleModel.status.in_(["APPROVED", "EFFECTIVE"]))
        )
        rules = list(result.scalars().all())
        total_recs = 0

        for rule in rules:
            rule_dict = _model_to_dict(rule)
            rule_analytics = await get_rule_analytics(session, str(rule.id), period_days=90)
            health = compute_health_score(
                rule_dict,
                evaluation_count_90d=rule_analytics.get("total_evaluations", 0),
            )
            recs = generate_recommendations(rule_dict, health, rule_analytics)

            for rec in recs:
                rec_row = RuleRecommendationModel(
                    id=rec["id"],
                    rule_id=rule.id,
                    type=rec["type"],
                    title=rec["title"],
                    description=rec["description"],
                    priority=rec["priority"],
                    status=rec.get("status", "open"),
                )
                session.add(rec_row)
                total_recs += 1

            # Alert: high deny rate
            deny_rate = rule_analytics.get("deny_rate", 0)
            if deny_rate > 0.5 and rule_analytics.get("total_evaluations", 0) >= 10:
                alert = AlertModel(
                    id=str(uuid4()),
                    alert_type="high_deny_rate",
                    severity="warning",
                    title=f"Rule has a {deny_rate:.0%} deny rate",
                    description=(
                        f"Rule {rule.id} has a deny rate of {deny_rate:.0%} over the last "
                        "90 days. This may indicate systematic non-compliance or an "
                        "overly strict rule."
                    ),
                    rule_id=rule.id,
                    status="active",
                )
                session.add(alert)

        await session.commit()
        logger.info(
            "generate_recommendations_completed",
            rules_analyzed=len(rules),
            recommendations_created=total_recs,
        )
    except Exception:
        await session.rollback()
        logger.exception("generate_recommendations_failed")
        raise
    finally:
        await session.close()


async def compute_correction_stats(ctx: dict) -> None:
    """Scheduled: aggregate correction statistics from the corrections table.

    Counts corrections by analysis_type and status, then logs the
    aggregated stats. Full persistence can be added later.
    """
    from rulerepo_server.adapters.postgres.models import CorrectionModel

    logger.info("compute_correction_stats_started")
    session = await _get_worker_session()
    try:
        # Count by analysis_type
        type_result = await session.execute(
            select(
                CorrectionModel.analysis_type,
                func.count().label("count"),
            ).group_by(CorrectionModel.analysis_type)
        )
        by_type = {row.analysis_type or "unknown": row.count for row in type_result.all()}

        # Count by status
        status_result = await session.execute(
            select(
                CorrectionModel.status,
                func.count().label("count"),
            ).group_by(CorrectionModel.status)
        )
        by_status = {row.status: row.count for row in status_result.all()}

        logger.info(
            "compute_correction_stats_completed",
            by_analysis_type=by_type,
            by_status=by_status,
            total=sum(by_status.values()),
        )
    except Exception:
        await session.rollback()
        logger.exception("compute_correction_stats_failed")
        raise
    finally:
        await session.close()


class WorkerSettings:
    """arq worker configuration."""

    functions: list = []  # async tasks triggered on demand
    cron_jobs = [
        cron(compute_health_scores, hour=2, minute=0),
        cron(generate_recommendations_task, hour=3, minute=0),
        cron(compute_correction_stats, minute=0),
    ]

    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

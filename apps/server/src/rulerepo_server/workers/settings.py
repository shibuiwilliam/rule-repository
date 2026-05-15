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
from rulerepo_server.workers.norm_lineage_propagation import propagate_norm_amendment
from rulerepo_server.workers.polyglot_validator import validate_polyglot_equivalence
from rulerepo_server.workers.translation_drift import verify_translation_drift
from rulerepo_server.workers.verdict_drift import detect_verdict_drift

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
        result = await session.execute(select(RuleModel).where(RuleModel.status.in_(["APPROVED", "EFFECTIVE"])))
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
                    project_id=rule.project_id,
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
                    project_id=rule.project_id,
                )
                session.add(alert)

            # Alert: low effectiveness score
            total_judgments = (rule.true_positive_count or 0) + (rule.false_positive_count or 0)
            if total_judgments >= 10:
                try:
                    from rulerepo_server.services.intelligence.effectiveness import (
                        compute_effectiveness,
                    )

                    eff = await compute_effectiveness(session, str(rule.id), period_days=30)
                    if eff["effectiveness_score"] < 30:
                        alert = AlertModel(
                            id=str(uuid4()),
                            alert_type="effectiveness_decline",
                            severity="warning",
                            title=f"Low effectiveness: {rule.statement[:60]}...",
                            description=(
                                f"Effectiveness score {eff['effectiveness_score']}. "
                                f"Precision: {eff['precision']}, "
                                f"FP: {eff['false_positives']}, TP: {eff['true_positives']}. "
                                "Consider rewriting or narrowing scope."
                            ),
                            rule_id=rule.id,
                            status="active",
                            project_id=rule.project_id,
                        )
                        session.add(alert)
                except Exception:
                    pass

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
        result = await session.execute(select(RuleModel).where(RuleModel.status.in_(["APPROVED", "EFFECTIVE"])))
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
                    project_id=rule.project_id,
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


async def auto_promote_rules(ctx: dict) -> None:
    """Promote or demote rules based on false-positive rate.

    - experimental → stable: 30+ days, 20+ evals, FP rate < 5%
    - stable → proven: 60+ days, FP rate < 1%
    - stable/proven → experimental: FP rate > 10% (demotion)
    """
    from rulerepo_server.adapters.postgres.models import RuleModel

    session = await _get_worker_session()
    try:
        result = await session.execute(select(RuleModel).where(RuleModel.status.in_(["APPROVED", "EFFECTIVE"])))
        rules = list(result.scalars().all())

        promoted = 0
        demoted = 0
        now = datetime.now(tz=UTC)

        for rule in rules:
            total = rule.true_positive_count + rule.false_positive_count
            if total < 20:
                continue
            fp_rate = rule.false_positive_count / max(total, 1)
            days_old = (now - rule.created_at).days if rule.created_at else 0

            old_level = rule.maturity_level

            if rule.maturity_level == "experimental" and days_old >= 30 and fp_rate < 0.05:
                rule.maturity_level = "stable"
                promoted += 1
            elif rule.maturity_level == "stable" and days_old >= 60 and fp_rate < 0.01:
                rule.maturity_level = "proven"
                promoted += 1
            elif rule.maturity_level in ("stable", "proven") and fp_rate > 0.10:
                rule.maturity_level = "experimental"
                demoted += 1

            if rule.maturity_level != old_level:
                logger.info(
                    "maturity_changed",
                    rule_id=str(rule.id),
                    old_level=old_level,
                    new_level=rule.maturity_level,
                    fp_rate=round(fp_rate, 3),
                    days_old=days_old,
                )

        await session.commit()
        logger.info(
            "auto_promote_rules_complete",
            total_evaluated=len(rules),
            promoted=promoted,
            demoted=demoted,
        )
    except Exception:
        await session.rollback()
        logger.exception("auto_promote_rules_failed")
        raise
    finally:
        await session.close()


async def cluster_corrections(ctx: dict) -> None:
    """Cluster recent corrections and auto-draft rule proposals.

    Per PROJECT_ENHANCE.md §3: the correction-to-rule flywheel.
    """
    session = await _get_worker_session()
    try:
        from rulerepo_server.services.feedback.auto_drafter import cluster_and_draft

        gemini = None
        try:
            from rulerepo_server.adapters.gemini.client import get_gemini_client

            gemini = get_gemini_client()
        except Exception:
            logger.warning("cluster_corrections_no_gemini")

        proposals = await cluster_and_draft(session, gemini)
        await session.commit()
        logger.info("cluster_corrections_complete", proposals_created=proposals)
    except Exception:
        await session.rollback()
        logger.exception("cluster_corrections_failed")
        raise
    finally:
        await session.close()


async def verify_translation_equivalence(ctx: dict) -> None:
    """Daily verification of translation pair equivalence scores.

    Loads all translation pairs from Postgres, re-runs equivalence
    checks via ``verify_all_translations``, and logs results.
    Gated behind ``polyglot_verification_enabled``.
    """
    from rulerepo_server.core.feature_flags import get_feature_flags

    if not get_feature_flags().polyglot_verification_enabled:
        logger.info("verify_translation_equivalence_skipped", reason="polyglot_verification_disabled")
        return

    session = await _get_worker_session()
    try:
        from sqlalchemy import select

        from rulerepo_server.adapters.postgres.models import RuleTranslationModel
        from rulerepo_server.workers.verify_translations import verify_all_translations

        result = await session.execute(select(RuleTranslationModel))
        rows = list(result.scalars().all())

        # Load source and target rule statements for each translation pair
        from rulerepo_server.adapters.postgres.models import RuleModel

        rule_ids = {str(row.source_rule_id) for row in rows} | {str(row.target_rule_id) for row in rows}
        rule_result = await session.execute(select(RuleModel).where(RuleModel.id.in_(rule_ids)))
        rule_map = {str(r.id): r for r in rule_result.scalars().all()}

        pairs = []
        for row in rows:
            source = rule_map.get(str(row.source_rule_id))
            target = rule_map.get(str(row.target_rule_id))
            if not source or not target:
                continue
            pairs.append(
                {
                    "rule_id": str(row.source_rule_id),
                    "sibling_rule_id": str(row.target_rule_id),
                    "rule_statement": source.statement or "",
                    "rule_language": getattr(source, "locale", "en") or "en",
                    "sibling_statement": target.statement or "",
                    "sibling_language": row.target_language or "ja",
                }
            )

        results = await verify_all_translations(translation_pairs=pairs)

        below = sum(1 for r in results if r.below_threshold)
        logger.info(
            "verify_translation_equivalence_completed",
            total_pairs=len(results),
            below_threshold=below,
        )
    except Exception:
        await session.rollback()
        logger.exception("verify_translation_equivalence_failed")
        raise
    finally:
        await session.close()


async def send_weekly_digest(ctx: dict) -> None:
    """Generate and optionally deliver the weekly governance digest.

    Runs every Monday at 9am. Generates the digest and sends it to the
    configured DIGEST_WEBHOOK_URL if set. Gated behind
    ADVANCED_OBSERVABILITY_ENABLED.
    """
    from rulerepo_server.core.feature_flags import get_feature_flags

    if not get_feature_flags().advanced_observability_enabled:
        logger.info("send_weekly_digest_skipped", reason="advanced_observability_disabled")
        return

    session = await _get_worker_session()
    try:
        from rulerepo_server.services.intelligence.digest import generate_weekly_digest

        digest = await generate_weekly_digest(session)
        logger.info(
            "weekly_digest_generated",
            compliance_rate=digest["compliance"]["current_rate"],
            rules_total=digest["rules"]["total"],
        )

        # Send to webhook if configured
        webhook_url = get_settings().digest_webhook_url
        if webhook_url:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    webhook_url,
                    json=digest,
                    timeout=30,
                )
                logger.info("weekly_digest_sent", status=resp.status_code)
    except Exception:
        await session.rollback()
        logger.exception("weekly_digest_failed")
        raise
    finally:
        await session.close()


class WorkerSettings:
    """arq worker configuration."""

    functions = [propagate_norm_amendment]  # on-demand tasks
    cron_jobs = [
        cron(compute_health_scores, hour=2, minute=0),
        cron(generate_recommendations_task, hour=3, minute=0),
        cron(verify_translation_drift, hour=3, minute=30),  # daily
        cron(auto_promote_rules, hour=4, minute=0),
        cron(cluster_corrections, hour=5, minute=0),
        cron(compute_correction_stats, minute=0),
        cron(send_weekly_digest, weekday=0, hour=9, minute=0),  # Monday 9am
        cron(detect_verdict_drift, hour=4, minute=30),  # daily (Phase 5i)
        cron(validate_polyglot_equivalence, weekday=6, hour=6, minute=0),  # Sunday 6am (Phase 7i)
        cron(verify_translation_equivalence, hour=5, minute=30),  # daily (CLAUDE.md §14.8)
    ]

    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)

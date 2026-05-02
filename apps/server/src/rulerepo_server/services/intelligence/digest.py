"""Weekly governance digest — automated report on rule health and compliance trends.

Generates a structured digest suitable for rendering as a dashboard page,
Slack message, or email. Called by the weekly cron job and available via API.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import (
    AlertModel,
    CorrectionModel,
    DraftRuleProposalModel,
    RuleModel,
)
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.intelligence.analytics import (
    get_compliance_trend,
    get_corpus_analytics,
    get_top_violated_rules,
)

logger = get_logger(__name__)


async def generate_weekly_digest(
    session: AsyncSession,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Generate the weekly governance digest.

    Args:
        session: Async database session.
        project_id: Optional project filter.

    Returns:
        Structured dict with all digest sections.
    """
    # 1. Compliance trend: this week vs last week
    this_week = await get_corpus_analytics(session, period_days=7)
    last_week = await get_corpus_analytics(session, period_days=14)
    daily_trend = await get_compliance_trend(session, days=7)

    tw_total = this_week.get("total_evaluations", 0)
    tw_allow = this_week.get("verdict_distribution", {}).get("ALLOW", 0)
    tw_rate = round(tw_allow / max(tw_total, 1), 3) if tw_total > 0 else 0.0

    lw_total = last_week.get("total_evaluations", 0) - tw_total
    lw_allow = last_week.get("verdict_distribution", {}).get("ALLOW", 0) - tw_allow
    lw_rate = round(lw_allow / max(lw_total, 1), 3) if lw_total > 0 else 0.0

    compliance_change = round((tw_rate - lw_rate) * 100, 1)

    # 2. Rule changes this week
    new_rules_result = await session.execute(
        select(func.count(RuleModel.id)).where(RuleModel.created_at > text("NOW() - INTERVAL '7 days'"))
    )
    new_rules = new_rules_result.scalar_one()

    total_rules_result = await session.execute(select(func.count(RuleModel.id)))
    total_rules = total_rules_result.scalar_one()

    # 3. Top violated rules
    top_violated = await get_top_violated_rules(session, period_days=7, limit=5)

    # 4. Rules needing attention: high FP rate or dormant
    attention_rules: list[dict[str, Any]] = []

    # High false positive rate
    fp_result = await session.execute(
        select(RuleModel)
        .where(
            RuleModel.false_positive_count > 5,
        )
        .limit(5)
    )
    for rule in fp_result.scalars().all():
        total = rule.false_positive_count + rule.true_positive_count
        if total > 0:
            fp_rate = round(rule.false_positive_count / total, 3)
            if fp_rate > 0.3:
                attention_rules.append(
                    {
                        "rule_id": str(rule.id),
                        "statement": rule.statement[:100],
                        "issue": f"{round(fp_rate * 100)}% false positive rate",
                        "severity": "warning",
                    }
                )

    # 5. Corrections this week
    corrections_result = await session.execute(
        select(func.count(CorrectionModel.id)).where(CorrectionModel.created_at > text("NOW() - INTERVAL '7 days'"))
    )
    corrections_count = corrections_result.scalar_one()

    # 6. Pending proposals
    try:
        proposals_result = await session.execute(
            select(func.count(DraftRuleProposalModel.id)).where(DraftRuleProposalModel.status == "pending")
        )
        pending_proposals = proposals_result.scalar_one()
    except Exception:
        pending_proposals = 0

    # 7. Active alerts
    alerts_result = await session.execute(select(func.count(AlertModel.id)).where(AlertModel.status == "active"))
    active_alerts = alerts_result.scalar_one()

    # 8. Maturity distribution
    maturity_result = await session.execute(
        select(
            RuleModel.maturity_level,
            func.count(RuleModel.id),
        ).group_by(RuleModel.maturity_level)
    )
    maturity_dist = {str(row[0]): row[1] for row in maturity_result.all()}

    # 9. Most effective and declining rules
    most_effective: list[dict[str, Any]] = []
    declining_rules: list[dict[str, Any]] = []
    try:
        from rulerepo_server.services.intelligence.effectiveness import (
            compute_effectiveness,
        )

        # Sample top rules by evaluation count for effectiveness scoring
        eff_candidates = await session.execute(
            select(RuleModel).where(RuleModel.status.in_(["APPROVED", "EFFECTIVE"])).limit(20)
        )
        for rule in eff_candidates.scalars().all():
            try:
                eff = await compute_effectiveness(session, str(rule.id), period_days=7)
                if eff["total_evaluations"] >= 3:
                    entry = {
                        "rule_id": str(rule.id),
                        "statement": rule.statement[:100],
                        "effectiveness_score": eff["effectiveness_score"],
                        "precision": eff["precision"],
                        "agent_adoption": eff["agent_adoption"],
                    }
                    most_effective.append(entry)
                    if eff["effectiveness_score"] < 30:
                        declining_rules.append(entry)
            except Exception as exc:
                logger.debug("effectiveness_compute_skipped", rule_id=str(rule.id), error=str(exc))
                continue

        most_effective.sort(key=lambda x: x["effectiveness_score"], reverse=True)
        most_effective = most_effective[:5]
    except Exception:
        pass

    digest = {
        "period": "7d",
        "compliance": {
            "current_rate": tw_rate,
            "previous_rate": lw_rate,
            "change_pp": compliance_change,
            "trend": "improving" if compliance_change > 0 else "declining" if compliance_change < 0 else "stable",
            "daily_trend": daily_trend,
            "total_evaluations": tw_total,
        },
        "rules": {
            "total": total_rules,
            "new_this_week": new_rules,
            "maturity_distribution": maturity_dist,
        },
        "top_violated_rules": top_violated,
        "most_effective_rules": most_effective,
        "declining_rules": declining_rules,
        "attention_needed": attention_rules,
        "corrections": {
            "this_week": corrections_count,
            "pending_proposals": pending_proposals,
        },
        "pending_actions": {
            "proposals_pending": pending_proposals,
            "active_alerts": active_alerts,
        },
    }

    logger.info(
        "weekly_digest_generated",
        compliance_rate=tw_rate,
        rules_total=total_rules,
        corrections=corrections_count,
    )

    return digest

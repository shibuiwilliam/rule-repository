"""IntelligenceService — orchestrates health scoring, analytics, and recommendations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import AlertModel, RuleModel
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.intelligence.analytics import (
    get_cache_stats,
    get_compliance_trend,
    get_corpus_analytics,
    get_rule_analytics,
    get_top_violated_rules,
)
from rulerepo_server.services.intelligence.health_scorer import compute_health_score
from rulerepo_server.services.intelligence.recommender import generate_recommendations

logger = get_logger(__name__)


class IntelligenceService:
    """Orchestrates all intelligence features: health, analytics, recommendations.

    Injected via FastAPI dependency. Uses the same session as the request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_dashboard(self, project_id: str | None = None) -> dict[str, Any]:
        """Get corpus-wide intelligence dashboard summary.

        Returns:
            DashboardSummary-compatible dict.
        """
        # Total rules
        count_query = select(func.count()).select_from(RuleModel)
        if project_id:
            count_query = count_query.where(RuleModel.project_id == project_id)
        result = await self._session.execute(count_query)
        total_rules = result.scalar_one()

        # Analytics from audit log
        analytics = await get_corpus_analytics(self._session, period_days=30)

        # Compute average health (sample up to 100 rules for performance)
        rules_query = select(RuleModel).limit(100)
        if project_id:
            rules_query = rules_query.where(RuleModel.project_id == project_id)
        rules_result = await self._session.execute(rules_query)
        rules = list(rules_result.scalars().all())

        health_scores = []
        for rule in rules:
            rule_dict = self._model_to_dict(rule)
            health = compute_health_score(rule_dict)
            health_scores.append(health["overall_score"])

        avg_health = round(sum(health_scores) / max(len(health_scores), 1), 1)

        # Health distribution
        distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        for score in health_scores:
            if score >= 80:
                distribution["excellent"] += 1
            elif score >= 60:
                distribution["good"] += 1
            elif score >= 40:
                distribution["fair"] += 1
            else:
                distribution["poor"] += 1

        # Compute recommendation count from current health scores
        open_recommendations = 0
        for rule in rules:
            rule_dict = self._model_to_dict(rule)
            rule_analytics = await get_rule_analytics(self._session, str(rule.id), period_days=90)
            health = compute_health_score(
                rule_dict,
                evaluation_count_90d=rule_analytics.get("total_evaluations", 0),
            )
            recs = generate_recommendations(rule_dict, health, rule_analytics)
            open_recommendations += len(recs)

        # Cache stats and top violations
        cache_stats = await get_cache_stats(self._session, period_days=30)
        top_violations = await get_top_violated_rules(self._session, period_days=30, limit=5)

        # Active alerts count
        alert_result = await self._session.execute(
            select(func.count()).select_from(AlertModel).where(AlertModel.status == "active")
        )
        active_alerts = alert_result.scalar_one()

        return {
            "total_rules": total_rules,
            "avg_health_score": avg_health,
            "total_evaluations_30d": analytics.get("total_evaluations", 0),
            "verdict_distribution": analytics.get("verdict_distribution", {}),
            "active_drift_alerts": active_alerts,
            "open_recommendations": open_recommendations,
            "health_distribution": distribution,
            "cache_stats": cache_stats,
            "top_violated_rules": top_violations,
        }

    async def get_health_scores(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "overall_score",
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Get health scores for all rules.

        Args:
            page: Page number.
            page_size: Items per page.
            sort_by: Field to sort by.

        Returns:
            Paginated list of health scores.
        """
        offset = (page - 1) * page_size
        health_rules_query = select(RuleModel).offset(offset).limit(page_size)
        if project_id:
            health_rules_query = health_rules_query.where(RuleModel.project_id == project_id)
        result = await self._session.execute(health_rules_query)
        rules = list(result.scalars().all())

        health_count_query = select(func.count()).select_from(RuleModel)
        if project_id:
            health_count_query = health_count_query.where(RuleModel.project_id == project_id)
        count_result = await self._session.execute(health_count_query)
        total = count_result.scalar_one()

        scores = []
        for rule in rules:
            rule_dict = self._model_to_dict(rule)
            rule_analytics = await get_rule_analytics(self._session, str(rule.id), period_days=90)
            health = compute_health_score(
                rule_dict,
                evaluation_count_90d=rule_analytics.get("total_evaluations", 0),
            )
            health["rule_id"] = str(rule.id)
            scores.append(health)

        # Sort
        reverse = sort_by != "overall_score" or True  # descending by default
        scores.sort(key=lambda s: s.get(sort_by, 0), reverse=reverse)

        return {"items": scores, "total": total, "page": page, "page_size": page_size}

    async def get_rule_health(self, rule_id: str) -> dict[str, Any]:
        """Get detailed health breakdown for a single rule.

        Args:
            rule_id: UUID string of the rule.

        Returns:
            Health score with all dimensions and issues.
        """
        result = await self._session.execute(select(RuleModel).where(RuleModel.id == UUID(rule_id)))
        rule = result.scalar_one_or_none()
        if rule is None:
            from rulerepo_server.core.errors import NotFoundError

            raise NotFoundError("Rule", rule_id)

        rule_dict = self._model_to_dict(rule)
        analytics = await get_rule_analytics(self._session, rule_id, period_days=90)
        health = compute_health_score(
            rule_dict,
            evaluation_count_90d=analytics.get("total_evaluations", 0),
        )
        health["rule_id"] = rule_id
        return health

    async def get_analytics(self, period_days: int = 30, project_id: str | None = None) -> dict[str, Any]:
        """Get corpus-wide evaluation analytics.

        Args:
            period_days: Number of days to aggregate.

        Returns:
            Analytics summary dict.
        """
        return await get_corpus_analytics(self._session, period_days=period_days)

    async def get_rule_analytics_detail(self, rule_id: str, period_days: int = 30) -> dict[str, Any]:
        """Get per-rule evaluation analytics.

        Args:
            rule_id: UUID string of the rule.
            period_days: Number of days to aggregate.

        Returns:
            Per-rule analytics dict.
        """
        return await get_rule_analytics(self._session, rule_id, period_days=period_days)

    async def get_recommendations(
        self,
        *,
        status: str = "open",
        page: int = 1,
        page_size: int = 50,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Get improvement recommendations by computing health for all rules.

        Args:
            status: Filter by recommendation status.
            page: Page number.
            page_size: Items per page.

        Returns:
            Paginated list of recommendations.
        """
        rec_rules_query = select(RuleModel).limit(100)
        if project_id:
            rec_rules_query = rec_rules_query.where(RuleModel.project_id == project_id)
        result = await self._session.execute(rec_rules_query)
        rules = list(result.scalars().all())

        all_recs: list[dict[str, Any]] = []
        for rule in rules:
            rule_dict = self._model_to_dict(rule)
            analytics = await get_rule_analytics(self._session, str(rule.id), period_days=90)
            health = compute_health_score(
                rule_dict,
                evaluation_count_90d=analytics.get("total_evaluations", 0),
            )
            recs = generate_recommendations(rule_dict, health, analytics)
            all_recs.extend(recs)

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_recs.sort(key=lambda r: priority_order.get(r.get("priority", "low"), 3))

        # Paginate
        start = (page - 1) * page_size
        return {
            "items": all_recs[start : start + page_size],
            "total": len(all_recs),
            "page": page,
            "page_size": page_size,
        }

    async def get_home_summary(self, project_id: str | None = None) -> dict[str, Any]:
        """Aggregate all data for the outcome-oriented home dashboard.

        Returns compliance rate, trend, rule counts, top violations,
        recent corrections, and pending action counts in a single call.

        Args:
            project_id: Optional project filter.

        Returns:
            Dashboard summary dict.
        """
        from rulerepo_server.adapters.postgres.models import (
            CorrectionModel,
        )

        # Run queries sequentially (same session can't run concurrent queries)

        # 1. Compliance rate + trend
        analytics = await get_corpus_analytics(self._session, period_days=30)
        trend = await get_compliance_trend(self._session, days=7)
        total_evals = analytics.get("total_evaluations", 0)
        dist = analytics.get("verdict_distribution", {})
        allow_count = dist.get("ALLOW", 0)
        compliance_rate = round(allow_count / max(total_evals, 1), 3) if total_evals > 0 else 0.0

        # 2. Rules by status
        status_result = await self._session.execute(
            select(RuleModel.status, func.count(RuleModel.id)).group_by(RuleModel.status)
        )
        rules_by_status = {str(row[0]): row[1] for row in status_result.all()}
        total_rules = sum(rules_by_status.values())

        # 3. Top violated rules (enriched with effectiveness scores)
        top_violated = await get_top_violated_rules(self._session, period_days=30, limit=5)
        try:
            from rulerepo_server.services.intelligence.effectiveness import (
                compute_effectiveness,
            )

            for item in top_violated:
                try:
                    eff = await compute_effectiveness(self._session, item["rule_id"], period_days=30)
                    item["effectiveness_score"] = eff["effectiveness_score"]
                except Exception:
                    item["effectiveness_score"] = None
        except Exception:
            pass

        # 4. Recent corrections
        corr_result = await self._session.execute(
            select(CorrectionModel).order_by(CorrectionModel.created_at.desc()).limit(5)
        )
        recent_corrections = [
            {
                "id": str(r.id),
                "status": r.status,
                "candidate_statement": r.candidate_statement,
                "analysis_type": r.analysis_type,
                "created_at": str(r.created_at),
            }
            for r in corr_result.scalars().all()
        ]

        # 5. Pending actions
        draft_result = await self._session.execute(
            select(func.count(RuleModel.id)).where(RuleModel.status.in_(["DRAFT", "REVIEW"]))
        )
        rules_pending = draft_result.scalar_one()

        pending_corr_result = await self._session.execute(
            select(func.count(CorrectionModel.id)).where(CorrectionModel.status == "pending")
        )
        corrections_pending = pending_corr_result.scalar_one()

        alert_result = await self._session.execute(
            select(func.count(AlertModel.id)).where(AlertModel.status == "active")
        )
        active_alerts = alert_result.scalar_one()

        return {
            "compliance_rate": compliance_rate,
            "compliance_trend": trend,
            "total_rules": total_rules,
            "rules_by_status": rules_by_status,
            "top_violated_rules": top_violated,
            "recent_corrections": recent_corrections,
            "pending_actions": {
                "rules_pending_review": rules_pending,
                "corrections_pending": corrections_pending,
                "active_alerts": active_alerts,
            },
        }

    @staticmethod
    def _model_to_dict(model: Any) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "project_id": str(model.project_id) if hasattr(model, "project_id") else None,
            "statement": model.statement,
            "modality": model.modality,
            "severity": model.severity,
            "status": model.status,
            "scope": model.scope,
            "tags": model.tags,
            "rationale": model.rationale,
            "source_refs": model.source_refs,
            "governance": model.governance,
            "clarity_score": getattr(model, "clarity_score", None),
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

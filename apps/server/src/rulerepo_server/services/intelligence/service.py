"""IntelligenceService — orchestrates health scoring, analytics, and recommendations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import RuleModel
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.intelligence.analytics import get_corpus_analytics, get_rule_analytics
from rulerepo_server.services.intelligence.health_scorer import compute_health_score
from rulerepo_server.services.intelligence.recommender import generate_recommendations

logger = get_logger(__name__)


class IntelligenceService:
    """Orchestrates all intelligence features: health, analytics, recommendations.

    Injected via FastAPI dependency. Uses the same session as the request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_dashboard(self) -> dict[str, Any]:
        """Get corpus-wide intelligence dashboard summary.

        Returns:
            DashboardSummary-compatible dict.
        """
        # Total rules
        result = await self._session.execute(select(func.count()).select_from(RuleModel))
        total_rules = result.scalar_one()

        # Analytics from audit log
        analytics = await get_corpus_analytics(self._session, period_days=30)

        # Compute average health (sample up to 100 rules for performance)
        rules_result = await self._session.execute(select(RuleModel).limit(100))
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

        return {
            "total_rules": total_rules,
            "avg_health_score": avg_health,
            "total_evaluations_30d": analytics.get("total_evaluations", 0),
            "verdict_distribution": analytics.get("verdict_distribution", {}),
            "active_drift_alerts": 0,  # populated when drift detector runs
            "open_recommendations": 0,  # populated when recommender runs
            "health_distribution": distribution,
        }

    async def get_health_scores(
        self, *, page: int = 1, page_size: int = 50, sort_by: str = "overall_score"
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
        result = await self._session.execute(select(RuleModel).offset(offset).limit(page_size))
        rules = list(result.scalars().all())

        count_result = await self._session.execute(select(func.count()).select_from(RuleModel))
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

    async def get_analytics(self, period_days: int = 30) -> dict[str, Any]:
        """Get corpus-wide evaluation analytics.

        Args:
            period_days: Number of days to aggregate.

        Returns:
            Analytics summary dict.
        """
        return await get_corpus_analytics(self._session, period_days=period_days)

    async def get_rule_analytics_detail(
        self, rule_id: str, period_days: int = 30
    ) -> dict[str, Any]:
        """Get per-rule evaluation analytics.

        Args:
            rule_id: UUID string of the rule.
            period_days: Number of days to aggregate.

        Returns:
            Per-rule analytics dict.
        """
        return await get_rule_analytics(self._session, rule_id, period_days=period_days)

    async def get_recommendations(
        self, *, status: str = "open", page: int = 1, page_size: int = 50
    ) -> dict[str, Any]:
        """Get improvement recommendations by computing health for all rules.

        Args:
            status: Filter by recommendation status.
            page: Page number.
            page_size: Items per page.

        Returns:
            Paginated list of recommendations.
        """
        result = await self._session.execute(select(RuleModel).limit(100))
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

    @staticmethod
    def _model_to_dict(model: Any) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "statement": model.statement,
            "modality": model.modality,
            "severity": model.severity,
            "status": model.status,
            "scope": model.scope,
            "tags": model.tags,
            "rationale": model.rationale,
            "source_refs": model.source_refs,
            "governance": model.governance,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

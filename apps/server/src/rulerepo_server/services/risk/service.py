"""Risk Register service -- manages risks and rule-to-risk mappings.

See IMPROVEMENT.md RR-019.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.risk import (
    Risk,
    RiskImpact,
    RiskLikelihood,
    RiskRuleMapping,
    RiskStatus,
)

logger = get_logger(__name__)


class RiskService:
    """Manages risks and their mappings to rules (controls).

    Uses in-memory storage. Will be replaced with Postgres persistence
    once the DB model is finalized.
    """

    def __init__(self) -> None:
        self._risks: dict[UUID, Risk] = {}
        self._mappings: list[RiskRuleMapping] = []

    # ------------------------------------------------------------------
    # Risk CRUD
    # ------------------------------------------------------------------

    async def create_risk(
        self,
        *,
        tenant_id: str = "default",
        title: str,
        description: str = "",
        likelihood: RiskLikelihood = RiskLikelihood.POSSIBLE,
        impact: RiskImpact = RiskImpact.MODERATE,
        status: RiskStatus = RiskStatus.IDENTIFIED,
        owner: str = "",
        category: str = "",
        framework_refs: list[str] | None = None,
        inherent_score: float = 0.0,
        residual_score: float = 0.0,
    ) -> Risk:
        """Create a new risk entry.

        Args:
            tenant_id: Tenant identifier.
            title: Short human-readable title.
            description: Detailed description of the risk.
            likelihood: Qualitative likelihood rating.
            impact: Qualitative impact rating.
            status: Initial lifecycle status.
            owner: Person or team responsible for this risk.
            category: Risk category (e.g. operational, financial).
            framework_refs: Regulatory framework references.
            inherent_score: Pre-control risk score.
            residual_score: Post-control risk score.

        Returns:
            The newly created Risk.
        """
        risk = Risk(
            id=uuid4(),
            tenant_id=tenant_id,
            title=title,
            description=description,
            likelihood=likelihood,
            impact=impact,
            status=status,
            owner=owner,
            category=category,
            framework_refs=framework_refs or [],
            inherent_score=inherent_score,
            residual_score=residual_score,
        )
        self._risks[risk.id] = risk

        logger.info(
            "risk_created",
            risk_id=str(risk.id),
            title=title,
            category=category,
        )
        return risk

    async def get_risk(self, risk_id: UUID) -> Risk:
        """Get a single risk by ID.

        Args:
            risk_id: The risk UUID.

        Returns:
            The matching risk.

        Raises:
            NotFoundError: If the risk does not exist.
        """
        risk = self._risks.get(risk_id)
        if risk is None:
            raise NotFoundError("Risk", str(risk_id))
        return risk

    async def list_risks(
        self,
        tenant_id: str = "default",
        *,
        category: str | None = None,
        status: RiskStatus | None = None,
        framework_ref: str | None = None,
    ) -> list[Risk]:
        """List risks for a tenant, optionally filtered.

        Args:
            tenant_id: Tenant identifier to scope the lookup.
            category: Filter by risk category.
            status: Filter by lifecycle status.
            framework_ref: Filter by framework reference (substring match).

        Returns:
            List of matching risks ordered by creation time (newest first).
        """
        results: list[Risk] = []
        for risk in self._risks.values():
            if risk.tenant_id != tenant_id:
                continue
            if category is not None and risk.category != category:
                continue
            if status is not None and risk.status != status:
                continue
            if framework_ref is not None and not any(framework_ref in ref for ref in risk.framework_refs):
                continue
            results.append(risk)

        results.sort(key=lambda r: r.created_at, reverse=True)
        return results

    async def update_risk(
        self,
        risk_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        likelihood: RiskLikelihood | None = None,
        impact: RiskImpact | None = None,
        status: RiskStatus | None = None,
        owner: str | None = None,
        category: str | None = None,
        framework_refs: list[str] | None = None,
        inherent_score: float | None = None,
        residual_score: float | None = None,
    ) -> Risk:
        """Update fields on an existing risk.

        Args:
            risk_id: The risk UUID.
            title: New title (if provided).
            description: New description (if provided).
            likelihood: New likelihood (if provided).
            impact: New impact (if provided).
            status: New status (if provided).
            owner: New owner (if provided).
            category: New category (if provided).
            framework_refs: New framework references (if provided).
            inherent_score: New inherent score (if provided).
            residual_score: New residual score (if provided).

        Returns:
            The updated Risk.

        Raises:
            NotFoundError: If the risk does not exist.
        """
        risk = self._risks.get(risk_id)
        if risk is None:
            raise NotFoundError("Risk", str(risk_id))

        if title is not None:
            risk.title = title
        if description is not None:
            risk.description = description
        if likelihood is not None:
            risk.likelihood = likelihood
        if impact is not None:
            risk.impact = impact
        if status is not None:
            risk.status = status
        if owner is not None:
            risk.owner = owner
        if category is not None:
            risk.category = category
        if framework_refs is not None:
            risk.framework_refs = framework_refs
        if inherent_score is not None:
            risk.inherent_score = inherent_score
        if residual_score is not None:
            risk.residual_score = residual_score

        risk.updated_at = datetime.now(tz=UTC)

        logger.info("risk_updated", risk_id=str(risk_id))
        return risk

    # ------------------------------------------------------------------
    # Rule-to-Risk mappings
    # ------------------------------------------------------------------

    async def map_rule_to_risk(
        self,
        risk_id: UUID,
        rule_id: UUID,
        mitigation_strength: str = "partial",
        notes: str = "",
    ) -> RiskRuleMapping:
        """Map a rule (control) to a risk it mitigates.

        Args:
            risk_id: The risk UUID.
            rule_id: The rule UUID.
            mitigation_strength: One of full, partial, minimal.
            notes: Optional explanation of the mapping.

        Returns:
            The created mapping.

        Raises:
            NotFoundError: If the risk does not exist.
        """
        if risk_id not in self._risks:
            raise NotFoundError("Risk", str(risk_id))

        mapping = RiskRuleMapping(
            risk_id=risk_id,
            rule_id=rule_id,
            mitigation_strength=mitigation_strength,
            notes=notes,
        )
        self._mappings.append(mapping)

        logger.info(
            "rule_mapped_to_risk",
            risk_id=str(risk_id),
            rule_id=str(rule_id),
            mitigation_strength=mitigation_strength,
        )
        return mapping

    async def get_risk_coverage(self, risk_id: UUID) -> dict[str, object]:
        """Get rule coverage summary for a single risk.

        Args:
            risk_id: The risk UUID.

        Returns:
            Dict with risk details, mapped rules, and coverage percentage.

        Raises:
            NotFoundError: If the risk does not exist.
        """
        risk = self._risks.get(risk_id)
        if risk is None:
            raise NotFoundError("Risk", str(risk_id))

        mappings = [m for m in self._mappings if m.risk_id == risk_id]
        full_count = sum(1 for m in mappings if m.mitigation_strength == "full")
        partial_count = sum(1 for m in mappings if m.mitigation_strength == "partial")
        minimal_count = sum(1 for m in mappings if m.mitigation_strength == "minimal")

        # Coverage heuristic: full=1.0, partial=0.5, minimal=0.25
        weighted = full_count * 1.0 + partial_count * 0.5 + minimal_count * 0.25
        coverage_pct = min(round(weighted / max(len(mappings), 1) * 100, 2), 100.0)

        return {
            "risk_id": str(risk.id),
            "risk_title": risk.title,
            "total_rules": len(mappings),
            "full": full_count,
            "partial": partial_count,
            "minimal": minimal_count,
            "coverage_pct": coverage_pct,
            "rules": [
                {
                    "rule_id": str(m.rule_id),
                    "mitigation_strength": m.mitigation_strength,
                    "notes": m.notes,
                }
                for m in mappings
            ],
        }

    async def get_rule_risks(self, rule_id: UUID) -> list[Risk]:
        """Get all risks that a given rule mitigates.

        Args:
            rule_id: The rule UUID.

        Returns:
            List of Risk objects linked to the rule.
        """
        risk_ids = {m.risk_id for m in self._mappings if m.rule_id == rule_id}
        return [self._risks[rid] for rid in risk_ids if rid in self._risks]

    async def get_framework_coverage(
        self,
        framework_ref: str,
        tenant_id: str = "default",
    ) -> dict[str, object]:
        """Get coverage summary for a regulatory framework.

        Args:
            framework_ref: Framework reference string (substring match).
            tenant_id: Tenant identifier.

        Returns:
            Dict with framework risks, coverage stats, and per-risk details.
        """
        # Find all risks referencing this framework.
        framework_risks = [
            r
            for r in self._risks.values()
            if r.tenant_id == tenant_id and any(framework_ref in ref for ref in r.framework_refs)
        ]

        per_risk: list[dict[str, object]] = []
        total_covered = 0

        for risk in framework_risks:
            mappings = [m for m in self._mappings if m.risk_id == risk.id]
            is_covered = len(mappings) > 0
            if is_covered:
                total_covered += 1
            per_risk.append(
                {
                    "risk_id": str(risk.id),
                    "risk_title": risk.title,
                    "status": risk.status.value,
                    "rule_count": len(mappings),
                    "covered": is_covered,
                }
            )

        total = len(framework_risks)
        coverage_pct = round(total_covered / max(total, 1) * 100, 2)

        return {
            "framework_ref": framework_ref,
            "total_risks": total,
            "covered_risks": total_covered,
            "uncovered_risks": total - total_covered,
            "coverage_pct": coverage_pct,
            "risks": per_risk,
        }

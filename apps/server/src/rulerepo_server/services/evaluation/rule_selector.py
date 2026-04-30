"""Rule Selector — narrows the full corpus to the ~5-20 rules relevant to this change.

Per CLAUDE_ENHANCE.md §1.4.2: selection pipeline runs scope→severity→tag→semantic.
Steps 1-3 should complete in <50ms. Step 4 (semantic) only when needed.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import RuleModel
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import EvaluationContext

logger = get_logger(__name__)

# Severity ordering for minimum threshold filtering
_SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


async def select_rules(
    session: AsyncSession,
    context: EvaluationContext,
    *,
    max_rules: int = 20,
    severity_min: str = "MEDIUM",
    modality_filter: list[str] | None = None,
    scope: str | None = None,
    federation_id: str | None = None,
    environment: str | None = None,
) -> list[dict[str, Any]]:
    """Select rules applicable to the given evaluation context.

    Runs a multi-stage filter pipeline, each stage narrowing the set:
    1. Scope filter (SQL)
    2. Severity/modality filter (in-memory)
    3. Tag filter (in-memory, if context has detected concepts)
    4. Rank by relevance and cap at max_rules

    Args:
        session: Async database session.
        context: The evaluation context.
        max_rules: Maximum rules to return.
        severity_min: Minimum severity to include.
        modality_filter: If set, only include these modalities. Default: MUST + MUST_NOT.
        scope: Explicit scope filter (overrides context-derived scope).
        federation_id: If provided, use federation-resolved rules instead of querying all.
        environment: If provided, use the snapshot deployed to this environment.

    Returns:
        List of rule dicts, ranked by relevance, capped at max_rules.
    """
    # When environment is provided, use the deployed snapshot
    if environment is not None:
        from rulerepo_server.adapters.postgres.models import (
            RuleSetDeploymentModel,
            RuleSetSnapshotModel,
        )
        from rulerepo_server.services.snapshots.serializer import deserialize_snapshot

        deploy_query = select(RuleSetDeploymentModel).where(
            RuleSetDeploymentModel.environment == environment,
            RuleSetDeploymentModel.active.is_(True),
        )
        deploy_result = await session.execute(deploy_query)
        deployment = deploy_result.scalar_one_or_none()
        if deployment is not None:
            snap_query = select(RuleSetSnapshotModel).where(RuleSetSnapshotModel.id == deployment.snapshot_id)
            snap_result = await session.execute(snap_query)
            snapshot = snap_result.scalar_one_or_none()
            if snapshot is not None:
                rules = deserialize_snapshot(snapshot.rule_snapshot)
                logger.info(
                    "rule_selector_environment",
                    environment=environment,
                    rules=len(rules),
                )
                return rules[:max_rules]
        logger.info("rule_selector_environment_fallback", environment=environment)

    # When federation_id is provided, delegate to the federation resolver
    if federation_id is not None:
        from rulerepo_server.services.federation.resolver import resolve_effective_rules

        effective = await resolve_effective_rules(federation_id, session)
        logger.info("rule_selector_federation", federation_id=federation_id, rules=len(effective))
        return effective[:max_rules]

    if modality_filter is None:
        modality_filter = ["MUST", "MUST_NOT"]

    min_order = _SEVERITY_ORDER.get(severity_min, 1)

    # Stage 1: Load candidate rules from Postgres with basic filters
    query = select(RuleModel).where(
        RuleModel.status.in_(["APPROVED", "EFFECTIVE"]),
    )

    # Scope filter: if scope provided, filter by overlap with any scope segment.
    # Handles both "engineering/python" (slash-separated) and "engineering" (single).
    if scope:
        scope_parts = [s.strip() for s in scope.split("/") if s.strip()]
        from sqlalchemy import or_

        scope_conditions = [RuleModel.scope.contains([part]) for part in scope_parts]
        if scope_conditions:
            query = query.where(or_(*scope_conditions))

    result = await session.execute(query.limit(500))
    all_rules_raw = list(result.scalars().all())

    # Enforce effective_period (CLAUDE_ENHANCE.md §0.3)
    from datetime import datetime

    now = datetime.now(tz=UTC)
    all_rules = []
    for rule in all_rules_raw:
        ep = rule.effective_period if isinstance(rule.effective_period, dict) else {}
        valid_from = ep.get("valid_from")
        valid_until = ep.get("valid_until")
        # Parse ISO strings if needed
        if isinstance(valid_from, str) and valid_from:
            try:
                valid_from = datetime.fromisoformat(valid_from)
            except (ValueError, TypeError):
                valid_from = None
        if isinstance(valid_until, str) and valid_until:
            try:
                valid_until = datetime.fromisoformat(valid_until)
            except (ValueError, TypeError):
                valid_until = None
        # Skip rules outside their effective period
        if valid_from and hasattr(valid_from, "timestamp") and valid_from > now:
            continue
        if valid_until and hasattr(valid_until, "timestamp") and valid_until < now:
            continue
        all_rules.append(rule)

    logger.info("rule_selector_stage1", candidates=len(all_rules))

    # Stage 2: Severity and modality filter (in-memory)
    filtered = []
    for rule in all_rules:
        rule_severity_order = _SEVERITY_ORDER.get(rule.severity, 0)
        if rule_severity_order < min_order:
            continue
        if modality_filter and rule.modality not in modality_filter:
            continue
        filtered.append(rule)

    logger.info("rule_selector_stage2", after_severity_modality=len(filtered))

    # Stage 3: Scope matching on file paths and languages (in-memory)
    if context.file_paths or context.languages:
        scored: list[tuple[Any, float]] = []
        for rule in filtered:
            score = _compute_relevance(rule, context)
            scored.append((rule, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        filtered = [r for r, _ in scored]

    # Stage 4: Cap at max_rules
    selected = filtered[:max_rules]

    logger.info("rule_selector_final", selected=len(selected))

    return [_rule_to_dict(r) for r in selected]


def _compute_relevance(rule: Any, context: EvaluationContext) -> float:
    """Compute a relevance score for a rule given the context.

    Higher scores = more relevant. Uses scope, tag, and language overlap.
    """
    score = 0.0
    rule_scope = rule.scope if isinstance(rule.scope, list) else []
    rule_tags = rule.tags if isinstance(rule.tags, list) else []

    # Scope overlap with file paths
    for scope_item in rule_scope:
        for fp in context.file_paths:
            if scope_item.lower() in fp.lower():
                score += 10.0
        for lang in context.languages:
            if lang.lower() in scope_item.lower():
                score += 5.0

    # Tag overlap with languages and file paths
    for tag in rule_tags:
        tag_lower = tag.lower()
        for lang in context.languages:
            if lang.lower() in tag_lower or tag_lower in lang.lower():
                score += 3.0
        for fp in context.file_paths:
            if tag_lower in fp.lower():
                score += 2.0

    # Severity bonus (CRITICAL rules always rank higher)
    severity_bonus = {"CRITICAL": 5, "HIGH": 3, "MEDIUM": 1, "LOW": 0}
    score += severity_bonus.get(rule.severity, 0)

    return score


def _rule_to_dict(rule: Any) -> dict[str, Any]:
    """Convert a RuleModel to a dict for use by the evaluation core."""
    return {
        "id": str(rule.id),
        "statement": rule.statement,
        "modality": rule.modality,
        "severity": rule.severity,
        "status": rule.status,
        "scope": rule.scope,
        "tags": rule.tags,
        "rationale": rule.rationale,
        "maturity_level": getattr(rule, "maturity_level", "proven"),
    }

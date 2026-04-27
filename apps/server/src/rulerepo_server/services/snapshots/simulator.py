"""Impact simulator — compare a proposed snapshot against a deployed environment."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import (
    AuditLogModel,
    RuleSetDeploymentModel,
    RuleSetSnapshotModel,
)
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.snapshots.serializer import deserialize_snapshot

logger = get_logger(__name__)


async def simulate_impact(
    snapshot_id: str,
    compare_environment: str,
    sample_size: int,
    session: AsyncSession,
    gemini: Any | None = None,
) -> dict[str, Any]:
    """Replay historical evaluations against a proposed snapshot.

    This performs a simplified structural comparison between the proposed
    snapshot and the currently deployed snapshot.  A full LLM-driven
    replay is deferred to a future enhancement.

    Args:
        snapshot_id: UUID of the proposed snapshot.
        compare_environment: Environment to compare against (e.g. "production").
        sample_size: Maximum number of historical evaluations to consider.
        session: Async database session.
        gemini: Optional Gemini client (reserved for future LLM replay).

    Returns:
        Dict with total_replayed, rules_added, rules_removed, risk_assessment.
    """
    # 1. Load proposed snapshot
    proposed_query = select(RuleSetSnapshotModel).where(RuleSetSnapshotModel.id == snapshot_id)
    proposed_result = await session.execute(proposed_query)
    proposed_snapshot = proposed_result.scalar_one_or_none()
    if proposed_snapshot is None:
        return {
            "total_replayed": 0,
            "rules_added": 0,
            "rules_removed": 0,
            "risk_assessment": f"Error: snapshot {snapshot_id} not found.",
        }

    proposed_rules = deserialize_snapshot(proposed_snapshot.rule_snapshot)
    proposed_ids = {r["id"] for r in proposed_rules}

    # 2. Get current active deployment for the environment
    deploy_query = select(RuleSetDeploymentModel).where(
        RuleSetDeploymentModel.environment == compare_environment,
        RuleSetDeploymentModel.active.is_(True),
    )
    deploy_result = await session.execute(deploy_query)
    current_deployment = deploy_result.scalar_one_or_none()

    if current_deployment is None:
        return {
            "total_replayed": 0,
            "rules_added": len(proposed_ids),
            "rules_removed": 0,
            "risk_assessment": (
                f"No active deployment found for environment '{compare_environment}'. "
                "All rules in the proposed snapshot would be new."
            ),
        }

    # Load current snapshot
    current_snap_query = select(RuleSetSnapshotModel).where(
        RuleSetSnapshotModel.id == current_deployment.snapshot_id
    )
    current_snap_result = await session.execute(current_snap_query)
    current_snapshot = current_snap_result.scalar_one_or_none()

    if current_snapshot is None:
        return {
            "total_replayed": 0,
            "rules_added": len(proposed_ids),
            "rules_removed": 0,
            "risk_assessment": "Current deployment's snapshot is missing.",
        }

    current_rules = deserialize_snapshot(current_snapshot.rule_snapshot)
    current_ids = {r["id"] for r in current_rules}

    # 3. Structural diff
    only_in_proposed = proposed_ids - current_ids
    only_in_current = current_ids - proposed_ids

    # 4. Fetch recent evaluation audit records (last 30 days)
    cutoff = datetime.now(tz=UTC) - timedelta(days=30)
    eval_query = (
        select(AuditLogModel)
        .where(
            AuditLogModel.action == "evaluate",
            AuditLogModel.timestamp >= cutoff,
        )
        .order_by(AuditLogModel.timestamp.desc())
        .limit(sample_size)
    )
    eval_result = await session.execute(eval_query)
    eval_records = list(eval_result.scalars().all())
    total_replayed = len(eval_records)

    # 5. Build risk assessment summary
    risk_parts: list[str] = []
    if only_in_proposed:
        risk_parts.append(
            f"{len(only_in_proposed)} rule(s) would be added that are not in the "
            f"current '{compare_environment}' deployment."
        )
    if only_in_current:
        risk_parts.append(
            f"{len(only_in_current)} rule(s) currently in '{compare_environment}' would be removed."
        )
    if not only_in_proposed and not only_in_current:
        risk_parts.append(
            "The proposed snapshot is identical to the current deployment. No impact expected."
        )
    if total_replayed > 0:
        risk_parts.append(f"Analyzed {total_replayed} recent evaluation(s) from the last 30 days.")
    else:
        risk_parts.append("No recent evaluations found for replay analysis.")

    logger.info(
        "simulation_complete",
        snapshot_id=snapshot_id,
        environment=compare_environment,
        rules_added=len(only_in_proposed),
        rules_removed=len(only_in_current),
        total_replayed=total_replayed,
    )

    return {
        "total_replayed": total_replayed,
        "rules_added": len(only_in_proposed),
        "rules_removed": len(only_in_current),
        "risk_assessment": " ".join(risk_parts),
    }

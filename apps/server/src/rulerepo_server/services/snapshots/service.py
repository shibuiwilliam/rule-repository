"""SnapshotService — create, deploy, and roll back immutable rule-set snapshots."""

from __future__ import annotations

import fnmatch
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import (
    DEFAULT_PROJECT_ID,
    RuleModel,
    RuleSetDeploymentModel,
    RuleSetSnapshotModel,
)
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.snapshots.serializer import serialize_rules

logger = get_logger(__name__)


class SnapshotService:
    """Manages rule-set snapshots and environment deployments."""

    def __init__(
        self,
        session: AsyncSession,
        gemini: Any | None = None,
    ) -> None:
        self._session = session
        self._gemini = gemini

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    async def create_snapshot(
        self,
        name: str,
        scope_filter: list[str] | None = None,
        description: str | None = None,
        created_by: str = "system",
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new snapshot of active rules matching *scope_filter*.

        Args:
            name: Human-readable snapshot name.
            scope_filter: List of glob patterns to match against rule scope items.
                          An empty list means "all active rules".
            description: Optional description.
            created_by: Actor creating the snapshot.

        Returns:
            Dict with id, name, rule_count, created_at.
        """
        effective_filter = scope_filter or []

        # Query active rules (APPROVED or EFFECTIVE)
        query = select(RuleModel).where(
            RuleModel.status.in_(["APPROVED", "EFFECTIVE"]),
        )
        if project_id:
            query = query.where(RuleModel.project_id == project_id)
        result = await self._session.execute(query)
        all_rules: list[Any] = list(result.scalars().all())

        # Apply scope filter via fnmatch
        if effective_filter:
            matched: list[Any] = []
            for rule in all_rules:
                rule_scope = rule.scope if isinstance(rule.scope, list) else []
                if _scope_matches(rule_scope, effective_filter):
                    matched.append(rule)
            all_rules = matched

        rule_snapshot = serialize_rules(all_rules)

        model = RuleSetSnapshotModel(
            name=name,
            description=description,
            scope_filter=effective_filter,
            rule_snapshot=rule_snapshot,
            rule_count=len(rule_snapshot),
            created_by=created_by,
            project_id=project_id or DEFAULT_PROJECT_ID,
        )
        self._session.add(model)
        await self._session.flush()

        logger.info(
            "snapshot_created",
            snapshot_id=str(model.id),
            name=name,
            rule_count=model.rule_count,
        )

        return {
            "id": str(model.id),
            "name": model.name,
            "description": model.description,
            "scope_filter": model.scope_filter,
            "rule_count": model.rule_count,
            "created_by": model.created_by,
            "created_at": model.created_at.isoformat() if model.created_at else "",
        }

    async def list_snapshots(self, project_id: str | None = None) -> list[dict[str, Any]]:
        """Return all snapshots ordered by created_at descending."""
        query = select(RuleSetSnapshotModel).order_by(RuleSetSnapshotModel.created_at.desc())
        if project_id:
            query = query.where(RuleSetSnapshotModel.project_id == project_id)
        result = await self._session.execute(query)
        rows = result.scalars().all()
        return [_snapshot_to_dict(r) for r in rows]

    async def get_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        """Return a single snapshot by ID.

        Raises:
            ValueError: If the snapshot is not found.
        """
        query = select(RuleSetSnapshotModel).where(RuleSetSnapshotModel.id == snapshot_id)
        result = await self._session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            msg = f"Snapshot not found: {snapshot_id}"
            raise ValueError(msg)
        return _snapshot_to_dict(row)

    # ------------------------------------------------------------------
    # Deployments
    # ------------------------------------------------------------------

    async def deploy(
        self,
        snapshot_id: str,
        environment: str,
        deployed_by: str = "system",
    ) -> dict[str, Any]:
        """Deploy a snapshot to an environment.

        Deactivates any current active deployment for the environment
        before inserting the new one.

        Args:
            snapshot_id: UUID of the snapshot to deploy.
            environment: Target environment name (e.g. "production", "staging").
            deployed_by: Actor performing the deployment.

        Returns:
            Dict representing the new deployment.
        """
        # Verify snapshot exists
        await self.get_snapshot(snapshot_id)

        # Deactivate current active deployment for this environment
        await self._session.execute(
            update(RuleSetDeploymentModel)
            .where(
                RuleSetDeploymentModel.environment == environment,
                RuleSetDeploymentModel.active.is_(True),
            )
            .values(active=False)
        )

        deployment = RuleSetDeploymentModel(
            snapshot_id=snapshot_id,
            environment=environment,
            deployed_by=deployed_by,
        )
        self._session.add(deployment)
        await self._session.flush()

        logger.info(
            "snapshot_deployed",
            deployment_id=str(deployment.id),
            snapshot_id=snapshot_id,
            environment=environment,
        )

        return _deployment_to_dict(deployment)

    async def rollback(self, deployment_id: str) -> dict[str, Any]:
        """Roll back a deployment.

        Marks the deployment as rolled back and re-activates the most
        recent previous deployment for the same environment.

        Args:
            deployment_id: UUID of the deployment to roll back.

        Returns:
            Dict representing the rolled-back deployment.

        Raises:
            ValueError: If the deployment is not found.
        """
        query = select(RuleSetDeploymentModel).where(RuleSetDeploymentModel.id == deployment_id)
        result = await self._session.execute(query)
        deployment = result.scalar_one_or_none()
        if deployment is None:
            msg = f"Deployment not found: {deployment_id}"
            raise ValueError(msg)

        now = datetime.now(tz=UTC)
        deployment.rolled_back_at = now
        deployment.active = False

        # Re-activate the most recent previous deployment for the same env
        prev_query = (
            select(RuleSetDeploymentModel)
            .where(
                RuleSetDeploymentModel.environment == deployment.environment,
                RuleSetDeploymentModel.id != deployment_id,
                RuleSetDeploymentModel.rolled_back_at.is_(None),
            )
            .order_by(RuleSetDeploymentModel.deployed_at.desc())
            .limit(1)
        )
        prev_result = await self._session.execute(prev_query)
        prev_deployment = prev_result.scalar_one_or_none()
        if prev_deployment is not None:
            prev_deployment.active = True

        await self._session.flush()

        logger.info(
            "snapshot_rolled_back",
            deployment_id=deployment_id,
            environment=deployment.environment,
            previous_deployment_id=str(prev_deployment.id) if prev_deployment else None,
        )

        return _deployment_to_dict(deployment)

    async def get_active_deployment(self, environment: str) -> dict[str, Any] | None:
        """Return the active deployment for an environment, or ``None``."""
        query = select(RuleSetDeploymentModel).where(
            RuleSetDeploymentModel.environment == environment,
            RuleSetDeploymentModel.active.is_(True),
        )
        result = await self._session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _deployment_to_dict(row)

    async def list_deployments(self) -> list[dict[str, Any]]:
        """Return all deployments ordered by deployed_at descending."""
        query = select(RuleSetDeploymentModel).order_by(RuleSetDeploymentModel.deployed_at.desc())
        result = await self._session.execute(query)
        rows = result.scalars().all()
        return [_deployment_to_dict(r) for r in rows]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _scope_matches(rule_scope: list[str], filters: list[str]) -> bool:
    """Return True if any rule scope item matches any filter pattern."""
    for scope_item in rule_scope:
        for pattern in filters:
            if fnmatch.fnmatch(scope_item, pattern):
                return True
    return False


def _snapshot_to_dict(row: RuleSetSnapshotModel) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "description": row.description,
        "scope_filter": row.scope_filter if row.scope_filter else [],
        "rule_count": row.rule_count,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def _deployment_to_dict(row: RuleSetDeploymentModel) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "snapshot_id": str(row.snapshot_id),
        "environment": row.environment,
        "active": row.active,
        "deployed_by": row.deployed_by,
        "deployed_at": row.deployed_at.isoformat() if row.deployed_at else "",
        "rolled_back_at": row.rolled_back_at.isoformat() if row.rolled_back_at else None,
    }

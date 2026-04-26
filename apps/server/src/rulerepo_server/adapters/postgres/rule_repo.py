"""PostgreSQL repository for Rule CRUD operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import (
    RuleModel,
    RuleRelationshipModel,
    RuleRevisionModel,
)
from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class PostgresRuleRepository:
    """Async CRUD operations for rules against PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, rule_data: dict) -> RuleModel:
        """Insert a new rule and return the persisted model.

        Args:
            rule_data: Dictionary of rule fields matching RuleModel columns.

        Returns:
            The newly created RuleModel instance.
        """
        model = RuleModel(**rule_data)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        logger.info("rule_created", rule_id=str(model.id))
        return model

    async def get_by_id(self, rule_id: UUID) -> RuleModel:
        """Fetch a single rule by ID.

        Args:
            rule_id: The rule's UUID.

        Returns:
            The matching RuleModel.

        Raises:
            NotFoundError: If the rule does not exist.
        """
        result = await self._session.execute(select(RuleModel).where(RuleModel.id == rule_id))
        model = result.scalar_one_or_none()
        if model is None:
            raise NotFoundError("Rule", str(rule_id))
        return model

    async def list_rules(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        modality: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        scope: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> tuple[list[RuleModel], int]:
        """List rules with optional filters and pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            modality: Filter by modality.
            severity: Filter by severity.
            status: Filter by status.
            scope: Filter by scope (any match).
            tags: Filter by tags (any match).

        Returns:
            Tuple of (list of RuleModel, total count).
        """
        query = select(RuleModel)
        count_query = select(func.count()).select_from(RuleModel)

        if modality:
            query = query.where(RuleModel.modality == modality)
            count_query = count_query.where(RuleModel.modality == modality)
        if severity:
            query = query.where(RuleModel.severity == severity)
            count_query = count_query.where(RuleModel.severity == severity)
        if status:
            query = query.where(RuleModel.status == status)
            count_query = count_query.where(RuleModel.status == status)
        if scope:
            query = query.where(RuleModel.scope.contains(scope))
            count_query = count_query.where(RuleModel.scope.contains(scope))
        if tags:
            query = query.where(RuleModel.tags.contains(tags))
            count_query = count_query.where(RuleModel.tags.contains(tags))

        query = query.order_by(RuleModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(query)
        rules = list(result.scalars().all())

        count_result = await self._session.execute(count_query)
        total = count_result.scalar_one()

        return rules, total

    async def update(self, rule_id: UUID, updates: dict) -> RuleModel:
        """Update an existing rule's fields.

        Args:
            rule_id: The rule's UUID.
            updates: Dictionary of fields to update.

        Returns:
            The updated RuleModel.

        Raises:
            NotFoundError: If the rule does not exist.
        """
        model = await self.get_by_id(rule_id)
        for key, value in updates.items():
            if value is not None and hasattr(model, key):
                setattr(model, key, value)
        await self._session.flush()
        await self._session.refresh(model)
        logger.info("rule_updated", rule_id=str(rule_id))
        return model

    async def create_revision(self, revision_data: dict) -> RuleRevisionModel:
        """Create a new revision snapshot.

        Args:
            revision_data: Dictionary of revision fields.

        Returns:
            The newly created RuleRevisionModel.
        """
        model = RuleRevisionModel(**revision_data)
        self._session.add(model)
        await self._session.flush()
        return model

    async def get_revisions(self, rule_id: UUID) -> list[RuleRevisionModel]:
        """Get all revisions for a rule, ordered by revision number.

        Args:
            rule_id: The rule's UUID.

        Returns:
            List of RuleRevisionModel ordered by revision_number.
        """
        result = await self._session.execute(
            select(RuleRevisionModel)
            .where(RuleRevisionModel.rule_id == rule_id)
            .order_by(RuleRevisionModel.revision_number)
        )
        return list(result.scalars().all())

    async def get_latest_revision_number(self, rule_id: UUID) -> int:
        """Get the latest revision number for a rule.

        Args:
            rule_id: The rule's UUID.

        Returns:
            The latest revision number, or 0 if no revisions exist.
        """
        result = await self._session.execute(
            select(func.max(RuleRevisionModel.revision_number)).where(
                RuleRevisionModel.rule_id == rule_id
            )
        )
        return result.scalar_one() or 0

    async def create_relationship(self, rel_data: dict) -> RuleRelationshipModel:
        """Create a relationship between two rules.

        Args:
            rel_data: Dictionary with source_id, target_id, relationship_type.

        Returns:
            The newly created RuleRelationshipModel.
        """
        model = RuleRelationshipModel(**rel_data)
        self._session.add(model)
        await self._session.flush()
        logger.info(
            "relationship_created",
            source_id=str(rel_data["source_id"]),
            target_id=str(rel_data["target_id"]),
            type=rel_data["relationship_type"],
        )
        return model

    async def get_relationships(self, rule_id: UUID) -> list[RuleRelationshipModel]:
        """Get all relationships involving a rule (as source or target).

        Args:
            rule_id: The rule's UUID.

        Returns:
            List of RuleRelationshipModel.
        """
        result = await self._session.execute(
            select(RuleRelationshipModel).where(
                (RuleRelationshipModel.source_id == rule_id)
                | (RuleRelationshipModel.target_id == rule_id)
            )
        )
        return list(result.scalars().all())

    async def delete_relationship(
        self, source_id: UUID, target_id: UUID, relationship_type: str
    ) -> None:
        """Delete a specific relationship between two rules.

        Args:
            source_id: Source rule UUID.
            target_id: Target rule UUID.
            relationship_type: Type of relationship to remove.
        """
        result = await self._session.execute(
            select(RuleRelationshipModel).where(
                RuleRelationshipModel.source_id == source_id,
                RuleRelationshipModel.target_id == target_id,
                RuleRelationshipModel.relationship_type == relationship_type,
            )
        )
        model = result.scalar_one_or_none()
        if model:
            await self._session.delete(model)
            await self._session.flush()

    async def get_rules_by_ids(self, rule_ids: list[UUID]) -> list[RuleModel]:
        """Fetch multiple rules by their IDs.

        Args:
            rule_ids: List of rule UUIDs.

        Returns:
            List of matching RuleModel instances.
        """
        if not rule_ids:
            return []
        result = await self._session.execute(select(RuleModel).where(RuleModel.id.in_(rule_ids)))
        return list(result.scalars().all())

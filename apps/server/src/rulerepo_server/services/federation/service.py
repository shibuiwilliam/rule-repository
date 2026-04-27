"""FederationService — manages federation nodes, memberships, and resolution.

Provides CRUD for federation hierarchy nodes, rule membership management,
effective rule resolution (via the resolver), and federation diff.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import (
    RuleFederationMembershipModel,
    RuleFederationModel,
    RuleModel,
)
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.federation.resolver import (
    resolve_effective_rules,
)

logger = get_logger(__name__)

_VALID_LEVELS = {"organization", "team", "project"}


class FederationService:
    """Manages the cross-project rule federation hierarchy.

    Attributes:
        _session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_federation(
        self,
        *,
        name: str,
        level: str,
        parent_id: str | None = None,
        description: str | None = None,
        default_scope: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new federation node.

        Args:
            name: Human-readable name.
            level: Hierarchy level (organization, team, project).
            parent_id: Parent federation node UUID, or None for root.
            description: Optional description.
            default_scope: Default scope tags for this node.

        Returns:
            Dict representation of the created federation node.

        Raises:
            ValueError: If the level is invalid or the parent does not exist.
        """
        if level not in _VALID_LEVELS:
            msg = f"Invalid federation level: {level}. Must be one of {_VALID_LEVELS}"
            raise ValueError(msg)

        if parent_id is not None:
            parent_result = await self._session.execute(
                select(RuleFederationModel).where(RuleFederationModel.id == UUID(parent_id))
            )
            if parent_result.scalar_one_or_none() is None:
                msg = f"Parent federation not found: {parent_id}"
                raise ValueError(msg)

        node = RuleFederationModel(
            name=name,
            level=level,
            parent_id=UUID(parent_id) if parent_id else None,
            description=description,
            default_scope=default_scope or [],
        )
        self._session.add(node)
        await self._session.flush()

        logger.info("federation_created", federation_id=str(node.id), name=name, level=level)
        return _node_to_dict(node)

    async def list_federations(self) -> list[dict[str, Any]]:
        """Return all federation nodes structured as a tree.

        Root nodes (parent_id is None) are top-level. Children are nested
        under their parent's ``children`` key.

        Returns:
            List of root federation node dicts with nested children.
        """
        result = await self._session.execute(
            select(RuleFederationModel).order_by(RuleFederationModel.created_at)
        )
        all_nodes = list(result.scalars().all())

        # Build lookup and tree
        by_id: dict[str, dict[str, Any]] = {}
        for node in all_nodes:
            d = _node_to_dict(node)
            d["children"] = []
            by_id[str(node.id)] = d

        roots: list[dict[str, Any]] = []
        for node in all_nodes:
            d = by_id[str(node.id)]
            parent_key = str(node.parent_id) if node.parent_id else None
            if parent_key and parent_key in by_id:
                by_id[parent_key]["children"].append(d)
            else:
                roots.append(d)

        return roots

    async def get_federation(self, federation_id: str) -> dict[str, Any]:
        """Get a federation node with its direct children and rules.

        Args:
            federation_id: UUID of the federation node.

        Returns:
            Dict with federation details, children, and direct rules.

        Raises:
            ValueError: If the federation node is not found.
        """
        result = await self._session.execute(
            select(RuleFederationModel).where(RuleFederationModel.id == UUID(federation_id))
        )
        node = result.scalar_one_or_none()
        if node is None:
            msg = f"Federation not found: {federation_id}"
            raise ValueError(msg)

        node_dict = _node_to_dict(node)

        # Get direct children
        children_result = await self._session.execute(
            select(RuleFederationModel).where(RuleFederationModel.parent_id == UUID(federation_id))
        )
        node_dict["children"] = [_node_to_dict(c) for c in children_result.scalars().all()]

        # Get direct rule memberships
        memberships_result = await self._session.execute(
            select(RuleFederationMembershipModel).where(
                RuleFederationMembershipModel.federation_id == UUID(federation_id)
            )
        )
        memberships = list(memberships_result.scalars().all())

        rules: list[dict[str, Any]] = []
        for m in memberships:
            rule_result = await self._session.execute(
                select(RuleModel).where(RuleModel.id == m.rule_id)
            )
            rule = rule_result.scalar_one_or_none()
            if rule is not None:
                rules.append(
                    {
                        "rule_id": str(rule.id),
                        "statement": rule.statement,
                        "modality": rule.modality,
                        "severity": rule.severity,
                        "override_parent_rule_id": str(m.override_parent_rule_id)
                        if m.override_parent_rule_id
                        else None,
                    }
                )
        node_dict["rules"] = rules

        return node_dict

    async def add_rule(
        self,
        federation_id: str,
        rule_id: str,
        override_parent_rule_id: str | None = None,
    ) -> dict[str, Any]:
        """Add a rule to a federation node.

        Args:
            federation_id: UUID of the federation node.
            rule_id: UUID of the rule to add.
            override_parent_rule_id: UUID of a parent-level rule this overrides.

        Returns:
            Dict confirming the membership creation.

        Raises:
            ValueError: If the federation or rule does not exist.
        """
        # Verify federation exists
        fed_result = await self._session.execute(
            select(RuleFederationModel).where(RuleFederationModel.id == UUID(federation_id))
        )
        if fed_result.scalar_one_or_none() is None:
            msg = f"Federation not found: {federation_id}"
            raise ValueError(msg)

        # Verify rule exists
        rule_result = await self._session.execute(
            select(RuleModel).where(RuleModel.id == UUID(rule_id))
        )
        if rule_result.scalar_one_or_none() is None:
            msg = f"Rule not found: {rule_id}"
            raise ValueError(msg)

        membership = RuleFederationMembershipModel(
            rule_id=UUID(rule_id),
            federation_id=UUID(federation_id),
            override_parent_rule_id=UUID(override_parent_rule_id)
            if override_parent_rule_id
            else None,
        )
        self._session.add(membership)
        await self._session.flush()

        logger.info(
            "federation_rule_added",
            federation_id=federation_id,
            rule_id=rule_id,
            overrides=override_parent_rule_id,
        )
        return {
            "membership_id": str(membership.id),
            "federation_id": federation_id,
            "rule_id": rule_id,
            "override_parent_rule_id": override_parent_rule_id,
        }

    async def remove_rule(
        self,
        federation_id: str,
        rule_id: str,
    ) -> dict[str, Any]:
        """Remove a rule from a federation node.

        Args:
            federation_id: UUID of the federation node.
            rule_id: UUID of the rule to remove.

        Returns:
            Dict confirming the removal.

        Raises:
            ValueError: If the membership does not exist.
        """
        result = await self._session.execute(
            select(RuleFederationMembershipModel).where(
                RuleFederationMembershipModel.federation_id == UUID(federation_id),
                RuleFederationMembershipModel.rule_id == UUID(rule_id),
            )
        )
        membership = result.scalar_one_or_none()
        if membership is None:
            msg = f"Rule {rule_id} is not a member of federation {federation_id}"
            raise ValueError(msg)

        await self._session.execute(
            delete(RuleFederationMembershipModel).where(
                RuleFederationMembershipModel.id == membership.id
            )
        )
        await self._session.flush()

        logger.info(
            "federation_rule_removed",
            federation_id=federation_id,
            rule_id=rule_id,
        )
        return {"federation_id": federation_id, "rule_id": rule_id, "removed": True}

    async def get_effective_rules(
        self,
        federation_id: str,
    ) -> list[dict[str, Any]]:
        """Resolve the effective rule set for a federation node.

        Delegates to the resolver which walks the ancestor chain and
        applies overrides from root to leaf.

        Args:
            federation_id: UUID of the target federation node.

        Returns:
            List of effective rule dicts.
        """
        return await resolve_effective_rules(federation_id, self._session)

    async def diff_federations(
        self,
        id_a: str,
        id_b: str,
    ) -> dict[str, Any]:
        """Compare the effective rule sets of two federation nodes.

        Args:
            id_a: UUID of the first federation node.
            id_b: UUID of the second federation node.

        Returns:
            Dict with ``only_in_a``, ``only_in_b``, and ``common`` rule lists.
        """
        rules_a = await resolve_effective_rules(id_a, self._session)
        rules_b = await resolve_effective_rules(id_b, self._session)

        ids_a = {r["rule_id"] for r in rules_a}
        ids_b = {r["rule_id"] for r in rules_b}

        by_id_a = {r["rule_id"]: r for r in rules_a}
        by_id_b = {r["rule_id"]: r for r in rules_b}

        only_a = ids_a - ids_b
        only_b = ids_b - ids_a
        common = ids_a & ids_b

        logger.info(
            "federation_diff",
            id_a=id_a,
            id_b=id_b,
            only_a=len(only_a),
            only_b=len(only_b),
            common=len(common),
        )

        return {
            "federation_a": id_a,
            "federation_b": id_b,
            "only_in_a": [by_id_a[rid] for rid in only_a],
            "only_in_b": [by_id_b[rid] for rid in only_b],
            "common": [by_id_a[rid] for rid in common],
        }


def _node_to_dict(node: RuleFederationModel) -> dict[str, Any]:
    """Convert a RuleFederationModel to a plain dict.

    Args:
        node: The ORM model instance.

    Returns:
        Dict representation.
    """
    return {
        "id": str(node.id),
        "name": node.name,
        "level": node.level,
        "parent_id": str(node.parent_id) if node.parent_id else None,
        "description": node.description,
        "default_scope": node.default_scope or [],
        "created_at": node.created_at.isoformat() if node.created_at else None,
    }

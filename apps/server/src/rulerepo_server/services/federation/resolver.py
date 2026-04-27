"""Federation chain resolver — walks ancestor chain, collects rules with overrides.

The resolver traverses from a leaf federation node up to the root,
collecting all rules and applying child overrides so that the final
effective rule set respects the inheritance hierarchy.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import (
    RuleFederationMembershipModel,
    RuleFederationModel,
    RuleModel,
)
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def get_ancestor_chain(
    federation_id: str,
    session: AsyncSession,
) -> list[RuleFederationModel]:
    """Walk from leaf to root, returning the chain ``[leaf, ..., root]``.

    Args:
        federation_id: UUID of the starting (leaf) federation node.
        session: Async database session.

    Returns:
        Ordered list of federation models from leaf to root.
    """
    chain: list[RuleFederationModel] = []
    current_id: str | None = federation_id

    while current_id is not None:
        result = await session.execute(
            select(RuleFederationModel).where(RuleFederationModel.id == UUID(current_id))
        )
        node = result.scalar_one_or_none()
        if node is None:
            break
        chain.append(node)
        current_id = str(node.parent_id) if node.parent_id else None

    logger.info("federation_ancestor_chain", federation_id=federation_id, depth=len(chain))
    return chain


async def resolve_effective_rules(
    federation_id: str,
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """Resolve all rules for a federation node including inherited rules.

    Processes the ancestor chain from root to leaf so that child-level
    overrides replace parent rules.

    Args:
        federation_id: UUID of the target federation node.
        session: Async database session.

    Returns:
        List of effective rule dicts with source federation metadata.
    """
    chain = await get_ancestor_chain(federation_id, session)

    # Process from root to leaf (reversed chain)
    effective: dict[str, dict[str, Any]] = {}

    for node in reversed(chain):
        result = await session.execute(
            select(RuleFederationMembershipModel).where(
                RuleFederationMembershipModel.federation_id == node.id
            )
        )
        memberships = list(result.scalars().all())

        for membership in memberships:
            # If this overrides a parent rule, remove the parent
            if membership.override_parent_rule_id:
                effective.pop(str(membership.override_parent_rule_id), None)

            # Fetch the actual rule
            rule_result = await session.execute(
                select(RuleModel).where(RuleModel.id == membership.rule_id)
            )
            rule = rule_result.scalar_one_or_none()
            if rule is not None:
                effective[str(membership.rule_id)] = {
                    "rule_id": str(rule.id),
                    "statement": rule.statement,
                    "modality": rule.modality,
                    "severity": rule.severity,
                    "scope": rule.scope,
                    "tags": rule.tags,
                    "source_federation_id": str(node.id),
                    "source_federation_name": node.name,
                    "overrides": str(membership.override_parent_rule_id)
                    if membership.override_parent_rule_id
                    else None,
                }

    logger.info(
        "federation_effective_rules",
        federation_id=federation_id,
        effective_count=len(effective),
    )
    return list(effective.values())

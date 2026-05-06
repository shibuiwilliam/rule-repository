"""Lineage resolver — walks DERIVES_FROM chains in Neo4j.

Provides multi-level provenance for the Why API endpoint
(``GET /api/v1/rules/{id}/why``).

Tier 2.5 — Why API and Provenance Lineage.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Maximum depth the API will allow, regardless of what the caller requests.
MAX_LINEAGE_DEPTH = 10


async def resolve_lineage(
    rule_id: str,
    session: AsyncSession,
    graph_repo: Any,
    depth: int = 3,
) -> dict[str, Any]:
    """Resolve the DERIVES_FROM lineage chain for a rule.

    Walks up to ``depth`` levels of DERIVES_FROM relationships in Neo4j,
    building a tree structure. If Neo4j is unavailable, returns just the
    rule itself (graceful degradation).

    Args:
        rule_id: The UUID string of the rule to start from.
        session: An async SQLAlchemy session for fetching rule metadata.
        graph_repo: A Neo4j graph repository instance (or ``None``).
        depth: Maximum traversal depth (clamped to ``MAX_LINEAGE_DEPTH``).

    Returns:
        A tree dict with keys ``rule_id``, ``statement``, ``rationale``,
        and ``derived_from`` (a list of child trees).
    """
    depth = min(depth, MAX_LINEAGE_DEPTH)

    # Fetch the root rule from Postgres.
    root_rule = await _fetch_rule_from_db(rule_id, session)
    if root_rule is None:
        return {
            "rule_id": rule_id,
            "statement": "",
            "rationale": "",
            "derived_from": [],
            "error": "Rule not found",
        }

    # If Neo4j is unavailable, return just the root.
    if graph_repo is None:
        logger.warning("lineage_resolver_no_graph", rule_id=rule_id)
        return {
            "rule_id": rule_id,
            "statement": root_rule.get("statement", ""),
            "rationale": root_rule.get("rationale", ""),
            "derived_from": [],
        }

    try:
        tree = await _walk_lineage(rule_id, session, graph_repo, depth, visited=set())
    except Exception as exc:
        logger.warning(
            "lineage_resolver_graph_error",
            rule_id=rule_id,
            error=str(exc),
        )
        tree = {
            "rule_id": rule_id,
            "statement": root_rule.get("statement", ""),
            "rationale": root_rule.get("rationale", ""),
            "derived_from": [],
        }

    return tree


async def _walk_lineage(
    rule_id: str,
    session: AsyncSession,
    graph_repo: Any,
    remaining_depth: int,
    visited: set[str],
) -> dict[str, Any]:
    """Recursively walk DERIVES_FROM relationships.

    Args:
        rule_id: Current rule ID.
        session: SQLAlchemy session.
        graph_repo: Neo4j graph repository.
        remaining_depth: How many more levels to traverse.
        visited: Set of already-visited rule IDs (cycle guard).

    Returns:
        A tree dict for the current node.
    """
    if rule_id in visited:
        return {
            "rule_id": rule_id,
            "statement": "",
            "rationale": "",
            "derived_from": [],
            "note": "cycle detected",
        }

    visited.add(rule_id)

    rule_data = await _fetch_rule_from_db(rule_id, session)
    statement = rule_data.get("statement", "") if rule_data else ""
    rationale = rule_data.get("rationale", "") if rule_data else ""

    node: dict[str, Any] = {
        "rule_id": rule_id,
        "statement": statement,
        "rationale": rationale,
        "derived_from": [],
    }

    if remaining_depth <= 0:
        return node

    # Query Neo4j for DERIVES_FROM targets.
    try:
        neighbors = await graph_repo.get_neighbors(
            UUID(rule_id),
            rel_types=["DERIVES_FROM"],
            depth=1,
        )
    except Exception as exc:
        logger.warning(
            "lineage_walk_graph_error",
            rule_id=rule_id,
            error=str(exc),
        )
        return node

    # Walk each parent in the derivation chain.
    for neighbor in neighbors:
        target_id = neighbor.get("target_id") or neighbor.get("source_id", "")
        if target_id and target_id != rule_id:
            child_tree = await _walk_lineage(
                target_id,
                session,
                graph_repo,
                remaining_depth - 1,
                visited,
            )
            # Include basis_type from the edge property if available
            basis_type = neighbor.get("basis_type")
            if basis_type:
                child_tree["basis_type"] = basis_type
            node["derived_from"].append(child_tree)

    return node


async def _fetch_rule_from_db(
    rule_id: str,
    session: AsyncSession,
) -> dict[str, Any] | None:
    """Fetch minimal rule metadata from Postgres.

    Args:
        rule_id: The rule's UUID string.
        session: An async SQLAlchemy session.

    Returns:
        A dict with ``statement`` and ``rationale``, or ``None``.
    """
    try:
        result = await session.execute(
            text("SELECT id, statement, rationale FROM rules WHERE id = :id"),
            {"id": rule_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return {
            "statement": row["statement"],
            "rationale": row.get("rationale", ""),
        }
    except Exception as exc:
        logger.warning(
            "fetch_rule_from_db_error",
            rule_id=rule_id,
            error=str(exc),
        )
        return None

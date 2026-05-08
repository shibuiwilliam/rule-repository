"""Postgres adjacency-table fallback for Tier 1/2 (no Neo4j).

Stores rule relationships in a ``rule_relationships`` table and uses
recursive CTEs for graph traversal.  This is functionally equivalent
to the Neo4j graph repository but trades traversal performance for
zero additional infrastructure.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class PostgresGraphRepository:
    """Rule relationship management using Postgres adjacency tables.

    Drop-in replacement for ``Neo4jGraphRepository`` in Tier 1/2
    deployments.  Uses the ``rule_relationships`` table with recursive
    CTEs for multi-hop traversal.
    """

    def __init__(self, session: AsyncSession, *, tenant_database: str | None = None) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    async def upsert_rule_node(self, rule_id: UUID, properties: dict[str, Any]) -> None:
        """No-op: rule nodes are rows in the ``rules`` table."""

    async def delete_rule_node(self, rule_id: UUID) -> None:
        """Remove all relationships involving the given rule."""
        await self._session.execute(
            text("DELETE FROM rule_relationships WHERE source_id = :id OR target_id = :id"),
            {"id": str(rule_id)},
        )

    # ------------------------------------------------------------------
    # Relationship CRUD
    # ------------------------------------------------------------------

    async def create_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        rel_type: str,
        *,
        basis_type: str | None = None,
    ) -> None:
        """Create or update a directed relationship between two rules.

        Args:
            source_id: Origin rule UUID.
            target_id: Destination rule UUID.
            rel_type: Relationship label (e.g. ``REFINES``, ``OVERRIDES``).
            basis_type: Optional qualifier for the relationship.
        """
        await self._session.execute(
            text(
                "INSERT INTO rule_relationships (source_id, target_id, rel_type, basis_type) "
                "VALUES (:source_id, :target_id, :rel_type, :basis_type) "
                "ON CONFLICT (source_id, target_id, rel_type) "
                "DO UPDATE SET basis_type = :basis_type"
            ),
            {
                "source_id": str(source_id),
                "target_id": str(target_id),
                "rel_type": rel_type,
                "basis_type": basis_type,
            },
        )

    async def delete_relationship(self, source_id: UUID, target_id: UUID, rel_type: str) -> None:
        """Delete a specific relationship."""
        await self._session.execute(
            text(
                "DELETE FROM rule_relationships "
                "WHERE source_id = :source_id "
                "AND target_id = :target_id "
                "AND rel_type = :rel_type"
            ),
            {
                "source_id": str(source_id),
                "target_id": str(target_id),
                "rel_type": rel_type,
            },
        )

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    async def get_neighbors(
        self,
        rule_id: UUID,
        *,
        rel_types: list[str] | None = None,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        """Return relationships reachable from *rule_id* up to *depth* hops.

        Args:
            rule_id: Starting rule UUID.
            rel_types: Optional filter on relationship types.
            depth: Maximum traversal depth.

        Returns:
            List of relationship dicts with ``source_id``, ``target_id``,
            ``rel_type``, and ``basis_type`` keys.
        """
        type_filter = ""
        params: dict[str, Any] = {"id": str(rule_id), "depth": depth}
        if rel_types:
            type_filter = "AND rel_type = ANY(:rel_types)"
            params["rel_types"] = rel_types

        sql = text(
            f"WITH RECURSIVE graph AS ( "
            f"  SELECT source_id, target_id, rel_type, basis_type, 1 AS hop "
            f"  FROM rule_relationships "
            f"  WHERE (source_id = :id OR target_id = :id) {type_filter} "
            f"  UNION ALL "
            f"  SELECT r.source_id, r.target_id, r.rel_type, r.basis_type, g.hop + 1 "
            f"  FROM rule_relationships r "
            f"  JOIN graph g ON (r.source_id = g.target_id OR r.target_id = g.source_id) "
            f"  WHERE g.hop < :depth {type_filter} "
            f") "
            f"SELECT DISTINCT source_id, target_id, rel_type, basis_type FROM graph"
        )
        result = await self._session.execute(sql, params)
        return [
            {
                "source_id": row[0],
                "target_id": row[1],
                "rel_type": row[2],
                "basis_type": row[3],
            }
            for row in result.fetchall()
        ]

    async def get_subgraph(self, rule_ids: list[UUID], *, depth: int = 1) -> dict[str, Any]:
        """Return a subgraph around the given rule IDs.

        Args:
            rule_ids: Seed rule UUIDs.
            depth: Maximum traversal depth from each seed.

        Returns:
            Dict with ``nodes`` and ``edges`` lists.
        """
        all_neighbors: list[dict[str, Any]] = []
        for rid in rule_ids:
            all_neighbors.extend(await self.get_neighbors(rid, depth=depth))

        node_ids: set[str] = set()
        edges: list[dict[str, str]] = []
        for n in all_neighbors:
            node_ids.add(n["source_id"])
            node_ids.add(n["target_id"])
            edges.append(
                {
                    "source": n["source_id"],
                    "target": n["target_id"],
                    "type": n["rel_type"],
                }
            )

        nodes = [{"id": nid, "properties": {}} for nid in node_ids]
        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------
    # Translation helpers
    # ------------------------------------------------------------------

    async def create_translation_link(
        self,
        source_id: UUID,
        target_id: UUID,
        *,
        source_language: str,
        target_language: str,
    ) -> None:
        """Create a ``TRANSLATES`` relationship between two rule translations."""
        await self.create_relationship(
            source_id,
            target_id,
            "TRANSLATES",
            basis_type=f"{source_language}->{target_language}",
        )

    async def get_translations(self, rule_id: UUID) -> list[dict[str, Any]]:
        """Return all translation links for the given rule.

        Returns:
            List of dicts with ``translated_id``, ``source_language``,
            ``target_language``, and ``props`` keys.
        """
        result = await self._session.execute(
            text(
                "SELECT target_id, basis_type FROM rule_relationships "
                "WHERE source_id = :id AND rel_type = 'TRANSLATES' "
                "UNION ALL "
                "SELECT source_id, basis_type FROM rule_relationships "
                "WHERE target_id = :id AND rel_type = 'TRANSLATES'"
            ),
            {"id": str(rule_id)},
        )
        translations: list[dict[str, Any]] = []
        for row in result.fetchall():
            langs = (row[1] or "->").split("->")
            translations.append(
                {
                    "translated_id": row[0],
                    "source_language": langs[0] if len(langs) > 1 else "",
                    "target_language": langs[1] if len(langs) > 1 else "",
                    "props": {},
                }
            )
        return translations

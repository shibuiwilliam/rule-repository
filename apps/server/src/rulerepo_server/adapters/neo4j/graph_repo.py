"""Neo4j graph repository for rule relationships."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from neo4j import AsyncDriver

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class Neo4jGraphRepository:
    """Manages rule nodes and relationships in Neo4j."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def upsert_rule_node(self, rule_id: UUID, properties: dict[str, Any]) -> None:
        """Create or update a Rule node.

        Args:
            rule_id: The rule's UUID.
            properties: Node properties to set (modality, severity, status, etc.).
        """
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (r:Rule {id: $id})
                SET r += $props
                """,
                id=str(rule_id),
                props=properties,
            )
        logger.info("rule_node_upserted", rule_id=str(rule_id))

    async def delete_rule_node(self, rule_id: UUID) -> None:
        """Delete a Rule node and all its relationships.

        Args:
            rule_id: The rule's UUID.
        """
        async with self._driver.session() as session:
            await session.run(
                "MATCH (r:Rule {id: $id}) DETACH DELETE r",
                id=str(rule_id),
            )

    async def create_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        rel_type: str,
    ) -> None:
        """Create a directed relationship between two Rule nodes.

        Args:
            source_id: Source rule UUID.
            target_id: Target rule UUID.
            rel_type: Relationship type (REFINES, OVERRIDES, etc.).
        """
        query = f"""
            MATCH (a:Rule {{id: $source_id}})
            MATCH (b:Rule {{id: $target_id}})
            MERGE (a)-[:{rel_type}]->(b)
        """
        async with self._driver.session() as session:
            await session.run(
                query,
                source_id=str(source_id),
                target_id=str(target_id),
            )
        logger.info(
            "relationship_created_neo4j",
            source_id=str(source_id),
            target_id=str(target_id),
            type=rel_type,
        )

    async def delete_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        rel_type: str,
    ) -> None:
        """Delete a specific relationship between two Rule nodes.

        Args:
            source_id: Source rule UUID.
            target_id: Target rule UUID.
            rel_type: Relationship type to remove.
        """
        query = f"""
            MATCH (a:Rule {{id: $source_id}})-[r:{rel_type}]->(b:Rule {{id: $target_id}})
            DELETE r
        """
        async with self._driver.session() as session:
            await session.run(
                query,
                source_id=str(source_id),
                target_id=str(target_id),
            )

    async def get_neighbors(
        self,
        rule_id: UUID,
        *,
        rel_types: list[str] | None = None,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        """Get neighboring rules and their relationships.

        Args:
            rule_id: The rule's UUID.
            rel_types: Optional filter on relationship types.
            depth: Maximum traversal depth.

        Returns:
            List of dicts with source, target, and relationship info.
        """
        rel_filter = "|".join(rel_types) if rel_types else ""
        rel_pattern = f"[r:{rel_filter}]" if rel_filter else "[r]"

        query = f"""
            MATCH (a:Rule {{id: $id}})-{rel_pattern}-(b:Rule)
            WHERE length(shortestPath((a)-[*..{depth}]-(b))) <= {depth}
            RETURN a.id AS source_id, type(r) AS rel_type,
                   b.id AS target_id, properties(b) AS target_props
        """
        async with self._driver.session() as session:
            result = await session.run(query, id=str(rule_id))
            records = [record.data() async for record in result]
        return records

    async def get_subgraph(self, rule_ids: list[UUID], *, depth: int = 1) -> dict[str, Any]:
        """Get a subgraph around the given rule IDs.

        Args:
            rule_ids: List of rule UUIDs to center the subgraph on.
            depth: Maximum traversal depth from each node.

        Returns:
            Dictionary with 'nodes' and 'edges' lists.
        """
        ids = [str(rid) for rid in rule_ids]
        query = f"""
            MATCH (a:Rule) WHERE a.id IN $ids
            OPTIONAL MATCH path = (a)-[*1..{depth}]-(b:Rule)
            WITH collect(DISTINCT a) + collect(DISTINCT b) AS allNodes,
                 collect(DISTINCT relationships(path)) AS allRelSets
            UNWIND allNodes AS node
            WITH collect(DISTINCT node) AS nodes, allRelSets
            UNWIND allRelSets AS relSet
            UNWIND relSet AS rel
            WITH nodes, collect(DISTINCT rel) AS rels
            RETURN
                [n IN nodes | {{id: n.id, properties: properties(n)}}] AS nodes,
                [r IN rels | {{
                    source: startNode(r).id,
                    target: endNode(r).id,
                    type: type(r)
                }}] AS edges
        """
        async with self._driver.session() as session:
            result = await session.run(query, ids=ids)
            record = await result.single()
            if record:
                return {"nodes": record["nodes"], "edges": record["edges"]}
            return {"nodes": [], "edges": []}

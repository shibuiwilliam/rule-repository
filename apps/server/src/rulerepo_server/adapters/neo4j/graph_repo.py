"""Neo4j graph repository for rule relationships."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from neo4j import AsyncDriver

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class Neo4jGraphRepository:
    """Manages rule nodes and relationships in Neo4j.

    Supports multi-database tenant isolation via Neo4j 5 multi-database.
    When tenant_database is set, all operations target that database.
    """

    def __init__(self, driver: AsyncDriver, *, tenant_database: str | None = None) -> None:
        self._driver = driver
        self._tenant_database = tenant_database

    def _session_kwargs(self) -> dict:
        """Return kwargs for driver.session() with optional database routing."""
        if self._tenant_database:
            return {"database": self._tenant_database}
        return {}

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
        *,
        basis_type: str | None = None,
    ) -> None:
        """Create a directed relationship between two Rule nodes.

        Args:
            source_id: Source rule UUID.
            target_id: Target rule UUID.
            rel_type: Relationship type (REFINES, OVERRIDES, etc.).
            basis_type: For DERIVES_FROM edges, the provenance type
                (law, regulation, internal_policy, department_rule,
                contract_template). Distinguishes provenance from federation.
        """
        if basis_type and rel_type == "DERIVES_FROM":
            query = f"""
                MATCH (a:Rule {{id: $source_id}})
                MATCH (b:Rule {{id: $target_id}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r.basis_type = $basis_type
            """
            params: dict[str, str] = {
                "source_id": str(source_id),
                "target_id": str(target_id),
                "basis_type": basis_type,
            }
        else:
            query = f"""
                MATCH (a:Rule {{id: $source_id}})
                MATCH (b:Rule {{id: $target_id}})
                MERGE (a)-[:{rel_type}]->(b)
            """
            params = {
                "source_id": str(source_id),
                "target_id": str(target_id),
            }
        async with self._driver.session() as session:
            await session.run(query, **params)
        logger.info(
            "relationship_created_neo4j",
            source_id=str(source_id),
            target_id=str(target_id),
            type=rel_type,
            basis_type=basis_type,
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
                   b.id AS target_id, properties(b) AS target_props,
                   r.basis_type AS basis_type
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

    # --- Polyglot Rules: TRANSLATES relationship (Phase 7c) ---

    async def create_translation_link(
        self,
        source_id: UUID,
        target_id: UUID,
        *,
        source_language: str,
        target_language: str,
    ) -> None:
        """Create a TRANSLATES relationship between two polyglot rule versions.

        Args:
            source_id: The source-language rule UUID.
            target_id: The target-language rule UUID.
            source_language: BCP-47 language tag of the source (e.g., "en").
            target_language: BCP-47 language tag of the target (e.g., "ja").
        """
        query = """
            MATCH (a:Rule {id: $source_id})
            MATCH (b:Rule {id: $target_id})
            MERGE (a)-[r:TRANSLATES]->(b)
            SET r.source_language = $source_lang,
                r.target_language = $target_lang
        """
        async with self._driver.session(**self._session_kwargs()) as session:
            await session.run(
                query,
                source_id=str(source_id),
                target_id=str(target_id),
                source_lang=source_language,
                target_lang=target_language,
            )
        logger.info(
            "translation_link_created",
            source_id=str(source_id),
            target_id=str(target_id),
            languages=f"{source_language}->{target_language}",
        )

    async def get_translations(self, rule_id: UUID) -> list[dict[str, Any]]:
        """Get all translation variants of a rule.

        Args:
            rule_id: The rule's UUID.

        Returns:
            List of dicts with translated rule info and language metadata.
        """
        query = """
            MATCH (a:Rule {id: $id})-[r:TRANSLATES]-(b:Rule)
            RETURN b.id AS translated_id,
                   r.source_language AS source_language,
                   r.target_language AS target_language,
                   properties(b) AS props
        """
        async with self._driver.session(**self._session_kwargs()) as session:
            result = await session.run(query, id=str(rule_id))
            return [record.data() async for record in result]

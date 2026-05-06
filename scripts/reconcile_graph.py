#!/usr/bin/env python3
"""Reconcile Neo4j graph from PostgreSQL source of truth.

Reads all rules and relationships from Postgres and rebuilds Neo4j from scratch.
Postgres is the source of truth; Neo4j is a derived projection.

Usage:
    uv run python scripts/reconcile_graph.py
"""

import asyncio
import os
import sys

# Add the server source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "server", "src"))


async def main() -> None:
    from neo4j import AsyncGraphDatabase
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from rulerepo_server.adapters.postgres.models import RuleModel, RuleRelationshipModel

    database_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://rule:rule@localhost:5432/ruledb")
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "ruledev")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    print("Reconciling Neo4j from PostgreSQL...")

    async with session_factory() as session:
        # Load all rules
        result = await session.execute(select(RuleModel))
        rules = list(result.scalars().all())
        print(f"Found {len(rules)} rules in PostgreSQL")

        # Load all relationships
        result = await session.execute(select(RuleRelationshipModel))
        relationships = list(result.scalars().all())
        print(f"Found {len(relationships)} relationships in PostgreSQL")

    # Clear and rebuild Neo4j
    async with driver.session() as neo_session:
        print("Clearing Neo4j...")
        await neo_session.run("MATCH (n:Rule) DETACH DELETE n")

        print("Creating rule nodes...")
        for rule in rules:
            await neo_session.run(
                """
                CREATE (r:Rule {
                    id: $id,
                    modality: $modality,
                    severity: $severity,
                    status: $status,
                    statement_preview: $preview
                })
                """,
                id=str(rule.id),
                modality=rule.modality,
                severity=rule.severity,
                status=rule.status,
                preview=rule.statement[:200],
            )

        print("Creating relationships...")
        for rel in relationships:
            # DERIVES_FROM edges carry basis_type for provenance distinction
            basis_type = getattr(rel, "basis_type", None)
            if rel.relationship_type == "DERIVES_FROM" and basis_type:
                query = f"""
                    MATCH (a:Rule {{id: $source_id}})
                    MATCH (b:Rule {{id: $target_id}})
                    CREATE (a)-[:{rel.relationship_type} {{basis_type: $basis_type}}]->(b)
                """
                await neo_session.run(
                    query,
                    source_id=str(rel.source_id),
                    target_id=str(rel.target_id),
                    basis_type=basis_type,
                )
            else:
                query = f"""
                    MATCH (a:Rule {{id: $source_id}})
                    MATCH (b:Rule {{id: $target_id}})
                    CREATE (a)-[:{rel.relationship_type}]->(b)
                """
                await neo_session.run(
                    query,
                    source_id=str(rel.source_id),
                    target_id=str(rel.target_id),
                )

        # Recreate constraints
        await neo_session.run("CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (r:Rule) REQUIRE r.id IS UNIQUE")

    await driver.close()
    await engine.dispose()

    print(f"Reconciliation complete: {len(rules)} nodes, {len(relationships)} relationships")


if __name__ == "__main__":
    asyncio.run(main())

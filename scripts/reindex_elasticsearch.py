#!/usr/bin/env python3
"""Reindex Elasticsearch from PostgreSQL source of truth.

The ES equivalent of reconcile_graph.py — reads all rules from Postgres
and re-indexes them in Elasticsearch. Use when:
- ES was temporarily down during rule writes
- ES index was corrupted or deleted
- ES schema changed (new index template applied)

Usage:
    uv run python scripts/reindex_elasticsearch.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "server", "src"))


async def main() -> None:
    from elasticsearch import AsyncElasticsearch
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from rulerepo_server.adapters.postgres.models import RuleModel

    database_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://rule:rule@localhost:5432/ruledb")
    elasticsearch_url = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    es = AsyncElasticsearch(hosts=[elasticsearch_url])

    print("Reindexing Elasticsearch from PostgreSQL...")

    async with session_factory() as session:
        result = await session.execute(select(RuleModel))
        rules = list(result.scalars().all())
        print(f"Found {len(rules)} rules in PostgreSQL")

    indexed = 0
    errors = 0

    for rule in rules:
        es_doc = {
            "rule_id": str(rule.id),
            "project_id": str(rule.project_id) if hasattr(rule, "project_id") and rule.project_id else None,
            "statement": rule.statement,
            "modality": rule.modality,
            "severity": rule.severity,
            "status": rule.status,
            "scope": rule.scope,
            "tags": rule.tags,
            "rationale": rule.rationale,
            "embedding": rule.embedding,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        }

        # Extract effective_period dates if available
        ep = rule.effective_period if isinstance(rule.effective_period, dict) else {}
        es_doc["effective_from"] = ep.get("valid_from")
        es_doc["effective_until"] = ep.get("valid_until")

        try:
            await es.index(index="rules", id=str(rule.id), document=es_doc)
            indexed += 1
        except Exception as exc:
            print(f"  Error indexing {rule.id}: {exc}")
            errors += 1

    await es.close()
    await engine.dispose()

    print(f"Reindex complete: {indexed} indexed, {errors} errors")


if __name__ == "__main__":
    asyncio.run(main())

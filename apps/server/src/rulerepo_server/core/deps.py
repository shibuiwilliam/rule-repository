"""FastAPI dependency injection factories.

Provides configured service instances for API route handlers.
Tier-aware: uses Postgres fallbacks when Elasticsearch or Neo4j
are disabled.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.feature_flags import get_feature_flags
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.rule_service import RuleService
from rulerepo_server.services.search import SearchService

_logger = get_logger(__name__)


async def get_search_index(
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Provide the appropriate search index adapter for the current tier.

    Tier 2/3: ``ElasticsearchRuleIndex``.
    Tier 1:   ``PostgresFTSIndex`` (Postgres full-text search fallback).
    """
    flags = get_feature_flags()
    if flags.elasticsearch_enabled:
        from rulerepo_server.adapters.elasticsearch.client import get_es_client
        from rulerepo_server.adapters.elasticsearch.rule_index import ElasticsearchRuleIndex

        return ElasticsearchRuleIndex(get_es_client())

    from rulerepo_server.adapters.search.postgres_fts import PostgresFTSIndex

    return PostgresFTSIndex(session)


async def get_graph_repo(
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Provide the appropriate graph repository for the current tier.

    Tier 3:   ``Neo4jGraphRepository``.
    Tier 1/2: ``PostgresGraphRepository`` (adjacency table fallback).
    """
    flags = get_feature_flags()
    if flags.neo4j_enabled:
        from rulerepo_server.adapters.neo4j.client import get_neo4j_driver
        from rulerepo_server.adapters.neo4j.graph_repo import Neo4jGraphRepository

        return Neo4jGraphRepository(get_neo4j_driver())

    from rulerepo_server.adapters.graph.postgres_adjacency import PostgresGraphRepository

    return PostgresGraphRepository(session)


def _get_optional_gemini() -> Any | None:
    """Attempt to get Gemini client, returning None if unavailable.

    Logs a warning on failure rather than silently swallowing the error.
    """
    try:
        from rulerepo_server.adapters.gemini.client import get_gemini_client

        return get_gemini_client()
    except Exception as exc:
        _logger.warning("gemini_client_unavailable", error=str(exc))
        return None


async def get_rule_service(
    session: AsyncSession = Depends(get_db_session),
    search_index: Any = Depends(get_search_index),
    graph_repo: Any = Depends(get_graph_repo),
) -> RuleService:
    """Provide a RuleService wired to all data stores."""
    return RuleService(session, search_index, graph_repo, _get_optional_gemini())


async def get_search_service(
    session: AsyncSession = Depends(get_db_session),
    search_index: Any = Depends(get_search_index),
) -> SearchService:
    """Provide a SearchService wired to the appropriate search adapter."""
    return SearchService(session, search_index, _get_optional_gemini())

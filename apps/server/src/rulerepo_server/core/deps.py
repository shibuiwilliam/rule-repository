"""FastAPI dependency injection factories.

Provides configured service instances for API route handlers.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.elasticsearch.client import get_es_client
from rulerepo_server.adapters.elasticsearch.rule_index import ElasticsearchRuleIndex
from rulerepo_server.adapters.gemini.client import get_gemini_client
from rulerepo_server.adapters.neo4j.client import get_neo4j_driver
from rulerepo_server.adapters.neo4j.graph_repo import Neo4jGraphRepository
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.rule_service import RuleService
from rulerepo_server.services.search import SearchService

_logger = get_logger(__name__)


async def get_es_index() -> ElasticsearchRuleIndex:
    """Provide an ElasticsearchRuleIndex instance."""
    return ElasticsearchRuleIndex(get_es_client())


async def get_graph_repo() -> Neo4jGraphRepository:
    """Provide a Neo4jGraphRepository instance."""
    return Neo4jGraphRepository(get_neo4j_driver())


def _get_optional_gemini():  # noqa: ANN202
    """Attempt to get Gemini client, returning None if unavailable.

    Logs a warning on failure rather than silently swallowing the error.
    """
    try:
        return get_gemini_client()
    except Exception as exc:
        _logger.warning("gemini_client_unavailable", error=str(exc))
        return None


async def get_rule_service(
    session: AsyncSession = Depends(get_db_session),
    es_index: ElasticsearchRuleIndex = Depends(get_es_index),
    graph_repo: Neo4jGraphRepository = Depends(get_graph_repo),
) -> RuleService:
    """Provide a RuleService wired to all data stores."""
    return RuleService(session, es_index, graph_repo, _get_optional_gemini())


async def get_search_service(
    session: AsyncSession = Depends(get_db_session),
    es_index: ElasticsearchRuleIndex = Depends(get_es_index),
) -> SearchService:
    """Provide a SearchService wired to ES and Postgres."""
    return SearchService(session, es_index, _get_optional_gemini())

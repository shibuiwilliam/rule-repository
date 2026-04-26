"""Elasticsearch async client management."""

from elasticsearch import AsyncElasticsearch

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

_client: AsyncElasticsearch | None = None


async def create_es_client() -> AsyncElasticsearch:
    """Create and store the async Elasticsearch client."""
    global _client  # noqa: PLW0603
    settings = get_settings()
    _client = AsyncElasticsearch(
        hosts=[settings.elasticsearch_url],
        request_timeout=30,
        max_retries=3,
        retry_on_timeout=True,
    )
    logger.info("elasticsearch_client_created", url=settings.elasticsearch_url)
    return _client


def get_es_client() -> AsyncElasticsearch:
    """Return the current Elasticsearch client."""
    if _client is None:
        msg = "Elasticsearch client not initialized. Call create_es_client() first."
        raise RuntimeError(msg)
    return _client


async def close_es_client() -> None:
    """Close the Elasticsearch client."""
    global _client  # noqa: PLW0603
    if _client is not None:
        await _client.close()
        _client = None
        logger.info("elasticsearch_client_closed")

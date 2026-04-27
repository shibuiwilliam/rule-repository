"""Neo4j async driver management."""

from neo4j import AsyncDriver, AsyncGraphDatabase

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

_driver: AsyncDriver | None = None


async def create_neo4j_driver() -> AsyncDriver:
    """Create and store the async Neo4j driver."""
    global _driver
    settings = get_settings()
    _driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    # Verify connectivity
    try:
        await _driver.verify_connectivity()
        logger.info("neo4j_driver_created", uri=settings.neo4j_uri)
    except Exception as exc:
        logger.warning("neo4j_connectivity_check_failed", error=str(exc))
    return _driver


def get_neo4j_driver() -> AsyncDriver:
    """Return the current Neo4j driver."""
    if _driver is None:
        msg = "Neo4j driver not initialized. Call create_neo4j_driver() first."
        raise RuntimeError(msg)
    return _driver


async def close_neo4j_driver() -> None:
    """Close the Neo4j driver."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
        logger.info("neo4j_driver_closed")

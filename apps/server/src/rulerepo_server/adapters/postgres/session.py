"""PostgreSQL async session management using SQLAlchemy."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine() -> AsyncEngine:
    """Create and store the async SQLAlchemy engine."""
    global _engine, _session_factory  # noqa: PLW0603
    settings = get_settings()
    _engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info("postgres_engine_created", url=settings.database_url.split("@")[-1])
    return _engine


def get_engine() -> AsyncEngine:
    """Return the current async engine, raising if not initialized."""
    if _engine is None:
        msg = "Database engine not initialized. Call create_engine() first."
        raise RuntimeError(msg)
    return _engine


async def dispose_engine() -> None:
    """Dispose the async engine and release all connections."""
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("postgres_engine_disposed")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session for FastAPI dependency injection."""
    if _session_factory is None:
        msg = "Session factory not initialized. Call create_engine() first."
        raise RuntimeError(msg)
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

"""Tier-aware feature flags derived from environment variables.

Provides runtime detection of which optional infrastructure components
(Elasticsearch, Neo4j, Redis, MCP) are available, and derives the
effective deployment tier from those flags.
"""

from __future__ import annotations

from functools import lru_cache

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class FeatureFlags:
    """Runtime feature detection based on ``*_ENABLED`` env vars.

    Tier derivation:
        - Tier 1: Postgres only (no ES, no Neo4j, no Redis).
        - Tier 2: Postgres + Elasticsearch + Redis.
        - Tier 3: Full stack (+ Neo4j, MCP).
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.elasticsearch_enabled: bool = getattr(settings, "elasticsearch_enabled", False)
        self.neo4j_enabled: bool = getattr(settings, "neo4j_enabled", False)
        self.redis_enabled: bool = getattr(settings, "redis_enabled", False)
        self.mcp_enabled: bool = getattr(settings, "mcp_enabled", False)

    @property
    def tier(self) -> int:
        """Return the effective deployment tier (1, 2, or 3)."""
        if self.neo4j_enabled:
            return 3
        if self.elasticsearch_enabled or self.redis_enabled:
            return 2
        return 1

    def log_tier_info(self) -> None:
        """Log the detected tier and enabled components."""
        logger.info(
            "tier_detected",
            tier=self.tier,
            elasticsearch=self.elasticsearch_enabled,
            neo4j=self.neo4j_enabled,
            redis=self.redis_enabled,
            mcp=self.mcp_enabled,
        )


@lru_cache
def get_feature_flags() -> FeatureFlags:
    """Return cached feature flags singleton."""
    return FeatureFlags()

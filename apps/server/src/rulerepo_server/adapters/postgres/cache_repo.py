"""LLM response cache repository — stores and retrieves cached LLM outputs.

Implements CLAUDE.md §9.5: Cache LLM responses by hash(inputs + model + prompt_version).
Invalidation happens when rules are revised (called from RuleService.update_rule).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import LLMCacheModel
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


def compute_cache_key(inputs: str, model_id: str, prompt_version: str) -> str:
    """Compute a deterministic cache key from inputs, model, and prompt version.

    Args:
        inputs: The serialized input content.
        model_id: The model identifier.
        prompt_version: A hash or version string for the prompt.

    Returns:
        A hex-encoded SHA-256 hash string.
    """
    payload = f"{model_id}:{prompt_version}:{inputs}"
    return hashlib.sha256(payload.encode()).hexdigest()


class LLMCacheRepository:
    """Cache for LLM responses keyed by hash(inputs + model + prompt_version)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, cache_key: str) -> dict[str, Any] | None:
        """Retrieve a cached response by key.

        Args:
            cache_key: The SHA-256 hash key.

        Returns:
            The cached response dict, or None if not found.
        """
        result = await self._session.execute(
            select(LLMCacheModel).where(LLMCacheModel.cache_key == cache_key)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        logger.debug("llm_cache_hit", cache_key=cache_key[:16])
        return model.response  # type: ignore[return-value]

    async def store(
        self,
        *,
        cache_key: str,
        model_id: str,
        prompt_version: str,
        inputs_hash: str,
        response: dict[str, Any],
        latency_ms: int,
    ) -> None:
        """Store an LLM response in the cache.

        Args:
            cache_key: The computed cache key.
            model_id: Which model produced the response.
            prompt_version: Hash or version of the prompt used.
            inputs_hash: Hash of the raw inputs for audit.
            response: The LLM response data to cache.
            latency_ms: How long the LLM call took in milliseconds.
        """
        model = LLMCacheModel(
            id=uuid4(),
            cache_key=cache_key,
            model_id=model_id,
            prompt_version=prompt_version,
            inputs_hash=inputs_hash,
            response=response,
            latency_ms=latency_ms,
            created_at=datetime.now(tz=UTC),
        )
        await self._session.merge(model)
        await self._session.flush()
        logger.debug("llm_cache_stored", cache_key=cache_key[:16], model_id=model_id)

    async def invalidate_all(self) -> int:
        """Invalidate all cached responses (e.g., after a rule revision).

        Returns:
            Number of entries deleted.
        """
        result = await self._session.execute(delete(LLMCacheModel))
        count = result.rowcount  # type: ignore[assignment]
        if count:
            logger.info("llm_cache_invalidated", entries_deleted=count)
        return count  # type: ignore[return-value]

    async def invalidate_by_model(self, model_id: str) -> int:
        """Invalidate cached responses for a specific model.

        Args:
            model_id: The model whose cache entries to remove.

        Returns:
            Number of entries deleted.
        """
        result = await self._session.execute(
            delete(LLMCacheModel).where(LLMCacheModel.model_id == model_id)
        )
        return result.rowcount  # type: ignore[return-value]

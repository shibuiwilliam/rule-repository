"""In-memory fact cache with TTL expiry.

Suitable for development and single-process deployments.  Production
deployments should swap in a Redis-backed implementation sharing the
same interface.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.fact import Fact

logger = get_logger(__name__)


@dataclass
class _CacheEntry:
    """Internal wrapper that stores a fact alongside its expiry."""

    fact: Fact
    expires_at: datetime | None


class FactCache:
    """Tenant-scoped, TTL-aware in-memory cache for resolved facts.

    Cache keys are derived from ``(fact_key, context_hash, tenant_id)``
    to guarantee tenant isolation.
    """

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(
        self,
        key: str,
        context_hash: str,
        tenant_id: str,
    ) -> Fact | None:
        """Retrieve a cached fact if present and not expired.

        Args:
            key: The canonical fact key.
            context_hash: Hash of the resolution context.
            tenant_id: Tenant identifier for isolation.

        Returns:
            The cached ``Fact`` or ``None``.
        """
        cache_key = self._make_key(key, context_hash, tenant_id)
        entry = self._store.get(cache_key)
        if entry is None:
            return None

        if entry.expires_at is not None and datetime.now(tz=UTC) > entry.expires_at:
            del self._store[cache_key]
            logger.debug("fact_cache_expired", key=key, tenant_id=tenant_id)
            return None

        logger.debug("fact_cache_hit", key=key, tenant_id=tenant_id)
        return entry.fact

    async def put(
        self,
        key: str,
        context_hash: str,
        tenant_id: str,
        fact: Fact,
    ) -> None:
        """Store a resolved fact in the cache.

        The entry's TTL is derived from ``fact.ttl_seconds``.  If the
        fact has no TTL, the entry is stored without expiry.

        Args:
            key: The canonical fact key.
            context_hash: Hash of the resolution context.
            tenant_id: Tenant identifier for isolation.
            fact: The resolved fact to cache.
        """
        expires_at: datetime | None = None
        if fact.ttl_seconds is not None:
            expires_at = datetime.now(tz=UTC) + timedelta(seconds=fact.ttl_seconds)

        cache_key = self._make_key(key, context_hash, tenant_id)
        self._store[cache_key] = _CacheEntry(fact=fact, expires_at=expires_at)
        logger.debug(
            "fact_cache_put",
            key=key,
            tenant_id=tenant_id,
            ttl=fact.ttl_seconds,
        )

    async def invalidate(
        self,
        key: str,
        context_hash: str | None,
        tenant_id: str,
    ) -> None:
        """Remove cached entries.

        Args:
            key: The fact key to invalidate.
            context_hash: If provided, invalidate only the specific
                context variant.  If ``None``, invalidate all cached
                entries for *key* within the tenant.
            tenant_id: Tenant identifier for isolation.
        """
        if context_hash is not None:
            cache_key = self._make_key(key, context_hash, tenant_id)
            self._store.pop(cache_key, None)
            logger.debug("fact_cache_invalidated", key=key, tenant_id=tenant_id)
        else:
            # Prefix scan — remove all context variants for this key+tenant.
            prefix = f"{tenant_id}:{key}:"
            to_remove = [k for k in self._store if k.startswith(prefix)]
            for k in to_remove:
                del self._store[k]
            logger.debug(
                "fact_cache_invalidated_all",
                key=key,
                tenant_id=tenant_id,
                count=len(to_remove),
            )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(key: str, context_hash: str, tenant_id: str) -> str:
        """Build a composite cache key ensuring tenant isolation."""
        return f"{tenant_id}:{key}:{context_hash}"

    @staticmethod
    def hash_context(context: dict) -> str:
        """Produce a stable hash of a resolution context dict.

        Args:
            context: The context dict supplied by the caller.

        Returns:
            Hex-encoded SHA-256 digest.
        """
        import json

        canonical = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

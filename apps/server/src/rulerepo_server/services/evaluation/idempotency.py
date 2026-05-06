"""Idempotency-Key middleware for evaluation requests.

Stores (idempotency_key, request_hash) → evaluation_id mappings with a
configurable TTL (default 24 hours).  Ensures that:

* Same key + same payload hash → cached evaluation_id is returned.
* Same key + different payload hash → ``ConflictError`` (HTTP 409).

The service supports two backends:

1. **Redis** - used when a valid ``redis_url`` is provided and the
   ``redis`` package is available.
2. **In-memory dict** - used as a fallback for tests and environments
   without Redis.  TTL expiry is simulated via stored timestamps.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass

import structlog

from rulerepo_server.core.errors import ConflictError

logger = structlog.get_logger(__name__)

# Default TTL in seconds (24 hours).
DEFAULT_TTL_SECONDS: int = 24 * 60 * 60


def compute_request_hash(payload: dict) -> str:
    """Compute a deterministic SHA-256 hash of *payload*.

    The payload is serialized with sorted keys and no extra whitespace so
    that logically identical payloads always produce the same hash.

    Args:
        payload: The evaluation request payload.

    Returns:
        A hex-encoded SHA-256 digest string.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class _MemoryEntry:
    """An entry in the in-memory idempotency store."""

    request_hash: str
    evaluation_id: str
    expires_at: float


class IdempotencyService:
    """Idempotency cache backed by Redis or an in-memory fallback.

    Args:
        redis_url: Redis connection URL.  When *None* or when the
            ``redis`` package is unavailable, the service falls back to
            an in-memory dictionary.
        ttl_seconds: Time-to-live for cached entries.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._redis: object | None = None
        self._memory: dict[str, _MemoryEntry] = {}

        if redis_url:
            try:
                import redis as redis_lib

                self._redis = redis_lib.Redis.from_url(redis_url, decode_responses=True)
                logger.info("idempotency_service.redis_connected", redis_url=redis_url)
            except Exception:
                logger.warning(
                    "idempotency_service.redis_unavailable",
                    redis_url=redis_url,
                )
                self._redis = None

        if self._redis is None:
            logger.info("idempotency_service.using_memory_backend")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check(self, key: str, request_hash: str) -> str | None:
        """Look up a cached evaluation for the given idempotency key.

        Args:
            key: The idempotency key from the request header.
            request_hash: SHA-256 hash of the request payload.

        Returns:
            The cached ``evaluation_id`` if the key exists and the
            payload hash matches, or *None* if no entry is found.

        Raises:
            ConflictError: If the key exists but the payload hash differs
                (same key reused with a different request body).
        """
        if self._redis is not None:
            return self._check_redis(key, request_hash)
        return self._check_memory(key, request_hash)

    async def store(self, key: str, request_hash: str, evaluation_id: str) -> None:
        """Store an idempotency mapping.

        Args:
            key: The idempotency key.
            request_hash: SHA-256 hash of the request payload.
            evaluation_id: The evaluation ID to cache.
        """
        if self._redis is not None:
            self._store_redis(key, request_hash, evaluation_id)
        else:
            self._store_memory(key, request_hash, evaluation_id)

        logger.info(
            "idempotency_service.stored",
            idempotency_key=key,
            evaluation_id=evaluation_id,
        )

    # ------------------------------------------------------------------
    # Redis backend
    # ------------------------------------------------------------------

    def _redis_key(self, key: str) -> str:
        return f"idempotency:{key}"

    def _check_redis(self, key: str, request_hash: str) -> str | None:
        import redis as redis_lib

        assert isinstance(self._redis, redis_lib.Redis)
        rkey = self._redis_key(key)
        data = self._redis.hgetall(rkey)
        if not data:
            return None

        stored_hash = data.get("request_hash", "")
        if stored_hash != request_hash:
            raise ConflictError(f"Idempotency key '{key}' already used with a different request payload.")
        return data.get("evaluation_id")

    def _store_redis(self, key: str, request_hash: str, evaluation_id: str) -> None:
        import redis as redis_lib

        assert isinstance(self._redis, redis_lib.Redis)
        rkey = self._redis_key(key)
        self._redis.hset(
            rkey,
            mapping={
                "request_hash": request_hash,
                "evaluation_id": evaluation_id,
            },
        )
        self._redis.expire(rkey, self._ttl_seconds)

    # ------------------------------------------------------------------
    # In-memory backend
    # ------------------------------------------------------------------

    def _check_memory(self, key: str, request_hash: str) -> str | None:
        entry = self._memory.get(key)
        if entry is None:
            return None

        # Honour TTL.
        if time.monotonic() > entry.expires_at:
            del self._memory[key]
            return None

        if entry.request_hash != request_hash:
            raise ConflictError(f"Idempotency key '{key}' already used with a different request payload.")
        return entry.evaluation_id

    def _store_memory(self, key: str, request_hash: str, evaluation_id: str) -> None:
        self._memory[key] = _MemoryEntry(
            request_hash=request_hash,
            evaluation_id=evaluation_id,
            expires_at=time.monotonic() + self._ttl_seconds,
        )

"""Unit tests for the IdempotencyService (in-memory backend)."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from rulerepo_server.core.errors import ConflictError
from rulerepo_server.services.evaluation.idempotency import (
    IdempotencyService,
    compute_request_hash,
)

# ---------------------------------------------------------------------------
# compute_request_hash
# ---------------------------------------------------------------------------


class TestComputeRequestHash:
    """Tests for the deterministic payload hashing function."""

    def test_same_payload_same_hash(self) -> None:
        payload = {"foo": "bar", "num": 42}
        assert compute_request_hash(payload) == compute_request_hash(payload)

    def test_key_order_does_not_matter(self) -> None:
        a = {"z": 1, "a": 2}
        b = {"a": 2, "z": 1}
        assert compute_request_hash(a) == compute_request_hash(b)

    def test_different_payloads_different_hash(self) -> None:
        a = {"action": "evaluate", "code": "x = 1"}
        b = {"action": "evaluate", "code": "x = 2"}
        assert compute_request_hash(a) != compute_request_hash(b)

    def test_returns_hex_sha256(self) -> None:
        h = compute_request_hash({"k": "v"})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# IdempotencyService (in-memory)
# ---------------------------------------------------------------------------


@pytest.fixture()
def service() -> IdempotencyService:
    """An IdempotencyService using the in-memory backend."""
    return IdempotencyService(redis_url=None, ttl_seconds=60)


class TestIdempotencyServiceMemory:
    """Tests for the in-memory idempotency backend."""

    @pytest.mark.asyncio()
    async def test_check_returns_none_for_unknown_key(self, service: IdempotencyService) -> None:
        result = await service.check("unknown-key", "somehash")
        assert result is None

    @pytest.mark.asyncio()
    async def test_store_and_check_same_hash(self, service: IdempotencyService) -> None:
        key = "req-001"
        req_hash = compute_request_hash({"diff": "hello"})
        eval_id = "eval-abc-123"

        await service.store(key, req_hash, eval_id)
        result = await service.check(key, req_hash)
        assert result == eval_id

    @pytest.mark.asyncio()
    async def test_same_key_different_hash_raises_conflict(self, service: IdempotencyService) -> None:
        key = "req-002"
        hash_a = compute_request_hash({"diff": "version-1"})
        hash_b = compute_request_hash({"diff": "version-2"})
        eval_id = "eval-xyz-789"

        await service.store(key, hash_a, eval_id)

        with pytest.raises(ConflictError) as exc_info:
            await service.check(key, hash_b)

        assert "already used with a different request payload" in str(exc_info.value)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio()
    async def test_expired_entry_returns_none(self) -> None:
        """An entry whose TTL has elapsed is treated as absent."""
        svc = IdempotencyService(redis_url=None, ttl_seconds=1)
        key = "req-003"
        req_hash = compute_request_hash({"data": "abc"})

        await svc.store(key, req_hash, "eval-old")

        # Simulate time passing beyond the TTL by patching monotonic.
        original_monotonic = time.monotonic
        with patch(
            "rulerepo_server.services.evaluation.idempotency.time.monotonic",
            side_effect=lambda: original_monotonic() + 2,
        ):
            result = await svc.check(key, req_hash)

        assert result is None

    @pytest.mark.asyncio()
    async def test_expired_entry_allows_reuse_of_key(self) -> None:
        """After expiry the same key can be stored with a new hash."""
        svc = IdempotencyService(redis_url=None, ttl_seconds=1)
        key = "req-004"
        hash_a = compute_request_hash({"v": 1})
        hash_b = compute_request_hash({"v": 2})

        await svc.store(key, hash_a, "eval-1")

        original_monotonic = time.monotonic
        with patch(
            "rulerepo_server.services.evaluation.idempotency.time.monotonic",
            side_effect=lambda: original_monotonic() + 2,
        ):
            # Key should be expired — check returns None.
            assert await svc.check(key, hash_b) is None

        # Now we can store with a different hash without conflict.
        await svc.store(key, hash_b, "eval-2")
        result = await svc.check(key, hash_b)
        assert result == "eval-2"

    @pytest.mark.asyncio()
    async def test_multiple_keys_independent(self, service: IdempotencyService) -> None:
        """Different idempotency keys are independent of each other."""
        hash_1 = compute_request_hash({"x": 1})
        hash_2 = compute_request_hash({"x": 2})

        await service.store("key-a", hash_1, "eval-a")
        await service.store("key-b", hash_2, "eval-b")

        assert await service.check("key-a", hash_1) == "eval-a"
        assert await service.check("key-b", hash_2) == "eval-b"

    @pytest.mark.asyncio()
    async def test_overwrite_same_key_same_hash(self, service: IdempotencyService) -> None:
        """Storing the same key+hash again updates the evaluation_id."""
        key = "req-005"
        req_hash = compute_request_hash({"q": "test"})

        await service.store(key, req_hash, "eval-first")
        await service.store(key, req_hash, "eval-second")

        result = await service.check(key, req_hash)
        assert result == "eval-second"

"""Unit tests for the Fact Store (workstream 7c).

Tests fact resolution, caching, provider registry, and tenant scoping.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from rulerepo_server.domain.fact import Fact, FactResolutionResult, FactSchema, FactStatus
from rulerepo_server.services.fact_store.cache import FactCache
from rulerepo_server.services.fact_store.registry import FactProviderRegistry
from rulerepo_server.services.fact_store.service import FactStore

# ---------------------------------------------------------------------------
# Test fixtures — mock provider
# ---------------------------------------------------------------------------


class MockProvider:
    """A simple mock FactProvider for testing."""

    name = "mock_provider"
    domain = "test"

    def __init__(self, facts: dict[str, Any] | None = None) -> None:
        self._facts = facts or {}
        self._call_count = 0

    async def supported_facts(self) -> list[FactSchema]:
        return [
            FactSchema(
                key=k,
                description=f"Mock fact: {k}",
                value_type="string",
                required_context_keys=[],
                domain="test",
            )
            for k in self._facts
        ]

    async def fetch(self, key: str, context: dict) -> Fact | None:
        self._call_count += 1
        if key in self._facts:
            return Fact(
                key=key,
                value=self._facts[key],
                status=FactStatus.RESOLVED,
                source_provider=self.name,
                resolved_at=datetime.now(tz=UTC),
                ttl_seconds=60,
                metadata={},
            )
        return None

    async def health_check(self) -> bool:
        return True


class FailingProvider:
    """Provider that always raises."""

    name = "failing_provider"
    domain = "test"

    async def supported_facts(self) -> list[FactSchema]:
        return [
            FactSchema(
                key="will_fail",
                description="Always fails",
                value_type="string",
                required_context_keys=[],
                domain="test",
            )
        ]

    async def fetch(self, key: str, context: dict) -> Fact | None:
        msg = "Provider unavailable"
        raise ConnectionError(msg)

    async def health_check(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Domain model tests
# ---------------------------------------------------------------------------


class TestFactDomain:
    def test_fact_creation(self) -> None:
        fact = Fact(
            key="employee_grade",
            value="senior",
            status=FactStatus.RESOLVED,
            source_provider="test",
            resolved_at=datetime.now(tz=UTC),
            ttl_seconds=300,
            metadata={},
        )
        assert fact.key == "employee_grade"
        assert fact.value == "senior"
        assert fact.status == FactStatus.RESOLVED

    def test_fact_status_values(self) -> None:
        assert FactStatus.RESOLVED == "resolved"
        assert FactStatus.NOT_FOUND == "not_found"
        assert FactStatus.ERROR == "error"
        assert FactStatus.CACHED == "cached"

    def test_fact_schema(self) -> None:
        schema = FactSchema(
            key="36_agreement_status",
            description="Status of 36-agreement",
            value_type="boolean",
            required_context_keys=["employee_id", "month"],
            domain="hr",
        )
        assert schema.key == "36_agreement_status"
        assert "employee_id" in schema.required_context_keys

    def test_resolution_result(self) -> None:
        result = FactResolutionResult(
            requested=["a", "b", "c"],
            resolved={
                "a": Fact(
                    key="a",
                    value=1,
                    status=FactStatus.RESOLVED,
                    source_provider="test",
                    resolved_at=datetime.now(tz=UTC),
                    ttl_seconds=None,
                    metadata={},
                )
            },
            missing=["b"],
            errors={"c": "provider error"},
        )
        assert len(result.resolved) == 1
        assert "b" in result.missing
        assert "c" in result.errors


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestFactProviderRegistry:
    @pytest.mark.asyncio
    async def test_register_and_lookup(self) -> None:
        registry = FactProviderRegistry()
        provider = MockProvider({"employee_grade": "senior"})
        registry.register(provider)
        found = await registry.get_provider("employee_grade")
        assert found is not None
        assert found.name == "mock_provider"

    @pytest.mark.asyncio
    async def test_lookup_missing_key(self) -> None:
        registry = FactProviderRegistry()
        assert await registry.get_provider("nonexistent") is None

    @pytest.mark.asyncio
    async def test_list_providers(self) -> None:
        registry = FactProviderRegistry()
        p1 = MockProvider({"fact_a": 1})
        p2 = MockProvider({"fact_b": 2})
        p2.name = "mock_provider_2"
        registry.register(p1)
        registry.register(p2)
        providers = await registry.list_providers()
        assert len(providers) >= 2


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------


class TestFactCache:
    @pytest.mark.asyncio
    async def test_put_and_get(self) -> None:
        cache = FactCache()
        fact = Fact(
            key="grade",
            value="senior",
            status=FactStatus.RESOLVED,
            source_provider="test",
            resolved_at=datetime.now(tz=UTC),
            ttl_seconds=300,
            metadata={},
        )
        await cache.put("grade", "ctx_hash_1", "tenant_1", fact)
        retrieved = await cache.get("grade", "ctx_hash_1", "tenant_1")
        assert retrieved is not None
        assert retrieved.value == "senior"

    @pytest.mark.asyncio
    async def test_tenant_isolation(self) -> None:
        cache = FactCache()
        fact = Fact(
            key="grade",
            value="senior",
            status=FactStatus.RESOLVED,
            source_provider="test",
            resolved_at=datetime.now(tz=UTC),
            ttl_seconds=300,
            metadata={},
        )
        await cache.put("grade", "ctx_hash", "tenant_1", fact)
        result = await cache.get("grade", "ctx_hash", "tenant_2")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate(self) -> None:
        cache = FactCache()
        fact = Fact(
            key="grade",
            value="senior",
            status=FactStatus.RESOLVED,
            source_provider="test",
            resolved_at=datetime.now(tz=UTC),
            ttl_seconds=300,
            metadata={},
        )
        await cache.put("grade", "ctx_hash", "tenant_1", fact)
        await cache.invalidate("grade", "ctx_hash", "tenant_1")
        result = await cache.get("grade", "ctx_hash", "tenant_1")
        assert result is None


# ---------------------------------------------------------------------------
# FactStore service tests
# ---------------------------------------------------------------------------


class TestFactStore:
    def _make_store(self, providers: list | None = None) -> FactStore:
        registry = FactProviderRegistry()
        for p in providers or []:
            registry.register(p)
        return FactStore(registry=registry)

    @pytest.mark.asyncio
    async def test_resolve_single_fact(self) -> None:
        provider = MockProvider({"employee_grade": "senior"})
        store = self._make_store([provider])
        result = await store.resolve(["employee_grade"], {}, "tenant_1")
        assert "employee_grade" in result.resolved
        assert result.resolved["employee_grade"].value == "senior"
        assert len(result.missing) == 0

    @pytest.mark.asyncio
    async def test_resolve_missing_fact(self) -> None:
        provider = MockProvider({"employee_grade": "senior"})
        store = self._make_store([provider])
        result = await store.resolve(["nonexistent_fact"], {}, "tenant_1")
        assert "nonexistent_fact" in result.missing

    @pytest.mark.asyncio
    async def test_resolve_multiple_facts(self) -> None:
        provider = MockProvider(
            {
                "employee_grade": "senior",
                "employee_department": "engineering",
            }
        )
        store = self._make_store([provider])
        result = await store.resolve(
            ["employee_grade", "employee_department"],
            {},
            "tenant_1",
        )
        assert len(result.resolved) == 2

    @pytest.mark.asyncio
    async def test_provider_error_captured(self) -> None:
        store = self._make_store([FailingProvider()])
        result = await store.resolve(["will_fail"], {}, "tenant_1")
        assert "will_fail" in result.errors

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        provider = MockProvider({"a": 1})
        store = self._make_store([provider])
        health = await store.health_check()
        assert "mock_provider" in health
        assert health["mock_provider"] is True

    @pytest.mark.asyncio
    async def test_caching_reduces_calls(self) -> None:
        provider = MockProvider({"employee_grade": "senior"})
        store = self._make_store([provider])
        # First call
        await store.resolve(["employee_grade"], {}, "tenant_1")
        first_count = provider._call_count
        # Second call should hit cache
        await store.resolve(["employee_grade"], {}, "tenant_1")
        assert provider._call_count == first_count  # no additional call

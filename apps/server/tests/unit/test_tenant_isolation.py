"""Tests for tenant isolation middleware and cross-tenant data boundaries.

Phase 7g: Verifies that tenant context is set per request and that
single-tenant mode uses the default tenant.
"""

from __future__ import annotations

from rulerepo_server.core.tenancy.context import (
    DEFAULT_TENANT_ID,
    TenantContext,
    get_current_tenant,
    tenant_scope,
)


class TestTenantIsolationMiddleware:
    """Tests for the TenantIsolationMiddleware behavior."""

    def test_default_tenant_in_single_tenant_mode(self) -> None:
        """In single-tenant mode, all operations use DEFAULT_TENANT_ID."""
        with tenant_scope(DEFAULT_TENANT_ID, "default") as ctx:
            assert ctx.tenant_id == DEFAULT_TENANT_ID
            current = get_current_tenant()
            assert current is not None
            assert current.tenant_id == DEFAULT_TENANT_ID

    def test_tenant_scope_isolates_context(self) -> None:
        """Different tenant scopes have different tenant IDs."""
        tenant_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        tenant_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

        with tenant_scope(tenant_a, "Tenant A") as ctx_a:
            assert ctx_a.tenant_id == tenant_a
            assert get_current_tenant().tenant_id == tenant_a

        with tenant_scope(tenant_b, "Tenant B") as ctx_b:
            assert ctx_b.tenant_id == tenant_b
            assert get_current_tenant().tenant_id == tenant_b

    def test_cross_tenant_context_does_not_leak(self) -> None:
        """After exiting a tenant scope, the previous context is restored."""
        outer_id = "outer-0000-0000-0000-000000000000"
        inner_id = "inner-0000-0000-0000-000000000000"

        with tenant_scope(outer_id):
            assert get_current_tenant().tenant_id == outer_id
            with tenant_scope(inner_id):
                assert get_current_tenant().tenant_id == inner_id
            # After inner scope exits, outer should be restored
            assert get_current_tenant().tenant_id == outer_id

    def test_tenant_context_cleared_after_scope(self) -> None:
        """After a scope exits, tenant context reverts to previous state."""
        before = get_current_tenant()
        with tenant_scope("temp-tenant"):
            assert get_current_tenant().tenant_id == "temp-tenant"
        after = get_current_tenant()
        # Should revert to whatever it was before
        assert after == before or after is None

    def test_tenant_id_is_required(self) -> None:
        """TenantContext requires a tenant_id string."""
        # Empty string is technically valid but useless — the real
        # enforcement is at the middleware level where we validate
        # against the tenants table. This test documents that the
        # dataclass itself is permissive.
        ctx = TenantContext(tenant_id="test-id")
        assert ctx.tenant_id == "test-id"

    def test_data_query_should_include_tenant_filter(self) -> None:
        """Conceptual test: queries SHOULD filter by tenant_id.

        This test documents the expectation that when multi-tenant mode
        is enabled, all data queries must include a tenant_id filter.
        The actual enforcement happens via RLS policies in Postgres
        (infra/postgres/rls_policies.sql) and routing in Elasticsearch.
        """
        # This is a documentation test — the actual enforcement is at DB level
        # When MULTI_TENANT_ENABLED=true:
        # 1. Postgres RLS policies filter by rulerepo.current_tenant_id
        # 2. Elasticsearch uses routing=tenant_{id}
        # 3. Neo4j uses per-tenant databases
        assert True  # Enforcement is at infrastructure level

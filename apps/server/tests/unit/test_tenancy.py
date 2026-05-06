"""Tests for tenant context management."""

from __future__ import annotations

from rulerepo_server.core.tenancy.context import (
    DEFAULT_TENANT_ID,
    TenantContext,
    get_current_tenant,
    set_current_tenant,
    tenant_scope,
)


class TestTenantContext:
    """Tests for the TenantContext dataclass."""

    def test_create_with_id_only(self) -> None:
        ctx = TenantContext(tenant_id="tenant-123")
        assert ctx.tenant_id == "tenant-123"
        assert ctx.tenant_name is None

    def test_create_with_name(self) -> None:
        ctx = TenantContext(tenant_id="tenant-123", tenant_name="Acme Corp")
        assert ctx.tenant_id == "tenant-123"
        assert ctx.tenant_name == "Acme Corp"

    def test_frozen(self) -> None:
        ctx = TenantContext(tenant_id="tenant-123")
        try:
            ctx.tenant_id = "other"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass

    def test_equality(self) -> None:
        a = TenantContext(tenant_id="t1", tenant_name="A")
        b = TenantContext(tenant_id="t1", tenant_name="A")
        assert a == b

    def test_inequality(self) -> None:
        a = TenantContext(tenant_id="t1")
        b = TenantContext(tenant_id="t2")
        assert a != b


class TestDefaultTenantId:
    """Tests for the default tenant ID constant."""

    def test_default_tenant_id_format(self) -> None:
        assert DEFAULT_TENANT_ID == "00000000-0000-0000-0000-000000000000"

    def test_default_tenant_id_is_uuid_format(self) -> None:
        parts = DEFAULT_TENANT_ID.split("-")
        assert len(parts) == 5
        assert [len(p) for p in parts] == [8, 4, 4, 4, 12]


class TestGetSetCurrentTenant:
    """Tests for get/set tenant context functions."""

    def test_get_returns_none_by_default(self) -> None:
        # In a fresh context, there should be no tenant set
        # Note: other tests may have set a tenant, so we reset first
        token = set_current_tenant(TenantContext(tenant_id="temp"))
        from rulerepo_server.core.tenancy.context import _current_tenant

        _current_tenant.reset(token)
        # After reset, the default is None
        result = get_current_tenant()
        assert result is None

    def test_set_and_get(self) -> None:
        tenant = TenantContext(tenant_id="test-tenant", tenant_name="Test")
        token = set_current_tenant(tenant)
        try:
            assert get_current_tenant() == tenant
            assert get_current_tenant() is not None
            assert get_current_tenant().tenant_id == "test-tenant"  # type: ignore[union-attr]
        finally:
            from rulerepo_server.core.tenancy.context import _current_tenant

            _current_tenant.reset(token)

    def test_set_returns_token(self) -> None:
        tenant = TenantContext(tenant_id="test-tenant")
        token = set_current_tenant(tenant)
        assert token is not None
        from rulerepo_server.core.tenancy.context import _current_tenant

        _current_tenant.reset(token)


class TestTenantScope:
    """Tests for the tenant_scope context manager."""

    def test_scope_sets_tenant(self) -> None:
        with tenant_scope("scope-tenant") as ctx:
            assert ctx.tenant_id == "scope-tenant"
            current = get_current_tenant()
            assert current is not None
            assert current.tenant_id == "scope-tenant"

    def test_scope_with_name(self) -> None:
        with tenant_scope("scope-tenant", tenant_name="Test Org") as ctx:
            assert ctx.tenant_name == "Test Org"
            current = get_current_tenant()
            assert current is not None
            assert current.tenant_name == "Test Org"

    def test_scope_resets_on_exit(self) -> None:
        # Set a known state first
        original = TenantContext(tenant_id="original")
        token = set_current_tenant(original)
        try:
            with tenant_scope("temporary"):
                assert get_current_tenant().tenant_id == "temporary"  # type: ignore[union-attr]
            # After exiting, should be back to original
            assert get_current_tenant().tenant_id == "original"  # type: ignore[union-attr]
        finally:
            from rulerepo_server.core.tenancy.context import _current_tenant

            _current_tenant.reset(token)

    def test_scope_resets_on_exception(self) -> None:
        original = TenantContext(tenant_id="original")
        token = set_current_tenant(original)
        try:
            try:
                with tenant_scope("error-tenant"):
                    raise ValueError("test error")
            except ValueError:
                pass
            # Should be back to original despite exception
            assert get_current_tenant().tenant_id == "original"  # type: ignore[union-attr]
        finally:
            from rulerepo_server.core.tenancy.context import _current_tenant

            _current_tenant.reset(token)

    def test_nested_scopes(self) -> None:
        with tenant_scope("outer") as outer:
            assert outer.tenant_id == "outer"
            with tenant_scope("inner") as inner:
                assert inner.tenant_id == "inner"
                assert get_current_tenant().tenant_id == "inner"  # type: ignore[union-attr]
            assert get_current_tenant().tenant_id == "outer"  # type: ignore[union-attr]

    def test_yields_tenant_context(self) -> None:
        with tenant_scope("yielded") as ctx:
            assert isinstance(ctx, TenantContext)
            assert ctx.tenant_id == "yielded"

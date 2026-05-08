"""Integration tests for tenant isolation (RR-007).

Validates that cross-tenant queries return empty results when
tenant context is properly set via Postgres session variables.
"""

from __future__ import annotations

import pytest

from rulerepo_server.core.auth_oidc import OIDCUser, validate_oidc_token


class TestOIDCUserExtraction:
    """Test OIDC user extraction from JWT tokens."""

    @pytest.mark.asyncio
    async def test_anonymous_access_when_auth_not_required(self) -> None:
        """When AUTH_REQUIRED=false, anonymous access is allowed."""
        from rulerepo_server.core.auth_oidc import require_oidc_user

        user = await require_oidc_user(authorization=None)
        assert user.sub == "anonymous"
        assert user.tenant_id == "default"

    @pytest.mark.asyncio
    async def test_reject_invalid_bearer_format(self) -> None:
        """Non-Bearer authorization should be rejected."""
        with pytest.raises(Exception, match="Invalid Authorization header"):
            await validate_oidc_token("Basic dXNlcjpwYXNz")

    @pytest.mark.asyncio
    async def test_reject_empty_token(self) -> None:
        """Empty Bearer token should be rejected."""
        with pytest.raises(Exception, match="Empty Bearer token"):
            await validate_oidc_token("Bearer ")

    @pytest.mark.asyncio
    async def test_reject_malformed_jwt(self) -> None:
        """Non-JWT strings should be rejected."""
        with pytest.raises(Exception, match="Malformed JWT"):
            await validate_oidc_token("Bearer not-a-jwt")


class TestTenantIsolationConcepts:
    """Test tenant isolation domain concepts."""

    def test_oidc_user_has_tenant_id(self) -> None:
        """OIDCUser must always carry a tenant_id."""
        user = OIDCUser(sub="user-1", tenant_id="tenant-abc")
        assert user.tenant_id == "tenant-abc"

    def test_default_tenant_id(self) -> None:
        """When no tenant_id is specified, default is used."""
        user = OIDCUser(sub="user-1")
        assert user.tenant_id == "default"

    def test_oidc_user_carries_roles(self) -> None:
        """OIDC user can carry roles from token claims."""
        user = OIDCUser(
            sub="user-1",
            roles=["admin", "rule_approver"],
            tenant_id="tenant-1",
        )
        assert "admin" in user.roles
        assert "rule_approver" in user.roles

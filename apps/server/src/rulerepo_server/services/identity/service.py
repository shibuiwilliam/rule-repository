"""Identity management service.

Handles authentication via OIDC, SAML, and API keys, plus lifecycle
management for service accounts and API key rotation.

In a production deployment the OIDC and SAML flows delegate to external
identity providers (Okta, Azure AD, Google Workspace).  Phase 7a ships
the interface and a stub implementation so callers can be wired before
the real IdP adapters land.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from uuid import uuid4

from rulerepo_server.core.errors import AuthenticationError, NotFoundError, ValidationError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.tenant import (
    Principal,
    PrincipalKind,
    ServiceAccount,
)

logger = get_logger(__name__)


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


class IdentityService:
    """Manages principal authentication and service account lifecycle.

    Args:
        principal_store: Optional mapping of principal_id -> Principal.
        sa_store: Optional mapping of service_account_id -> ServiceAccount.
        key_index: Optional mapping of key_hash -> service_account_id.
    """

    def __init__(
        self,
        principal_store: dict[str, Principal] | None = None,
        sa_store: dict[str, ServiceAccount] | None = None,
        key_index: dict[str, str] | None = None,
    ) -> None:
        self._principals: dict[str, Principal] = principal_store if principal_store is not None else {}
        self._service_accounts: dict[str, ServiceAccount] = sa_store if sa_store is not None else {}
        self._key_index: dict[str, str] = key_index if key_index is not None else {}

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def authenticate_oidc(self, token: str) -> Principal:
        """Authenticate a principal via an OIDC ID token.

        In the stub implementation the token is treated as a principal ID
        for local development.  A production implementation validates the
        JWT signature, issuer, audience, and extracts claims.

        Args:
            token: An OIDC ID token (JWT).

        Returns:
            The authenticated Principal.

        Raises:
            AuthenticationError: If the token is invalid or the principal
                                 is unknown.
        """
        # Stub: treat token as principal ID for dev convenience
        principal = self._principals.get(token)
        if principal is None:
            raise AuthenticationError(f"OIDC token does not resolve to a known principal: {token[:8]}...")
        logger.info("oidc_authenticated", principal_id=principal.id)
        return principal

    async def authenticate_saml(self, assertion: str) -> Principal:
        """Authenticate a principal via a SAML assertion.

        In the stub implementation the assertion is treated as a
        principal ID.  A production implementation validates the XML
        signature and extracts attributes.

        Args:
            assertion: A SAML response / assertion (XML).

        Returns:
            The authenticated Principal.

        Raises:
            AuthenticationError: If the assertion is invalid.
        """
        principal = self._principals.get(assertion)
        if principal is None:
            raise AuthenticationError("SAML assertion does not resolve to a known principal")
        logger.info("saml_authenticated", principal_id=principal.id)
        return principal

    async def authenticate_api_key(self, key: str) -> Principal:
        """Authenticate a principal via an API key.

        Looks up the key hash in the index, resolves the owning service
        account, and returns a Principal representing it.

        Args:
            key: The raw API key.

        Returns:
            A Principal representing the service account.

        Raises:
            AuthenticationError: If the key is invalid or expired.
        """
        key_hash = _hash_key(key)
        sa_id = self._key_index.get(key_hash)
        if sa_id is None:
            raise AuthenticationError("Invalid API key")

        sa = self._service_accounts.get(sa_id)
        if sa is None:
            raise AuthenticationError("Service account not found for API key")

        # Check expiry
        if sa.expires_at is not None and sa.expires_at < datetime.now(tz=UTC):
            raise AuthenticationError("API key has expired")

        principal = Principal(
            id=sa.id,
            tenant_id=sa.tenant_id,
            kind=PrincipalKind.SERVICE_ACCOUNT,
            display_name=sa.name,
            roles=["service_account"],
        )
        logger.info("api_key_authenticated", sa_id=sa.id, tenant_id=sa.tenant_id)
        return principal

    # ------------------------------------------------------------------
    # Service account management
    # ------------------------------------------------------------------

    async def create_service_account(
        self,
        tenant_id: str,
        name: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[ServiceAccount, str]:
        """Create a new service account and generate an API key.

        Args:
            tenant_id: The owning tenant.
            name: Human-readable name for the service account.
            scopes: Permitted API scopes. Defaults to empty (no access).
            expires_at: Optional expiry for the API key.

        Returns:
            A tuple of (ServiceAccount, raw_api_key). The raw key is only
            returned once — it is not stored.

        Raises:
            ValidationError: If name is empty.
        """
        if not name.strip():
            raise ValidationError("Service account name must not be empty")

        raw_key = secrets.token_urlsafe(48)
        key_hash = _hash_key(raw_key)

        sa = ServiceAccount(
            id=str(uuid4()),
            tenant_id=tenant_id,
            name=name.strip(),
            scopes=scopes or [],
            api_key_hash=key_hash,
            created_at=datetime.now(tz=UTC),
            expires_at=expires_at,
        )
        self._service_accounts[sa.id] = sa
        self._key_index[key_hash] = sa.id
        logger.info("service_account_created", sa_id=sa.id, tenant_id=tenant_id)
        return sa, raw_key

    async def rotate_api_key(self, service_account_id: str) -> str:
        """Rotate the API key for a service account.

        The old key is immediately invalidated.

        Args:
            service_account_id: The service account to rotate.

        Returns:
            The new raw API key (only returned once).

        Raises:
            NotFoundError: If the service account does not exist.
        """
        sa = self._service_accounts.get(service_account_id)
        if sa is None:
            raise NotFoundError("ServiceAccount", service_account_id)

        # Remove old key from index
        old_hash = sa.api_key_hash
        self._key_index.pop(old_hash, None)

        # Generate new key
        raw_key = secrets.token_urlsafe(48)
        new_hash = _hash_key(raw_key)

        updated = ServiceAccount(
            id=sa.id,
            tenant_id=sa.tenant_id,
            name=sa.name,
            scopes=sa.scopes,
            api_key_hash=new_hash,
            created_at=sa.created_at,
            expires_at=sa.expires_at,
        )
        self._service_accounts[sa.id] = updated
        self._key_index[new_hash] = sa.id
        logger.info("api_key_rotated", sa_id=sa.id)
        return raw_key

    # ------------------------------------------------------------------
    # Principal management (for dev/test — production uses IdP sync)
    # ------------------------------------------------------------------

    async def register_principal(self, principal: Principal) -> Principal:
        """Register a principal in the local store.

        Used for development and testing. In production, principals are
        synced from the identity provider via SCIM.

        Args:
            principal: The principal to register.

        Returns:
            The registered principal.
        """
        self._principals[principal.id] = principal
        logger.info("principal_registered", principal_id=principal.id, tenant_id=principal.tenant_id)
        return principal

    async def get_principal(self, principal_id: str) -> Principal:
        """Get a principal by ID.

        Raises:
            NotFoundError: If the principal does not exist.
        """
        principal = self._principals.get(principal_id)
        if principal is None:
            raise NotFoundError("Principal", principal_id)
        return principal

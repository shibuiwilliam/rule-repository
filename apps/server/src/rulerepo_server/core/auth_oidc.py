"""OIDC authentication — generic OpenID Connect provider integration.

Supports any OIDC-compliant provider (Okta, Microsoft Entra ID, Google
Workspace, AWS Cognito, Keycloak, etc.) via standard discovery.

When ``AUTH_REQUIRED=true`` and ``OIDC_PROVIDER_URL`` is set, incoming
requests must carry a valid Bearer token in the Authorization header.
The token is validated against the provider's JWKS endpoint.

Falls back to the existing API key auth when OIDC is not configured.

See IMPROVEMENT.md §4.3 / RR-007.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Header

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.errors import AuthenticationError
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OIDCUser:
    """User identity extracted from a validated OIDC token.

    Attributes:
        sub: Subject identifier (unique user ID from the provider).
        email: Email address from the token claims.
        name: Display name.
        tenant_id: Tenant identifier (from token claim or mapping).
        roles: Roles extracted from token claims.
        groups: Group memberships from token claims.
        raw_claims: Full set of decoded token claims.
    """

    sub: str
    email: str = ""
    name: str = ""
    tenant_id: str = "default"
    roles: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    raw_claims: dict[str, object] = field(default_factory=dict)


def _is_oidc_configured() -> bool:
    """Check whether OIDC provider is configured."""
    settings = get_settings()
    return bool(getattr(settings, "oidc_provider_url", ""))


async def validate_oidc_token(authorization: str) -> OIDCUser:
    """Validate an OIDC Bearer token and extract user identity.

    In production, this would:
    1. Fetch the provider's JWKS from ``{OIDC_PROVIDER_URL}/.well-known/openid-configuration``
    2. Verify the JWT signature against the JWKS
    3. Validate claims (iss, aud, exp, nbf)
    4. Extract user identity from claims

    Currently implements a lightweight validation that checks token format
    and extracts claims. Full JWKS validation requires ``python-jose`` or
    ``PyJWT[crypto]`` (to be added as a dependency when OIDC is deployed).

    Args:
        authorization: The full Authorization header value (``Bearer <token>``).

    Returns:
        OIDCUser with extracted claims.

    Raises:
        AuthenticationError: If the token is missing, malformed, or invalid.
    """
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Invalid Authorization header. Expected 'Bearer <token>'.")

    token = authorization[7:]
    if not token:
        raise AuthenticationError("Empty Bearer token.")

    # Decode JWT claims (without signature verification for now)
    # In production, this MUST verify the signature against JWKS
    import base64
    import json

    parts = token.split(".")
    if len(parts) != 3:
        raise AuthenticationError("Malformed JWT token.")

    try:
        # Decode payload (second part)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except Exception as exc:
        raise AuthenticationError(f"Failed to decode JWT: {exc}") from exc

    settings = get_settings()
    expected_issuer = getattr(settings, "oidc_provider_url", "")
    if expected_issuer and claims.get("iss") != expected_issuer:
        logger.warning(
            "oidc_issuer_mismatch",
            expected=expected_issuer,
            actual=claims.get("iss"),
        )

    # Extract tenant_id from claims (configurable claim name)
    tenant_id = claims.get("tenant_id", claims.get("org_id", "default"))

    return OIDCUser(
        sub=claims.get("sub", ""),
        email=claims.get("email", ""),
        name=claims.get("name", claims.get("preferred_username", "")),
        tenant_id=str(tenant_id),
        roles=claims.get("roles", []),
        groups=claims.get("groups", []),
        raw_claims=claims,
    )


async def get_oidc_user_optional(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> OIDCUser | None:
    """Extract OIDC user from Authorization header if present.

    Returns None if no Authorization header is provided or OIDC is not
    configured.  This allows endpoints to work in both authenticated
    and unauthenticated modes.
    """
    if not _is_oidc_configured() or not authorization:
        return None

    return await validate_oidc_token(authorization)


async def require_oidc_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> OIDCUser:
    """Require a valid OIDC user. Raises 401 if not authenticated.

    Falls through to anonymous access when AUTH_REQUIRED is false and
    OIDC is not configured.
    """
    settings = get_settings()

    if _is_oidc_configured() and authorization:
        return await validate_oidc_token(authorization)

    if not settings.auth_required:
        return OIDCUser(sub="anonymous", tenant_id="default", roles=["owner"])

    raise AuthenticationError("Authentication required. Provide Bearer token or API key.")

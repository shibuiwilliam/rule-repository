"""Authentication and authorization — API key auth with role-based access control.

Phase 1 implements simple API-key-based auth. Full OIDC/OAuth2 deferred to later.
"""

from __future__ import annotations

import enum
import hashlib
from dataclasses import dataclass

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import ApiKeyModel
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.config import get_settings
from rulerepo_server.core.errors import AuthenticationError, AuthorizationError
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class Role(str, enum.Enum):
    """User roles for RBAC."""

    OWNER = "OWNER"
    APPROVER = "APPROVER"
    READER = "READER"


@dataclass
class CurrentUser:
    """Authenticated user context."""

    user_id: str
    role: Role
    scopes: list[str]


def _hash_key(api_key: str) -> str:
    """Hash an API key for storage comparison."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def get_current_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    """Authenticate the request via API key.

    When AUTH_REQUIRED is false (development), unauthenticated requests are
    allowed as OWNER. When true (production), a valid API key is required.

    Args:
        x_api_key: API key from the X-API-Key header.
        session: Database session.

    Returns:
        CurrentUser with role and scopes.

    Raises:
        AuthenticationError: If authentication is required and key is missing/invalid.
    """
    settings = get_settings()

    if not x_api_key:
        if settings.auth_required:
            raise AuthenticationError("API key required. Set X-API-Key header.")
        # Development fallback — anonymous access as OWNER for ease of use
        logger.debug("anonymous_access_allowed", auth_required=False)
        return CurrentUser(user_id="anonymous", role=Role.OWNER, scopes=["*"])

    key_hash = _hash_key(x_api_key)
    result = await session.execute(
        select(ApiKeyModel).where(
            ApiKeyModel.key_hash == key_hash,
            ApiKeyModel.active.is_(True),
        )
    )
    api_key_model = result.scalar_one_or_none()

    if api_key_model is None:
        raise AuthenticationError("Invalid API key")

    logger.info("authenticated", user_id=api_key_model.user_id, role=api_key_model.role)
    return CurrentUser(
        user_id=api_key_model.user_id,
        role=Role(api_key_model.role),
        scopes=api_key_model.scopes,
    )


def require_role(*allowed_roles: Role):
    """Create a dependency that enforces role-based access.

    Args:
        *allowed_roles: Roles that are permitted access.

    Returns:
        A FastAPI dependency function.
    """

    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise AuthorizationError(
                f"Role {user.role.value} not allowed. Required: {[r.value for r in allowed_roles]}"
            )
        return user

    return _check

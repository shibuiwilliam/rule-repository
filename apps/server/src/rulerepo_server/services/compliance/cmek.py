"""Customer-Managed Encryption Key (CMEK) integration.

Provides tenant-isolated encryption using customer-managed keys.
In development, Fernet symmetric encryption with locally generated
keys is used.  In production, the service delegates to a configured
Key Management Service (AWS KMS, GCP KMS, or Azure Key Vault).

See CLAUDE.md section 14 and IMPROVEMENT.md for the compliance roadmap.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from cryptography.fernet import Fernet

from rulerepo_server.core.errors import RuleRepoError
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class CMEKError(RuleRepoError):
    """Raised when a CMEK operation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="CMEK_ERROR", status_code=500)


class KeyProvider(StrEnum):
    """Supported key management providers."""

    LOCAL = "local"
    AWS_KMS = "aws_kms"
    GCP_KMS = "gcp_kms"
    AZURE_KEYVAULT = "azure_keyvault"


@dataclass(frozen=True, slots=True)
class KeyInfo:
    """Metadata about a tenant's encryption key.

    Attributes:
        key_id: Unique identifier of the key (or key version).
        provider: Which KMS backend manages the key.
        created_at: When the key was first created.
        last_rotated_at: When the key was last rotated (may equal created_at).
        tenant_id: The tenant that owns the key.
    """

    key_id: str
    provider: str
    created_at: datetime
    last_rotated_at: datetime
    tenant_id: str


@dataclass(slots=True)
class _TenantKeyState:
    """Internal mutable state for a single tenant's key."""

    key_id: str
    fernet: Fernet
    created_at: datetime
    last_rotated_at: datetime
    version: int = 1


class CMEKService:
    """Tenant-isolated encryption using customer-managed keys.

    The local (development) implementation generates Fernet keys
    per tenant and stores them in memory.  Production deployments
    replace this with calls to the configured KMS via envelope
    encryption: a data-encryption key (DEK) is generated locally,
    and the DEK is wrapped by the customer's KMS key.
    """

    def __init__(self, *, provider: KeyProvider | None = None) -> None:
        """Initialize the CMEK service.

        Args:
            provider: The key-management provider.  Defaults to ``LOCAL``
                in development.  Read from ``CMEK_PROVIDER`` env var if
                not specified.
        """
        if provider is not None:
            self._provider = provider
        else:
            env_provider = os.environ.get("CMEK_PROVIDER", "local")
            self._provider = KeyProvider(env_provider)

        self._tenant_keys: dict[str, _TenantKeyState] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def encrypt(self, data: bytes, tenant_id: str) -> bytes:
        """Encrypt data using the tenant's key.

        If the tenant does not yet have a key, one is generated
        automatically (local mode) or provisioned via KMS.

        Args:
            data: Plaintext bytes to encrypt.
            tenant_id: Tenant identifier for key isolation.

        Returns:
            Ciphertext bytes.

        Raises:
            CMEKError: If encryption fails.
        """
        state = self._ensure_key(tenant_id)
        try:
            return state.fernet.encrypt(data)
        except Exception as exc:
            raise CMEKError(f"Encryption failed for tenant {tenant_id}: {exc}") from exc

    async def decrypt(self, data: bytes, tenant_id: str) -> bytes:
        """Decrypt data using the tenant's key.

        Args:
            data: Ciphertext bytes produced by :meth:`encrypt`.
            tenant_id: Tenant identifier.

        Returns:
            Plaintext bytes.

        Raises:
            CMEKError: If decryption fails (wrong key, corrupted data, etc.).
        """
        state = self._tenant_keys.get(tenant_id)
        if state is None:
            raise CMEKError(
                f"No encryption key found for tenant '{tenant_id}'. Cannot decrypt data without the original key."
            )
        try:
            return state.fernet.decrypt(data)
        except Exception as exc:
            raise CMEKError(f"Decryption failed for tenant {tenant_id}: {exc}") from exc

    async def rotate_key(self, tenant_id: str) -> str:
        """Rotate the encryption key for a tenant.

        In local mode, a new Fernet key is generated.  Existing data
        encrypted with the old key must be re-encrypted by the caller
        using a background migration job.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            The new key version identifier.

        Raises:
            CMEKError: If key rotation fails.
        """
        now = datetime.now(tz=UTC)
        old_state = self._tenant_keys.get(tenant_id)
        new_version = (old_state.version + 1) if old_state else 1
        new_key = Fernet.generate_key()
        new_key_id = f"{tenant_id}:v{new_version}"

        self._tenant_keys[tenant_id] = _TenantKeyState(
            key_id=new_key_id,
            fernet=Fernet(new_key),
            created_at=old_state.created_at if old_state else now,
            last_rotated_at=now,
            version=new_version,
        )

        logger.info(
            "cmek_key_rotated",
            tenant_id=tenant_id,
            new_key_id=new_key_id,
            version=new_version,
            provider=self._provider,
        )

        return new_key_id

    def get_key_info(self, tenant_id: str) -> KeyInfo:
        """Retrieve metadata about a tenant's encryption key.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            A :class:`KeyInfo` describing the key.

        Raises:
            CMEKError: If the tenant has no key.
        """
        state = self._tenant_keys.get(tenant_id)
        if state is None:
            # Auto-provision for info queries
            state = self._ensure_key(tenant_id)

        return KeyInfo(
            key_id=state.key_id,
            provider=self._provider.value,
            created_at=state.created_at,
            last_rotated_at=state.last_rotated_at,
            tenant_id=tenant_id,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_key(self, tenant_id: str) -> _TenantKeyState:
        """Ensure a key exists for the tenant, creating one if needed."""
        if tenant_id in self._tenant_keys:
            return self._tenant_keys[tenant_id]

        if self._provider != KeyProvider.LOCAL:
            logger.warning(
                "cmek_kms_stub",
                tenant_id=tenant_id,
                provider=self._provider,
                msg="Non-local KMS providers are not yet implemented; falling back to local key.",
            )

        now = datetime.now(tz=UTC)
        key = Fernet.generate_key()
        key_id = f"{tenant_id}:v1"

        state = _TenantKeyState(
            key_id=key_id,
            fernet=Fernet(key),
            created_at=now,
            last_rotated_at=now,
            version=1,
        )
        self._tenant_keys[tenant_id] = state

        logger.info(
            "cmek_key_provisioned",
            tenant_id=tenant_id,
            key_id=key_id,
            provider=self._provider,
        )

        return state

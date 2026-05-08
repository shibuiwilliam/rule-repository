"""Encrypted shadow store for PII originals.

Stores the reverse-mapping produced by the redactor so that original
PII values can be recovered by authorized personnel (e.g. for data
subject access requests) while remaining encrypted at rest.

In development mode the store uses Fernet symmetric encryption with a
local key derived from the ``PII_SHADOW_KEY`` environment variable.
In production the encryption layer delegates to a customer-managed
encryption key (CMEK) service.

See CLAUDE.md section 14.4.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cryptography.fernet import Fernet

from rulerepo_server.core.errors import RuleRepoError
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class ShadowStoreError(RuleRepoError):
    """Raised when the shadow store encounters an unrecoverable error."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="SHADOW_STORE_ERROR", status_code=500)


@dataclass(frozen=True, slots=True)
class ShadowEntry:
    """A single shadow-store record.

    Attributes:
        redaction_id: Correlation key matching the ``RedactionResult``.
        tenant_id: Tenant that owns the data.
        encrypted_payload: The Fernet-encrypted JSON of the redaction map.
        subject_id: Optional data-subject identifier for erasure lookups.
        created_at: When the entry was stored.
    """

    redaction_id: str
    tenant_id: str
    encrypted_payload: bytes
    subject_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class ShadowStore:
    """Encrypted storage for PII redaction mappings.

    The default implementation uses an in-memory dictionary backed by
    Fernet encryption.  Production deployments should replace the
    backing store with a durable, encrypted database or object store
    and the encryption with CMEK via :class:`~services.compliance.cmek.CMEKService`.
    """

    def __init__(self, *, encryption_key: bytes | None = None) -> None:
        """Initialize the shadow store.

        Args:
            encryption_key: A Fernet-compatible key.  If not provided,
                the store reads ``PII_SHADOW_KEY`` from the environment.
                If that is also absent a fresh key is generated (suitable
                only for development / testing).
        """
        if encryption_key is not None:
            self._key = encryption_key
        else:
            env_key = os.environ.get("PII_SHADOW_KEY")
            if env_key:
                self._key = env_key.encode()
            else:
                self._key = Fernet.generate_key()
                logger.warning(
                    "shadow_store_ephemeral_key",
                    msg="No PII_SHADOW_KEY configured; generated an ephemeral key. Data will not survive restarts.",
                )
        self._fernet = Fernet(self._key)
        # In-memory backing store.  Replace with a persistent adapter
        # for production use.
        self._store: dict[str, ShadowEntry] = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def store(
        self,
        redaction_id: str,
        redaction_map: dict[str, Any],
        tenant_id: str,
        *,
        subject_id: str | None = None,
    ) -> str:
        """Encrypt and persist a redaction mapping.

        Args:
            redaction_id: Unique identifier from the redaction result.
            redaction_map: The placeholder-to-original mapping.
            tenant_id: Tenant that owns the PII.
            subject_id: Optional data-subject identifier for erasure.

        Returns:
            A storage reference (currently the ``redaction_id`` itself).

        Raises:
            ShadowStoreError: If encryption fails.
        """
        try:
            payload = json.dumps(redaction_map, default=str).encode()
            encrypted = self._fernet.encrypt(payload)
        except Exception as exc:
            raise ShadowStoreError(f"Encryption failed: {exc}") from exc

        entry = ShadowEntry(
            redaction_id=redaction_id,
            tenant_id=tenant_id,
            encrypted_payload=encrypted,
            subject_id=subject_id,
        )
        self._store[self._key_for(redaction_id, tenant_id)] = entry

        logger.info(
            "shadow_store_entry_created",
            redaction_id=redaction_id,
            tenant_id=tenant_id,
            subject_id=subject_id,
        )
        return redaction_id

    async def retrieve(self, redaction_id: str, tenant_id: str) -> dict[str, Any] | None:
        """Retrieve and decrypt a redaction mapping.

        Args:
            redaction_id: The identifier returned by :meth:`store`.
            tenant_id: Tenant that owns the PII.

        Returns:
            The original redaction map, or ``None`` if not found.
        """
        entry = self._store.get(self._key_for(redaction_id, tenant_id))
        if entry is None:
            return None

        try:
            decrypted = self._fernet.decrypt(entry.encrypted_payload)
            return json.loads(decrypted)  # type: ignore[no-any-return]
        except Exception as exc:
            logger.error(
                "shadow_store_decrypt_failed",
                redaction_id=redaction_id,
                error=str(exc),
            )
            raise ShadowStoreError(f"Decryption failed for {redaction_id}") from exc

    async def delete(self, redaction_id: str, tenant_id: str) -> bool:
        """Permanently delete a shadow entry (right-to-erasure).

        Args:
            redaction_id: The identifier of the entry.
            tenant_id: Tenant that owns the PII.

        Returns:
            True if an entry was deleted, False if not found.
        """
        key = self._key_for(redaction_id, tenant_id)
        if key in self._store:
            del self._store[key]
            logger.info(
                "shadow_store_entry_deleted",
                redaction_id=redaction_id,
                tenant_id=tenant_id,
            )
            return True
        return False

    async def delete_by_subject(self, subject_id: str, tenant_id: str) -> int:
        """Delete all shadow entries for a data subject.

        Used for GDPR Article 17 right-to-erasure requests.

        Args:
            subject_id: The data-subject identifier.
            tenant_id: Tenant that owns the PII.

        Returns:
            The number of entries deleted.
        """
        keys_to_delete = [
            key for key, entry in self._store.items() if entry.subject_id == subject_id and entry.tenant_id == tenant_id
        ]
        for key in keys_to_delete:
            del self._store[key]

        logger.info(
            "shadow_store_subject_erased",
            subject_id=subject_id,
            tenant_id=tenant_id,
            count=len(keys_to_delete),
        )
        return len(keys_to_delete)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _key_for(redaction_id: str, tenant_id: str) -> str:
        """Composite key for the backing store."""
        return f"{tenant_id}:{redaction_id}"

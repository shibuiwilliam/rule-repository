"""Audit log entry — immutable, hash-chained records of all significant actions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

# Well-known genesis hash for the first entry in the chain
GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditEntry:
    """An immutable audit log record with hash-chain integrity.

    Each entry references the hash of the previous entry, forming a
    tamper-evident chain. The chain can be verified by recomputing
    hashes from the genesis entry forward.
    """

    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    action: str = ""
    actor: str = "system"
    resource_type: str = ""
    resource_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    previous_hash: str = GENESIS_HASH
    entry_hash: str = ""

    @staticmethod
    def compute_hash(previous_hash: str, entry_data: dict[str, Any]) -> str:
        """Compute the SHA-256 hash for an audit entry.

        Args:
            previous_hash: Hash of the previous entry in the chain.
            entry_data: Canonical dictionary of entry fields to hash.

        Returns:
            Hex-encoded SHA-256 hash string.
        """
        canonical = json.dumps(entry_data, sort_keys=True, default=str)
        payload = f"{previous_hash}{canonical}"
        return hashlib.sha256(payload.encode()).hexdigest()

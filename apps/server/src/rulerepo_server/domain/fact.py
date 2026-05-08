"""Domain models for the Fact Store.

The Fact Store resolves external facts that rules depend on but that no
input artifact contains.  Examples: employee 36-agreement status, OFAC
sanctions matches, employee grade, vendor screening status.

All types in this module are pure domain objects with no external
dependencies beyond the standard library.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class FactStatus(str, enum.Enum):
    """Resolution status of a single fact lookup."""

    RESOLVED = "resolved"
    NOT_FOUND = "not_found"
    ERROR = "error"
    CACHED = "cached"


@dataclass(frozen=True)
class Fact:
    """A single resolved external fact.

    Attributes:
        key: The canonical fact key (e.g., ``employee_grade``).
        value: The resolved value.  Type depends on the fact schema.
        status: Resolution status.
        source_provider: Name of the provider that resolved this fact.
        resolved_at: Timestamp when the fact was resolved.
        ttl_seconds: Time-to-live for caching.  ``None`` means no caching.
        metadata: Provider-specific metadata (e.g., match confidence).
    """

    key: str
    value: Any
    status: FactStatus
    source_provider: str
    resolved_at: datetime
    ttl_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FactSchema:
    """Schema descriptor for a fact that a provider can resolve.

    Attributes:
        key: Canonical fact key.
        description: Human-readable description of what this fact represents.
        value_type: Expected Python type name (e.g., ``str``, ``bool``, ``int``).
        required_context_keys: Context keys that must be present for resolution.
        domain: Business domain this fact belongs to (e.g., ``hr``, ``finance``).
    """

    key: str
    description: str
    value_type: str
    required_context_keys: list[str] = field(default_factory=list)
    domain: str = "general"


@dataclass(frozen=True)
class FactResolutionResult:
    """Aggregate result of resolving a batch of facts.

    Attributes:
        requested: The list of fact keys that were requested.
        resolved: Successfully resolved facts keyed by fact key.
        missing: Fact keys for which no provider was found or the value
            could not be determined.
        errors: Fact keys that failed resolution, mapped to error messages.
    """

    requested: list[str] = field(default_factory=list)
    resolved: dict[str, Fact] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

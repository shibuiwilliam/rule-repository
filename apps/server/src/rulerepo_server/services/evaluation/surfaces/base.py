"""Surface adapter base — the abstraction boundary for per-surface logic.

Each surface provides an adapter that converts domain-specific input
into a uniform Subject representation. The evaluation core never
imports from surface packages directly — it dispatches through the
registry.

See CLAUDE.md §7.2, §14.2.2.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.domain.evaluation import Actor, Surface


@dataclass(frozen=True)
class EvaluationSubjectPayload:
    """Uniform subject payload that the evaluation core consumes.

    Surface adapters produce this from domain-specific input. The
    evaluation core consumes it without knowing which surface produced it.

    Attributes:
        surface: Which surface this subject belongs to.
        identifier: Stable subject reference for audit (e.g., ``pr#42``).
        description: Natural-language description for the LLM prompt.
        payload: Structured payload data (surface-specific).
        facts: Normalized facts that any rule may consult.
        actor: Who is acting / being evaluated.
        timestamp: When the subject came into being.
        locale: Locale of the payload content.
    """

    surface: Surface
    identifier: str
    description: str
    payload: dict[str, Any] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)
    actor: Actor | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    locale: str = "en"


class SurfaceAdapter(ABC):
    """Abstract base class for surface-specific evaluation adapters.

    Each surface implements this ABC. The adapter is responsible for:
    1. Parsing domain-specific input into a ``EvaluationSubjectPayload``
    2. Resolving applicable rule scopes
    3. Providing surface-specific prompt hints for the LLM
    4. Specifying PII fields for sanitization
    5. Specifying default audit retention

    Implementations live in ``surfaces/<surface_name>/adapter.py``.
    """

    @property
    @abstractmethod
    def surface(self) -> Surface:
        """The Surface enum value this adapter handles."""
        ...

    @abstractmethod
    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a domain-specific request payload into a uniform subject.

        Args:
            payload: Raw request payload with surface-specific fields.

        Returns:
            Uniform EvaluationSubjectPayload for the evaluation core.
        """
        ...

    @abstractmethod
    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve applicable rule scopes from the payload.

        Args:
            payload: Raw request payload.

        Returns:
            List of scope strings for rule selection.
        """
        ...

    def get_prompt_hints(self) -> str:
        """Return surface-specific hints injected into the universal prompt.

        Override this to provide domain-specific guidance to the LLM judge.
        Default returns an empty string (no hints).

        Returns:
            Prompt hint text, or empty string.
        """
        return ""

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        """Return JSON paths into ``payload`` that contain PII.

        Override per surface. Default returns empty list.

        Args:
            payload: Raw request payload.

        Returns:
            List of JSON path strings pointing to PII fields.
        """
        return []

    @property
    def default_audit_retention_days(self) -> int:
        """Default audit log retention for this surface in days.

        Override per surface. Default is 365 days (1 year).
        """
        return 365

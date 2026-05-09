"""Generic surface adapter — fallback for unclassified subjects.

Used when the incoming evaluation request does not match any specific
surface. Provides minimal parsing with no special prompt hints or PII
handling.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import Surface
from rulerepo_server.services.evaluation.surfaces.base import (
    EvaluationSubjectPayload,
    SurfaceAdapter,
)


class GenericSurfaceAdapter(SurfaceAdapter):
    """Fallback surface adapter for unclassified subjects.

    Accepts free-form content and description with optional facts.
    No surface-specific prompt hints, PII fields, or special scope
    resolution.
    """

    @property
    def surface(self) -> Surface:
        return Surface.GENERIC

    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a generic evaluation request into a uniform subject.

        Expected payload keys:
            - content: str — free-form content to evaluate
            - description: str — narrative description
            - facts: dict — additional structured facts

        Returns:
            EvaluationSubjectPayload with minimal generic fields.
        """
        content = payload.get("content", "")
        description = payload.get("description", "")

        if not description and content:
            description = content[:500]
            if len(content) > 500:
                description += "..."
        elif not description:
            description = "Generic evaluation subject"

        facts = dict(payload.get("facts", {}))

        return EvaluationSubjectPayload(
            surface=Surface.GENERIC,
            identifier=f"generic:{hash(content) % 10**8:08d}",
            description=description,
            payload={
                "content": content,
            },
            facts=facts,
            locale=payload.get("locale", "en"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Generic surface has no special scope resolution."""
        return ["general"]

    def get_prompt_hints(self) -> str:
        """Generic surface provides no special prompt hints."""
        return ""

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        return []

    @property
    def default_audit_retention_days(self) -> int:
        return 365

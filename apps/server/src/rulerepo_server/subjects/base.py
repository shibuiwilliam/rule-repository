"""SubjectAdapter protocol — the interface every subject type must implement."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from rulerepo_server.domain.evaluation import EvaluationContext


@runtime_checkable
class SubjectAdapter(Protocol):
    """Protocol for subject-type-specific evaluation adapters.

    Each adapter translates a typed payload into the uniform
    EvaluationContext consumed by the evaluation pipeline.
    """

    @property
    def subject_type(self) -> str:
        """The SubjectType this adapter handles."""
        ...

    def parse_payload(self, payload: dict[str, Any]) -> EvaluationContext:
        """Parse a subject-specific payload into an EvaluationContext.

        Args:
            payload: Type-specific data (diff, event details, clause text, etc.).

        Returns:
            A uniform EvaluationContext for the evaluation pipeline.
        """
        ...

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Determine applicable rule scopes from the payload.

        Args:
            payload: Type-specific data.

        Returns:
            List of scope strings for rule selection.
        """
        ...

    def format_prompt_context(self, payload: dict[str, Any]) -> str:
        """Format the payload into a human-readable context string for the LLM prompt.

        Args:
            payload: Type-specific data.

        Returns:
            Formatted context string to embed in the evaluation prompt.
        """
        ...

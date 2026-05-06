"""Base protocol for evaluation domain adapters.

Each adapter knows how to parse domain-specific input into a uniform
EvaluationContext, resolve applicable rule scopes, and provide
domain-specific prompt fragments for the LLM judge.

See: CLAUDE.md §14, PROJECT.md §4.3
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EvaluationDomainAdapter(Protocol):
    """Protocol for domain-specific evaluation adapters.

    Implementations must provide:
      - ``domain``: discriminator string (e.g. ``"code"``, ``"business_event"``)
      - ``parse()``: convert raw request payload into an EvaluationContext
      - ``resolve_scopes()``: extract applicable rule scopes from the payload
      - ``get_prompt_fragments()``: return domain-specific prompt text for the LLM
    """

    @property
    def domain(self) -> str:
        """Discriminator string identifying this adapter's domain."""
        ...

    async def parse(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Parse the request payload into an EvaluationContext dict.

        The returned dict is the uniform input to RuleSelector and BatchEvaluator.

        Args:
            payload: Raw request payload with domain-specific fields.

        Returns:
            EvaluationContext-compatible dict with normalized fields.
        """
        ...

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve applicable rule scopes from the payload.

        For ``code``: from file paths via DEFAULT_SCOPE_MAP.
        For ``business_event``: from event_type and Subject fields.
        For ``document_diff``: from contract_type and ContractScope.
        For ``communication``: from channel sensitivity and audience.
        For ``documentation``: from doc paths and document type.

        Args:
            payload: Raw request payload.

        Returns:
            List of scope strings for rule selection.
        """
        ...

    def get_prompt_fragments(self) -> dict[str, str]:
        """Return adapter-specific prompt fragments for the evaluation prompt.

        Keys are placeholders (e.g. ``domain_intro``, ``context_format``)
        used in the shared prompt template.

        Returns:
            Dict mapping placeholder names to prompt text.
        """
        ...

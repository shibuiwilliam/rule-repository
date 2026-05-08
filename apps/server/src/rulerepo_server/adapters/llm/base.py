"""Base LLM provider Protocol definition.

All LLM providers must implement this Protocol. The Protocol
abstracts away provider-specific details so that the evaluation
engine, extraction pipeline, and other services can work with
any configured provider.

See CLAUDE.md §9 for mandatory rules when calling any LLM provider.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM provider implementations.

    Each provider must expose a name, generation methods for text
    and structured output, an embed method for producing vector
    embeddings, token counting, and cost properties.

    Attributes:
        name: Human-readable provider identifier (e.g., "gemini", "anthropic").
    """

    name: str

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 1.0,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a completion from the LLM.

        Args:
            prompt: The input prompt text.
            model: Optional model ID override. If None, uses the
                   provider's default model.
            temperature: Sampling temperature. Default 1.0 per Gemini
                        best practices. Do not change without justification.
            response_format: Optional structured output format specification.
                           Provider-specific (e.g., JSON schema).

        Returns:
            A dict containing at minimum:
                - "text": The generated text response.
                - "model": The model ID that was used.
                - "input_tokens": Number of input tokens consumed.
                - "output_tokens": Number of output tokens generated.
                - "provider": The provider name.
        """
        ...

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured output conforming to a JSON schema.

        Default implementation calls generate with response_format.
        Providers may override for native structured-output support.

        Args:
            prompt: The input prompt text.
            schema: JSON Schema the output must conform to.
            model: Optional model ID override.

        Returns:
            A dict with the same keys as generate(), plus:
                - "structured": The parsed JSON object.
        """
        ...

    async def embed(self, text: str) -> list[float]:
        """Generate a vector embedding for the given text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        ...

    async def count_tokens(self, text: str) -> int:
        """Estimate the token count for a text string.

        Args:
            text: The input text.

        Returns:
            Approximate number of tokens.
        """
        ...

    @property
    def model_id(self) -> str:
        """Return the default model ID for this provider."""
        ...

    @property
    def cost_per_1k_input_tokens(self) -> float:
        """Return the cost in USD per 1,000 input tokens."""
        ...

    @property
    def cost_per_1k_output_tokens(self) -> float:
        """Return the cost in USD per 1,000 output tokens."""
        ...

"""Local/self-hosted LLM provider stub (Ollama / vLLM).

This is a stub implementation that raises NotImplementedError
until a local LLM endpoint is configured. To enable this provider:

1. Run Ollama or vLLM locally (e.g., ollama serve)
2. Set LLM_PROVIDER_SELF_HOSTED_URL in .env
3. Configure LLM_TENANT_OVERRIDES for sensitivity-based routing

This provider is intended for handling RESTRICTED-sensitivity rules
that must not be sent to external cloud LLM providers.
"""

from __future__ import annotations

from typing import Any


class LocalProvider:
    """Local/self-hosted LLM provider (Ollama, vLLM, etc.).

    Requires LLM_PROVIDER_SELF_HOSTED_URL environment variable to be set.
    Communicates with the local LLM server via its OpenAI-compatible
    HTTP API.

    Attributes:
        name: Provider identifier.
    """

    name: str = "local"

    @property
    def model_id(self) -> str:
        """Return the default model ID."""
        return "local"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        """Return the cost in USD per 1,000 input tokens (zero for self-hosted)."""
        return 0.0

    @property
    def cost_per_1k_output_tokens(self) -> float:
        """Return the cost in USD per 1,000 output tokens (zero for self-hosted)."""
        return 0.0

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 1.0,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a completion using the local LLM.

        Args:
            prompt: The input prompt text.
            model: Optional model ID (e.g., "llama3.1:70b").
            temperature: Sampling temperature.
            response_format: Optional structured output format.

        Raises:
            NotImplementedError: Always, until the provider is configured.
        """
        raise NotImplementedError(
            "Local LLM provider not configured. "
            "Set LLM_PROVIDER_SELF_HOSTED_URL environment variable and ensure the LLM server is running."
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured output using the local LLM.

        Args:
            prompt: The input prompt text.
            schema: JSON Schema the output must conform to.
            model: Optional model ID override.

        Raises:
            NotImplementedError: Always, until the provider is configured.
        """
        raise NotImplementedError(
            "Local LLM provider not configured. "
            "Set LLM_PROVIDER_SELF_HOSTED_URL environment variable and ensure the LLM server is running."
        )

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding using the local LLM.

        Args:
            text: The input text to embed.

        Raises:
            NotImplementedError: Always, until the provider is configured.
        """
        raise NotImplementedError(
            "Local LLM provider not configured. "
            "Set LLM_PROVIDER_SELF_HOSTED_URL environment variable and ensure the LLM server is running."
        )

    async def count_tokens(self, text: str) -> int:
        """Estimate token count for a text string.

        Args:
            text: The input text.

        Raises:
            NotImplementedError: Always, until the provider is configured.
        """
        raise NotImplementedError(
            "Local LLM provider not configured. "
            "Set LLM_PROVIDER_SELF_HOSTED_URL environment variable and ensure the LLM server is running."
        )

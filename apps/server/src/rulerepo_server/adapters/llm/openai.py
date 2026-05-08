"""OpenAI GPT LLM provider stub.

This is a stub implementation that raises NotImplementedError
until the OpenAI SDK is configured. To enable this provider:

1. Install the SDK: uv add openai
2. Set OPENAI_API_KEY in .env
3. Set LLM_PROVIDER_PRIMARY=openai or configure per-rule routing

The provider supports both text generation and embeddings via
the OpenAI API.
"""

from __future__ import annotations

from typing import Any


class OpenAIProvider:
    """OpenAI GPT LLM provider.

    Requires OPENAI_API_KEY environment variable to be set.
    Uses the openai Python SDK for API communication.

    Attributes:
        name: Provider identifier.
    """

    name: str = "openai"

    @property
    def model_id(self) -> str:
        """Return the default model ID."""
        return "gpt-4o"

    @property
    def cost_per_1k_input_tokens(self) -> float:
        """Return the cost in USD per 1,000 input tokens."""
        return 0.0025

    @property
    def cost_per_1k_output_tokens(self) -> float:
        """Return the cost in USD per 1,000 output tokens."""
        return 0.01

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 1.0,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a completion using OpenAI GPT.

        Args:
            prompt: The input prompt text.
            model: Optional model ID (e.g., "gpt-4o").
            temperature: Sampling temperature.
            response_format: Optional structured output format.

        Raises:
            NotImplementedError: Always, until the provider is configured.
        """
        raise NotImplementedError(
            "OpenAI provider not configured. Set OPENAI_API_KEY environment variable and install the openai package."
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured output using OpenAI GPT.

        Args:
            prompt: The input prompt text.
            schema: JSON Schema the output must conform to.
            model: Optional model ID override.

        Raises:
            NotImplementedError: Always, until the provider is configured.
        """
        raise NotImplementedError(
            "OpenAI provider not configured. Set OPENAI_API_KEY environment variable and install the openai package."
        )

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding using OpenAI.

        Args:
            text: The input text to embed.

        Raises:
            NotImplementedError: Always, until the provider is configured.
        """
        raise NotImplementedError(
            "OpenAI provider not configured. Set OPENAI_API_KEY environment variable and install the openai package."
        )

    async def count_tokens(self, text: str) -> int:
        """Estimate token count for a text string.

        Args:
            text: The input text.

        Raises:
            NotImplementedError: Always, until the provider is configured.
        """
        raise NotImplementedError(
            "OpenAI provider not configured. Set OPENAI_API_KEY environment variable and install the openai package."
        )

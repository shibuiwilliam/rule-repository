"""Anthropic Claude LLM provider stub.

This is a stub implementation that raises NotImplementedError
until the Anthropic SDK is configured. To enable this provider:

1. Install the SDK: uv add anthropic
2. Set ANTHROPIC_API_KEY in .env
3. Set LLM_PROVIDER_DEFAULT=anthropic or configure per-rule routing

The provider will use Claude models for generation and a compatible
embedding model when available.
"""

from __future__ import annotations

from typing import Any


class AnthropicProvider:
    """Anthropic Claude LLM provider.

    Requires ANTHROPIC_API_KEY environment variable to be set.
    Uses the anthropic Python SDK for API communication.

    Attributes:
        name: Provider identifier.
    """

    name: str = "anthropic"

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 1.0,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a completion using Anthropic Claude.

        Args:
            prompt: The input prompt text.
            model: Optional model ID (e.g., "claude-sonnet-4-20250514").
            temperature: Sampling temperature.
            response_format: Optional structured output format.

        Raises:
            NotImplementedError: Always, until the provider is configured.
        """
        raise NotImplementedError(
            "Anthropic provider not configured. "
            "Set ANTHROPIC_API_KEY environment variable and install the anthropic package."
        )

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding using Anthropic.

        Args:
            text: The input text to embed.

        Raises:
            NotImplementedError: Always, until the provider is configured.
        """
        raise NotImplementedError(
            "Anthropic provider not configured. "
            "Set ANTHROPIC_API_KEY environment variable and install the anthropic package."
        )

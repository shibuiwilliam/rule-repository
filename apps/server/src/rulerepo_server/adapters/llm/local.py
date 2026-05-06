"""Local/self-hosted LLM provider stub (Ollama / vLLM).

This is a stub implementation that raises NotImplementedError
until a local LLM endpoint is configured. To enable this provider:

1. Run Ollama or vLLM locally (e.g., ollama serve)
2. Set LOCAL_LLM_ENDPOINT in .env (default: http://localhost:11434)
3. Set LLM_PROVIDER_RESTRICTED=local for sensitivity=RESTRICTED rules

This provider is intended for handling RESTRICTED-sensitivity rules
that must not be sent to external cloud LLM providers.
"""

from __future__ import annotations

from typing import Any


class LocalProvider:
    """Local/self-hosted LLM provider (Ollama, vLLM, etc.).

    Requires LOCAL_LLM_ENDPOINT environment variable to be set.
    Communicates with the local LLM server via its OpenAI-compatible
    HTTP API.

    Attributes:
        name: Provider identifier.
    """

    name: str = "local"

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
            "Set LOCAL_LLM_ENDPOINT environment variable and ensure the LLM server is running."
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
            "Set LOCAL_LLM_ENDPOINT environment variable and ensure the LLM server is running."
        )

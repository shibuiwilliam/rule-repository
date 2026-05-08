"""Gemini LLM provider -- wraps the google-genai SDK into the LLMProvider protocol.

This is the default provider for the Rule Repository. It delegates to
the existing Gemini client (adapters/gemini/client.py) and embeddings
(adapters/gemini/embeddings.py) modules.

See CLAUDE.md §9 for mandatory rules when calling any LLM provider.
"""

from __future__ import annotations

import json
from typing import Any

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class GeminiProvider:
    """Gemini LLM provider using the google-genai SDK.

    Uses the existing Gemini client for generation and embeddings.
    Lazily initializes the underlying google-genai Client on first use.

    Attributes:
        name: Provider identifier.
    """

    name: str = "gemini"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.gemini_api_key
        self._default_model = settings.llm_default_model
        self._client: Any = None

    def _get_client(self) -> Any:
        """Return the google-genai Client, creating it lazily."""
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
            logger.info("gemini_provider_client_created")
        return self._client

    @property
    def model_id(self) -> str:
        """Return the default model ID."""
        return self._default_model

    @property
    def cost_per_1k_input_tokens(self) -> float:
        """Return the cost in USD per 1,000 input tokens (Flash pricing)."""
        return 0.0001

    @property
    def cost_per_1k_output_tokens(self) -> float:
        """Return the cost in USD per 1,000 output tokens (Flash pricing)."""
        return 0.0004

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 1.0,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a completion using Gemini.

        Args:
            prompt: The input prompt text.
            model: Optional model ID override.
            temperature: Sampling temperature. Default 1.0 per CLAUDE.md rules.
            response_format: Optional structured output format.

        Returns:
            A dict with text, model, token counts, and provider name.
        """
        client = self._get_client()
        model_id = model or self._default_model

        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
            )
            text = response.text or ""

            # Extract token counts from usage metadata
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

            return {
                "text": text,
                "model": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "provider": self.name,
            }
        except Exception as exc:
            logger.error("gemini_generate_failed", error=str(exc), model=model_id)
            raise

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured output conforming to a JSON schema.

        Calls generate with a response_format hint and parses the result.

        Args:
            prompt: The input prompt text.
            schema: JSON Schema the output must conform to.
            model: Optional model ID override.

        Returns:
            A dict with text, model, token counts, provider, and structured data.
        """
        result = await self.generate(
            prompt,
            model=model,
            response_format={"type": "json_object", "schema": schema},
        )
        try:
            parsed = json.loads(result["text"])
            result["structured"] = parsed
        except json.JSONDecodeError:
            logger.warning("gemini_structured_parse_failed", model=result.get("model"))
            result["structured"] = {}
        return result

    async def embed(self, text: str) -> list[float]:
        """Generate a vector embedding using Gemini embeddings.

        Delegates to the existing embeddings module.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        from rulerepo_server.adapters.gemini.embeddings import generate_embedding

        client = self._get_client()
        return await generate_embedding(client, text)

    async def count_tokens(self, text: str) -> int:
        """Estimate the token count for a text string.

        Uses a rough heuristic of ~4 characters per token.
        This avoids an API call for simple estimation.

        Args:
            text: The input text.

        Returns:
            Approximate number of tokens.
        """
        return len(text) // 4

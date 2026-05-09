"""LLM provider router -- selects provider with primary -> fallback chain.

All LLM calls in the application MUST go through this router.
Never call a provider directly from business logic.

See CLAUDE.md §9 and IMPROVEMENT.md RR-010.
"""

from __future__ import annotations

import json
from typing import Any

from rulerepo_server.adapters.llm.base import LLMProvider
from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class LLMRouter:
    """Routes LLM calls to the configured provider with fallback support.

    Configuration via environment:
        LLM_PROVIDER_PRIMARY=gemini (default)
        LLM_PROVIDER_FALLBACK=anthropic,openai
        LLM_TENANT_OVERRIDES={"hr-confidential": "local"}

    The router lazily initializes providers on first use and caches them.
    Scope-based overrides allow routing confidential content to self-hosted
    providers.
    """

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._primary_name: str = ""
        self._fallback_names: list[str] = []
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazily initialize providers from configuration."""
        if self._initialized:
            return
        settings = get_settings()
        self._primary_name = settings.llm_provider_primary
        fallback_str = settings.llm_provider_fallback
        self._fallback_names = [f.strip() for f in fallback_str.split(",") if f.strip()] if fallback_str else []

        self._register_providers()
        self._initialized = True

        logger.info(
            "llm_router_initialized",
            primary=self._primary_name,
            fallbacks=self._fallback_names,
            available=list(self._providers.keys()),
        )

    def _register_providers(self) -> None:
        """Register all available providers based on configuration."""
        settings = get_settings()

        # Always try to register Gemini if API key is present
        if settings.gemini_api_key:
            try:
                from rulerepo_server.adapters.llm.gemini import GeminiProvider

                self._providers["gemini"] = GeminiProvider()
            except Exception as exc:
                logger.warning("gemini_provider_init_failed", error=str(exc))

        # Register Anthropic if API key present
        if settings.anthropic_api_key:
            try:
                from rulerepo_server.adapters.llm.anthropic import AnthropicProvider

                self._providers["anthropic"] = AnthropicProvider()
            except Exception as exc:
                logger.warning("anthropic_provider_init_failed", error=str(exc))

        # Register OpenAI if API key present
        if settings.openai_api_key:
            try:
                from rulerepo_server.adapters.llm.openai import OpenAIProvider

                self._providers["openai"] = OpenAIProvider()
            except Exception as exc:
                logger.warning("openai_provider_init_failed", error=str(exc))

        # Register local/self-hosted if URL configured
        if settings.llm_provider_self_hosted_url:
            try:
                from rulerepo_server.adapters.llm.local import LocalProvider

                self._providers["local"] = LocalProvider()
            except Exception as exc:
                logger.warning("local_provider_init_failed", error=str(exc))

    def get_provider(self, *, scope: str | None = None) -> LLMProvider:
        """Get the appropriate provider for a given scope.

        Checks tenant overrides first, then returns primary provider,
        falling back through the chain if primary is unavailable.

        Args:
            scope: Optional scope string for tenant-based routing
                (e.g., "hr-confidential").

        Returns:
            The selected LLMProvider instance.

        Raises:
            RuntimeError: If no providers are configured.
        """
        self._ensure_initialized()

        # Check tenant/scope overrides
        if scope:
            settings = get_settings()
            overrides_str = settings.llm_tenant_overrides
            if overrides_str and overrides_str != "{}":
                try:
                    overrides = json.loads(overrides_str)
                    if scope in overrides:
                        override_name = overrides[scope]
                        if override_name in self._providers:
                            logger.info(
                                "llm_scope_override",
                                scope=scope,
                                provider=override_name,
                            )
                            return self._providers[override_name]
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        "llm_tenant_overrides_parse_failed",
                        raw=overrides_str,
                    )

        # Try primary
        if self._primary_name in self._providers:
            return self._providers[self._primary_name]

        # Try fallbacks in order
        for name in self._fallback_names:
            if name in self._providers:
                logger.warning(
                    "llm_using_fallback",
                    primary=self._primary_name,
                    fallback=name,
                )
                return self._providers[name]

        # Last resort: return any available provider
        if self._providers:
            name = next(iter(self._providers))
            logger.warning("llm_using_any_available", provider=name)
            return self._providers[name]

        raise RuntimeError(
            "No LLM providers configured. Set GEMINI_API_KEY or another provider key in the environment."
        )

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        scope: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate text through the router (convenience method).

        Args:
            prompt: The input prompt text.
            model: Optional model ID override.
            scope: Optional scope for provider routing.
            **kwargs: Additional arguments passed to the provider.

        Returns:
            The provider's response dict.
        """
        provider = self.get_provider(scope=scope)
        import time

        start = time.monotonic()
        result = await provider.generate(prompt, model=model, **kwargs)
        elapsed = (time.monotonic() - start) * 1000

        used_model = result.get("model", model or provider.name)
        tokens_in = result.get("input_tokens", 0)
        tokens_out = result.get("output_tokens", 0)

        logger.info(
            "llm_call_completed",
            model=used_model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=round(elapsed, 2),
            scope=scope or "general",
        )
        return result

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured output through the router (convenience method).

        Args:
            prompt: The input prompt text.
            schema: JSON Schema the output must conform to.
            model: Optional model ID override.
            scope: Optional scope for provider routing.

        Returns:
            The provider's response dict with a "structured" key.
        """
        provider = self.get_provider(scope=scope)
        return await provider.generate_structured(prompt, schema, model=model)

    async def embed(self, text: str, *, scope: str | None = None) -> list[float]:
        """Generate embedding through the router (convenience method).

        Args:
            text: The input text to embed.
            scope: Optional scope for provider routing.

        Returns:
            A list of floats representing the embedding vector.
        """
        provider = self.get_provider(scope=scope)
        return await provider.embed(text)


# Module-level singleton
_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    """Return the singleton LLM router.

    Returns:
        The global LLMRouter instance.
    """
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router

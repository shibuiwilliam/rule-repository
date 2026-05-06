"""Tests for LLM provider abstraction layer."""

from __future__ import annotations

import pytest

from rulerepo_server.adapters.llm.anthropic import AnthropicProvider
from rulerepo_server.adapters.llm.base import LLMProvider
from rulerepo_server.adapters.llm.local import LocalProvider
from rulerepo_server.adapters.llm.openai import OpenAIProvider


class TestLLMProviderProtocol:
    """Tests for Protocol compliance of all provider stubs."""

    def test_anthropic_is_llm_provider(self) -> None:
        provider = AnthropicProvider()
        assert isinstance(provider, LLMProvider)

    def test_openai_is_llm_provider(self) -> None:
        provider = OpenAIProvider()
        assert isinstance(provider, LLMProvider)

    def test_local_is_llm_provider(self) -> None:
        provider = LocalProvider()
        assert isinstance(provider, LLMProvider)

    def test_provider_names(self) -> None:
        assert AnthropicProvider.name == "anthropic"
        assert OpenAIProvider.name == "openai"
        assert LocalProvider.name == "local"


class TestAnthropicProvider:
    """Tests for the Anthropic provider stub."""

    @pytest.mark.asyncio
    async def test_generate_raises_not_implemented(self) -> None:
        provider = AnthropicProvider()
        with pytest.raises(NotImplementedError, match="ANTHROPIC_API_KEY"):
            await provider.generate("test prompt")

    @pytest.mark.asyncio
    async def test_embed_raises_not_implemented(self) -> None:
        provider = AnthropicProvider()
        with pytest.raises(NotImplementedError, match="ANTHROPIC_API_KEY"):
            await provider.embed("test text")

    @pytest.mark.asyncio
    async def test_generate_with_kwargs_raises(self) -> None:
        provider = AnthropicProvider()
        with pytest.raises(NotImplementedError):
            await provider.generate(
                "test",
                model="claude-sonnet-4-20250514",
                temperature=1.0,
                response_format={"type": "json"},
            )


class TestOpenAIProvider:
    """Tests for the OpenAI provider stub."""

    @pytest.mark.asyncio
    async def test_generate_raises_not_implemented(self) -> None:
        provider = OpenAIProvider()
        with pytest.raises(NotImplementedError, match="OPENAI_API_KEY"):
            await provider.generate("test prompt")

    @pytest.mark.asyncio
    async def test_embed_raises_not_implemented(self) -> None:
        provider = OpenAIProvider()
        with pytest.raises(NotImplementedError, match="OPENAI_API_KEY"):
            await provider.embed("test text")


class TestLocalProvider:
    """Tests for the local LLM provider stub."""

    @pytest.mark.asyncio
    async def test_generate_raises_not_implemented(self) -> None:
        provider = LocalProvider()
        with pytest.raises(NotImplementedError, match="LOCAL_LLM_ENDPOINT"):
            await provider.generate("test prompt")

    @pytest.mark.asyncio
    async def test_embed_raises_not_implemented(self) -> None:
        provider = LocalProvider()
        with pytest.raises(NotImplementedError, match="LOCAL_LLM_ENDPOINT"):
            await provider.embed("test text")

"""LLM provider abstraction layer.

Defines the LLMProvider Protocol and implementations for
multiple providers. The LLMRouter selects the active provider
based on configuration and scope-based overrides.

All LLM calls in business logic MUST go through the router.
See CLAUDE.md §9 for mandatory rules.
"""

from rulerepo_server.adapters.llm.base import LLMProvider
from rulerepo_server.adapters.llm.router import LLMRouter, get_llm_router

__all__ = ["LLMProvider", "LLMRouter", "get_llm_router"]

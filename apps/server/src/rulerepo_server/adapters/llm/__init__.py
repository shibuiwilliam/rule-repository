"""LLM provider abstraction layer.

Defines the LLMProvider Protocol and stub implementations for
multiple providers. The active provider is selected based on
configuration in core/llm.py.
"""

from rulerepo_server.adapters.llm.base import LLMProvider

__all__ = ["LLMProvider"]

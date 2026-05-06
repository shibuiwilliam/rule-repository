"""LLM configuration — centralized model selection and generation config.

Model IDs and thinking levels are read from Settings.
Never hardcode model IDs in business logic.

Sensitivity-aware routing: RESTRICTED rules are not sent to external LLMs;
they return NEEDS_CONFIRMATION until a self-hosted provider is configured.
"""

from __future__ import annotations

from dataclasses import dataclass

from rulerepo_server.core.config import get_settings


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for a Gemini API call.

    Attributes:
        model_id: The model to use (e.g., "gemini-3-flash-preview").
        thinking_level: Thinking depth ("minimal", "low", "medium", "high").
        skip_llm: If True, the caller should return NEEDS_CONFIRMATION
            instead of making an LLM call (used for RESTRICTED sensitivity).
    """

    model_id: str
    thinking_level: str = "low"
    skip_llm: bool = False


def get_default_config() -> LLMConfig:
    """Config for high-throughput routine tasks (Flash model, low thinking).

    Returns:
        LLMConfig for the default (fast) model.
    """
    settings = get_settings()
    return LLMConfig(model_id=settings.llm_default_model, thinking_level="low")


def get_judge_config() -> LLMConfig:
    """Config for high-stakes judgment tasks (Pro model, high thinking).

    Returns:
        LLMConfig for the judge (strongest reasoning) model.
    """
    settings = get_settings()
    return LLMConfig(model_id=settings.llm_judge_model, thinking_level="high")


def get_config_for_sensitivity(sensitivity: str) -> LLMConfig:
    """Select LLM config based on rule sensitivity level.

    Args:
        sensitivity: The rule's sensitivity level (PUBLIC, INTERNAL,
            CONFIDENTIAL, RESTRICTED).

    Returns:
        LLMConfig appropriate for the sensitivity level.
        For RESTRICTED, skip_llm=True until a self-hosted provider is available.
    """
    if sensitivity == "RESTRICTED":
        return LLMConfig(model_id="", skip_llm=True)
    return get_default_config()

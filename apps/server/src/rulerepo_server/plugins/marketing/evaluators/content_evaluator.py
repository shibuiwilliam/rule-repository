"""Content evaluator for marketing materials.

Evaluates marketing copy, advertisements, and promotional content
against rules for truthfulness, regulatory compliance (Keihyohou,
Yakkihou), brand guidelines, and claim substantiation.

See: CLAUDE.md SS12.5
"""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

LLMCallable = Callable[[str], Coroutine[Any, Any, str]]


def _build_content_narrative(payload: dict[str, Any]) -> str:
    """Build a narrative from marketing content fields.

    Args:
        payload: Marketing content payload.

    Returns:
        Formatted narrative string.
    """
    parts: list[str] = []

    content_type = payload.get("content_type", "general")
    parts.append(f"Content Type: {content_type}")

    if "channel" in payload:
        parts.append(f"Channel: {payload['channel']}")
    if "target_audience" in payload:
        parts.append(f"Target Audience: {payload['target_audience']}")
    if "product" in payload:
        parts.append(f"Product/Service: {payload['product']}")
    if "campaign" in payload:
        parts.append(f"Campaign: {payload['campaign']}")

    if "headline" in payload:
        parts.append(f"\nHeadline: {payload['headline']}")
    if "body_text" in payload:
        parts.append(f"\nBody Text:\n{payload['body_text']}")
    if "claims" in payload and isinstance(payload["claims"], list):
        parts.append("\nClaims Made:")
        for i, claim in enumerate(payload["claims"], 1):
            parts.append(f"  {i}. {claim}")
    if "disclaimer" in payload:
        parts.append(f"\nDisclaimer: {payload['disclaimer']}")

    if "cta" in payload:
        parts.append(f"Call to Action: {payload['cta']}")

    if "price_mentions" in payload:
        parts.append(f"Price Mentions: {payload['price_mentions']}")
    if "comparison_claims" in payload:
        parts.append(f"Comparative Claims: {payload['comparison_claims']}")

    if "images_described" in payload and isinstance(payload["images_described"], list):
        parts.append("\nVisual Content:")
        for desc in payload["images_described"]:
            parts.append(f"  - {desc}")

    if "legal_review_status" in payload:
        parts.append(f"Legal Review: {payload['legal_review_status']}")

    if "jurisdiction" in payload:
        parts.append(f"Target Market: {payload['jurisdiction']}")

    # Diff from previous version
    if "diff" in payload:
        parts.append(f"\n--- Changes from Previous Version ---\n{payload['diff']}")

    return "\n".join(parts)


def _format_rules_for_prompt(rules: list[dict[str, Any]]) -> str:
    """Format rules for the evaluation prompt.

    Args:
        rules: List of rule dicts.

    Returns:
        Formatted rules text.
    """
    parts: list[str] = []
    for i, rule in enumerate(rules, 1):
        parts.append(
            f"Rule {i} (ID: {rule.get('id', 'unknown')}):\n"
            f"  Statement: {rule.get('statement', '')}\n"
            f"  Modality: {rule.get('modality', 'MUST')}\n"
            f"  Severity: {rule.get('severity', 'MEDIUM')}"
        )
    return "\n\n".join(parts)


def _parse_verdict_response(
    response_text: str,
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Parse LLM response into per-rule verdict dicts.

    Args:
        response_text: Raw LLM response.
        rules: Rules that were evaluated.

    Returns:
        List of verdict dicts.
    """
    try:
        parsed = json.loads(response_text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "verdicts" in parsed:
            return parsed["verdicts"]
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    return [
        {
            "rule_id": rule.get("id", "unknown"),
            "verdict": "NEEDS_CONFIRMATION",
            "confidence": 0.5,
            "reasoning": ("Automated parsing of LLM response failed. Marketing compliance review required."),
            "raw_response": response_text[:500],
        }
        for rule in rules
    ]


class ContentEvaluator:
    """Evaluator for marketing content and promotional materials.

    Assesses marketing copy against rules for truthful advertising,
    regulatory compliance (Japan: Act against Unjustifiable Premiums
    and Misleading Representations / Keihyohou, Pharmaceutical and
    Medical Device Act / Yakkihou), brand guidelines, claim
    substantiation, and proper disclaimers.

    Args:
        llm_callable: Async function for LLM calls.
        prompt_template: Optional custom prompt template.
    """

    def __init__(
        self,
        llm_callable: LLMCallable | None = None,
        prompt_template: str | None = None,
    ) -> None:
        self._llm_callable = llm_callable
        self._prompt_template = prompt_template or self._load_default_prompt()

    @property
    def name(self) -> str:
        return "content_evaluator"

    @property
    def domain(self) -> str:
        return "marketing"

    @property
    def supported_subject_kinds(self) -> list[str]:
        return ["creative", "document"]

    def set_llm_callable(self, llm_callable: LLMCallable) -> None:
        """Set the LLM callable after construction.

        Args:
            llm_callable: Async function for LLM calls.
        """
        self._llm_callable = llm_callable

    async def evaluate(
        self,
        subject_payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Evaluate marketing content against marketing and compliance rules.

        Args:
            subject_payload: Marketing content data (body_text, claims, ...).
            rules: List of marketing/compliance rule dicts.
            context: Additional context (jurisdiction, channel, ...).

        Returns:
            List of verdict dicts, one per rule.

        Raises:
            PluginError: If no LLM callable is configured.
        """
        from rulerepo_server.plugins.base import PluginError

        if self._llm_callable is None:
            raise PluginError("ContentEvaluator requires an LLM callable. Call set_llm_callable() before evaluate().")

        narrative = _build_content_narrative(subject_payload)
        rules_text = _format_rules_for_prompt(rules)

        jurisdiction = subject_payload.get("jurisdiction") or context.get("jurisdiction", "global")

        prompt = self._prompt_template.format(
            content_narrative=narrative,
            rules=rules_text,
            jurisdiction=jurisdiction,
            content_type=subject_payload.get("content_type", "general"),
        )

        response_text = await self._llm_callable(prompt)
        return _parse_verdict_response(response_text, rules)

    @staticmethod
    def _load_default_prompt() -> str:
        """Load the default content evaluation prompt template."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "content_evaluation.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")

        return (
            "You are a marketing compliance assistant evaluating promotional "
            "content against advertising and regulatory rules.\n\n"
            "## Content\n{content_narrative}\n\n"
            "## Jurisdiction\n{jurisdiction}\n\n"
            "## Content Type\n{content_type}\n\n"
            "## Rules to Evaluate\n{rules}\n\n"
            "For each rule, return a JSON verdict object.\n"
            "Return a JSON array of verdict objects."
        )

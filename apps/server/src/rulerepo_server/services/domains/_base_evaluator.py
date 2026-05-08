"""Base domain evaluator — shared LLM evaluation logic.

All domain evaluators inherit from this class to get LLM-routed
evaluation with structured output parsing, prompt injection defense,
and cost tracking.  Each domain only needs to provide its system
prompt and focus areas.

See CLAUDE.md §9 (LLM rules) and §14 Rule #3 (always use the router).
"""

from __future__ import annotations

import json
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Structured output schema for verdict responses
_VERDICT_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "rule_id": {"type": "string"},
            "verdict": {"type": "string", "enum": ["ALLOW", "DENY", "NEEDS_CONFIRMATION"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {"type": "string"},
        },
        "required": ["rule_id", "verdict", "confidence", "reasoning"],
    },
}


class BaseDomainEvaluator:
    """Base class for domain-specific evaluators.

    Subclasses set ``domain_name`` and ``system_prompt`` to customize
    behavior.  The LLM call, prompt construction, safety wrapping,
    and response parsing are handled here.
    """

    domain_name: str = "unknown"
    system_prompt: str = ""

    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Evaluate an artifact against rules using the LLM router.

        Args:
            context: LLM-ready context from the domain's ContextAssembler.
            rules: List of rule dicts to check against.
            **kwargs: Additional arguments (tenant_id, etc.).

        Returns:
            List of verdict dicts with rule_id, verdict, confidence, reasoning.
        """
        if not rules:
            return []

        # Build the evaluation prompt
        rules_text = self._format_rules(rules)
        prompt = self._build_prompt(context, rules_text)

        # Wrap user content for injection defense
        from rulerepo_server.core.llm_safety import get_safety_system_suffix, wrap_user_content

        safe_prompt = f"{self.system_prompt}\n{get_safety_system_suffix()}\n\n{wrap_user_content(prompt)}"

        # Call LLM through the router (CLAUDE.md §14 Rule #3)
        try:
            from rulerepo_server.adapters.llm.router import get_llm_router

            router = get_llm_router()
            result = await router.generate(
                safe_prompt,
                scope=self.domain_name,
            )
            response_text = result.get("text", "")

            # Parse structured response
            verdicts = self._parse_verdicts(response_text, rules)

        except Exception as exc:
            logger.warning(
                "llm_evaluation_failed",
                domain=self.domain_name,
                error=str(exc),
                rules_count=len(rules),
            )
            # Fallback: return NEEDS_CONFIRMATION for all rules
            verdicts = self._fallback_verdicts(rules, reason=f"LLM unavailable: {exc}")

        logger.info(
            "domain_evaluation_complete",
            domain=self.domain_name,
            rules_evaluated=len(rules),
            verdicts=len(verdicts),
        )
        return verdicts

    def _format_rules(self, rules: list[dict[str, Any]]) -> str:
        """Format rules into a numbered list for the LLM."""
        lines: list[str] = []
        for i, rule in enumerate(rules, 1):
            rule_id = rule.get("id", f"rule-{i}")
            statement = rule.get("statement", "")
            severity = rule.get("severity", "MEDIUM")
            modality = rule.get("modality", "MUST")
            lines.append(f"{i}. [{rule_id}] ({modality}, {severity}): {statement}")
        return "\n".join(lines)

    def _build_prompt(self, context: str, rules_text: str) -> str:
        """Build the full evaluation prompt."""
        return f"""ARTIFACT TO EVALUATE:
{context}

RULES TO CHECK:
{rules_text}

For each rule, respond with a JSON array of verdicts."""

    def _parse_verdicts(self, response_text: str, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse LLM response into structured verdicts."""
        # Try to extract JSON from the response
        try:
            # Handle responses that may have markdown code blocks
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            parsed = json.loads(text)
            if isinstance(parsed, list):
                return self._validate_verdicts(parsed, rules)
        except (json.JSONDecodeError, IndexError):
            pass

        # If parsing fails, return NEEDS_CONFIRMATION
        logger.warning(
            "verdict_parse_failed",
            domain=self.domain_name,
            response_preview=response_text[:200],
        )
        return self._fallback_verdicts(rules, reason="Could not parse LLM response")

    def _validate_verdicts(self, parsed: list[Any], rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate parsed verdicts and ensure all rules are covered."""
        valid_verdicts = {"ALLOW", "DENY", "NEEDS_CONFIRMATION"}
        result: list[dict[str, Any]] = []

        for item in parsed:
            if not isinstance(item, dict):
                continue
            verdict = item.get("verdict", "NEEDS_CONFIRMATION")
            if verdict not in valid_verdicts:
                verdict = "NEEDS_CONFIRMATION"
            result.append(
                {
                    "rule_id": str(item.get("rule_id", "")),
                    "rule_statement": item.get("rule_statement", ""),
                    "verdict": verdict,
                    "confidence": min(max(float(item.get("confidence", 0.5)), 0.0), 1.0),
                    "reasoning": item.get("reasoning", ""),
                }
            )

        # Add NEEDS_CONFIRMATION for any rules not covered
        covered_ids = {v["rule_id"] for v in result}
        for rule in rules:
            rid = str(rule.get("id", ""))
            if rid and rid not in covered_ids:
                result.append(
                    {
                        "rule_id": rid,
                        "rule_statement": rule.get("statement", ""),
                        "verdict": "NEEDS_CONFIRMATION",
                        "confidence": 0.3,
                        "reasoning": "Rule not addressed in LLM response",
                    }
                )

        return result

    def _fallback_verdicts(self, rules: list[dict[str, Any]], *, reason: str) -> list[dict[str, Any]]:
        """Generate NEEDS_CONFIRMATION verdicts as fallback."""
        return [
            {
                "rule_id": str(rule.get("id", "")),
                "rule_statement": rule.get("statement", ""),
                "verdict": "NEEDS_CONFIRMATION",
                "confidence": 0.0,
                "reasoning": reason,
            }
            for rule in rules
        ]

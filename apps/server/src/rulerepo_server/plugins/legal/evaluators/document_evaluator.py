"""Document evaluator for contract and legal document review.

Evaluates contract clauses, terms, and legal documents against
organizational rules for NDA, MSA, procurement, and compliance.

See: CLAUDE.md SS12.2
"""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

LLMCallable = Callable[[str], Coroutine[Any, Any, str]]


def _build_document_narrative(payload: dict[str, Any]) -> str:
    """Build a narrative from contract/document fields.

    Args:
        payload: Document payload.

    Returns:
        Formatted narrative string.
    """
    parts: list[str] = []

    contract_type = payload.get("contract_type", "unknown")
    parts.append(f"Document Type: {contract_type}")

    if "title" in payload:
        parts.append(f"Title: {payload['title']}")
    if "counterparty" in payload:
        parts.append(f"Counterparty: {payload['counterparty']}")
    if "governing_law" in payload:
        parts.append(f"Governing Law: {payload['governing_law']}")
    if "effective_date" in payload:
        parts.append(f"Effective Date: {payload['effective_date']}")
    if "expiration_date" in payload:
        parts.append(f"Expiration Date: {payload['expiration_date']}")
    if "contract_value" in payload:
        parts.append(f"Contract Value: {payload['contract_value']}")

    if "clause_text" in payload:
        parts.append(f"\n--- Clause Under Review ---\n{payload['clause_text']}")
    if "clause_type" in payload:
        parts.append(f"Clause Type: {payload['clause_type']}")

    if "clauses" in payload and isinstance(payload["clauses"], list):
        parts.append("\n--- All Clauses ---")
        for i, clause in enumerate(payload["clauses"], 1):
            clause_type = clause.get("type", "unknown")
            clause_text = clause.get("text", "")
            parts.append(f"\nClause {i} ({clause_type}):\n{clause_text}")

    if "diff" in payload:
        parts.append(f"\n--- Changes from Previous Version ---\n{payload['diff']}")

    if "review_type" in payload:
        parts.append(f"\nReview Type: {payload['review_type']}")

    # Additional context
    for key in ("notes", "special_terms", "related_agreements"):
        if key in payload:
            parts.append(f"{key}: {payload[key]}")

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
            f"  Severity: {rule.get('severity', 'MEDIUM')}\n"
            f"  Legal Force: {rule.get('legal_force', 'policy')}"
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
            "reasoning": "Automated parsing of LLM response failed. Legal review required.",
            "raw_response": response_text[:500],
        }
        for rule in rules
    ]


class DocumentEvaluator:
    """Evaluator for contract and legal document review.

    Assesses contract clauses and legal documents against organizational
    rules covering NDA terms, MSA requirements, procurement regulations,
    and compliance standards. All remediations are marked as non-auto-applicable
    by default -- auto-applying contract changes is dangerous.

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
        return "document_evaluator"

    @property
    def domain(self) -> str:
        return "legal"

    @property
    def supported_subject_kinds(self) -> list[str]:
        return ["clause_set", "document"]

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
        """Evaluate a contract or legal document against rules.

        Args:
            subject_payload: Document data (clause_text, contract_type, ...).
            rules: List of legal rule dicts.
            context: Additional context (jurisdiction, review_type, ...).

        Returns:
            List of verdict dicts, one per rule.

        Raises:
            PluginError: If no LLM callable is configured.
        """
        from rulerepo_server.plugins.base import PluginError

        if self._llm_callable is None:
            raise PluginError("DocumentEvaluator requires an LLM callable. Call set_llm_callable() before evaluate().")

        narrative = _build_document_narrative(subject_payload)
        rules_text = _format_rules_for_prompt(rules)

        governing_law = subject_payload.get("governing_law") or context.get("jurisdiction", "Not specified")

        prompt = self._prompt_template.format(
            document_narrative=narrative,
            rules=rules_text,
            governing_law=governing_law,
            contract_type=subject_payload.get("contract_type", "general"),
        )

        response_text = await self._llm_callable(prompt)
        verdicts = _parse_verdict_response(response_text, rules)

        # Ensure all remediations are marked non-auto-applicable
        for verdict in verdicts:
            remediation = verdict.get("remediation")
            if isinstance(remediation, dict):
                remediation["auto_applicable"] = False
                if "requires_counterparty_consent" not in remediation:
                    remediation["requires_counterparty_consent"] = True

        return verdicts

    @staticmethod
    def _load_default_prompt() -> str:
        """Load the default document evaluation prompt template."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "document_evaluation.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")

        return (
            "You are a legal compliance assistant reviewing a contract or "
            "legal document against organizational rules.\n\n"
            "## Document\n{document_narrative}\n\n"
            "## Governing Law\n{governing_law}\n\n"
            "## Contract Type\n{contract_type}\n\n"
            "## Rules to Evaluate\n{rules}\n\n"
            "For each rule, return a JSON verdict object.\n"
            "Return a JSON array of verdict objects."
        )

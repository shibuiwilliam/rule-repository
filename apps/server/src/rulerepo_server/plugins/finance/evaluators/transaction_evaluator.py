"""Transaction evaluator for financial compliance.

Evaluates expense claims, purchase orders, and financial transactions
against finance rules covering approval thresholds, documentation
requirements, segregation of duties, and anti-bribery controls.

See: CLAUDE.md SS12.4
"""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

LLMCallable = Callable[[str], Coroutine[Any, Any, str]]


def _build_transaction_narrative(payload: dict[str, Any]) -> str:
    """Build a narrative from transaction/expense fields.

    Args:
        payload: Transaction payload.

    Returns:
        Formatted narrative string.
    """
    parts: list[str] = []

    tx_type = payload.get("transaction_type", payload.get("expense_type", "general"))
    parts.append(f"Transaction Type: {tx_type}")

    if "amount" in payload:
        currency = payload.get("currency", "JPY")
        parts.append(f"Amount: {payload['amount']} {currency}")

    if "employee_id" in payload or "requester" in payload:
        requester = payload.get("employee_id", payload.get("requester", ""))
        parts.append(f"Requester: {requester}")

    if "department" in payload:
        parts.append(f"Department: {payload['department']}")

    if "date" in payload:
        parts.append(f"Date: {payload['date']}")

    if "vendor" in payload or "payee" in payload:
        parts.append(f"Vendor/Payee: {payload.get('vendor', payload.get('payee', ''))}")

    if "description" in payload:
        parts.append(f"Description: {payload['description']}")

    if "category" in payload:
        parts.append(f"Category: {payload['category']}")

    if "cost_center" in payload:
        parts.append(f"Cost Center: {payload['cost_center']}")

    if "project" in payload:
        parts.append(f"Project: {payload['project']}")

    # Approval chain
    if "approvals" in payload and isinstance(payload["approvals"], list):
        parts.append("\n--- Approval Chain ---")
        for approval in payload["approvals"]:
            approver = approval.get("approver", "unknown")
            status = approval.get("status", "pending")
            parts.append(f"  {approver}: {status}")

    # Receipts and documentation
    if "receipt_attached" in payload:
        parts.append(f"Receipt Attached: {'Yes' if payload['receipt_attached'] else 'No'}")

    if "attendees" in payload:
        parts.append(f"Attendees: {payload['attendees']}")

    if "purpose" in payload:
        parts.append(f"Business Purpose: {payload['purpose']}")

    # Related transactions (for pattern detection)
    related = payload.get("related_transactions")
    if isinstance(related, list) and related:
        parts.append(f"\n--- Related Transactions ({len(related)}) ---")
        total = sum(t.get("amount", 0) for t in related)
        parts.append(f"Total related amount: {total}")
        for i, tx in enumerate(related[:5], 1):
            parts.append(
                f"  {i}. {tx.get('date', '?')} - {tx.get('amount', 0)} "
                f"{tx.get('currency', 'JPY')} - {tx.get('description', '')}"
            )
        if len(related) > 5:
            parts.append(f"  ... and {len(related) - 5} more")

    # Additional context
    if "jurisdiction" in payload:
        parts.append(f"Jurisdiction: {payload['jurisdiction']}")

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
            "reasoning": "Automated parsing of LLM response failed. Finance review required.",
            "raw_response": response_text[:500],
        }
        for rule in rules
    ]


class TransactionEvaluator:
    """Evaluator for financial transactions and expense claims.

    Assesses transactions against finance rules covering approval
    thresholds, documentation requirements, segregation of duties,
    entertainment expense limits, and anti-bribery controls.

    Every evaluation goes through the audit subsystem when classification
    is CONFIDENTIAL or above.

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
        return "transaction_evaluator"

    @property
    def domain(self) -> str:
        return "finance"

    @property
    def supported_subject_kinds(self) -> list[str]:
        return ["transaction"]

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
        """Evaluate a financial transaction against finance rules.

        Args:
            subject_payload: Transaction data (amount, type, vendor, ...).
            rules: List of finance rule dicts.
            context: Additional context (jurisdiction, ...).

        Returns:
            List of verdict dicts, one per rule.

        Raises:
            PluginError: If no LLM callable is configured.
        """
        from rulerepo_server.plugins.base import PluginError

        if self._llm_callable is None:
            raise PluginError(
                "TransactionEvaluator requires an LLM callable. Call set_llm_callable() before evaluate()."
            )

        narrative = _build_transaction_narrative(subject_payload)
        rules_text = _format_rules_for_prompt(rules)

        jurisdiction = subject_payload.get("jurisdiction") or context.get("jurisdiction", "global")

        amount = subject_payload.get("amount", 0)
        currency = subject_payload.get("currency", "JPY")

        prompt = self._prompt_template.format(
            transaction_narrative=narrative,
            rules=rules_text,
            jurisdiction=jurisdiction,
            amount=amount,
            currency=currency,
        )

        response_text = await self._llm_callable(prompt)
        verdicts = _parse_verdict_response(response_text, rules)

        # Ensure all remediations are non-auto-applicable for finance
        for verdict in verdicts:
            remediation = verdict.get("remediation")
            if isinstance(remediation, dict):
                remediation["auto_applicable"] = False

        return verdicts

    @staticmethod
    def _load_default_prompt() -> str:
        """Load the default transaction evaluation prompt template."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "transaction_evaluation.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")

        return (
            "You are a financial compliance assistant evaluating a transaction "
            "against finance and compliance rules.\n\n"
            "## Transaction Details\n{transaction_narrative}\n\n"
            "## Jurisdiction\n{jurisdiction}\n\n"
            "## Amount\n{amount} {currency}\n\n"
            "## Rules to Evaluate\n{rules}\n\n"
            "For each rule, return a JSON verdict object.\n"
            "Return a JSON array of verdict objects."
        )

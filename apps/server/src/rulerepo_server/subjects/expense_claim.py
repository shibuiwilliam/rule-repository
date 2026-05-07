"""Transaction subject adapter — handles expense and financial evaluations.

Evaluates expense claims and transactions against finance and compliance rules.
See: CLAUDE.md §12.4
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext, ExpenseRemediation
from rulerepo_server.domain.subject import PromptFormat, SubjectKind
from rulerepo_server.subjects.registry import register


@register(SubjectKind.TRANSACTION)
class TransactionAdapter:
    """Adapter for transaction / expense claim evaluations."""

    kind = SubjectKind.TRANSACTION

    @property
    def identifier(self) -> str:
        return "transaction"

    @property
    def subject_type(self) -> str:
        """Backward-compatible alias."""
        return self.kind.value

    def parse_payload(self, payload: dict[str, Any]) -> EvaluationContext:
        """Parse an expense claim payload into an EvaluationContext."""
        return EvaluationContext(
            facts=payload,
            intent="expense_review",
            narrative=_build_narrative(payload),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from expense type and jurisdiction."""
        scopes = ["finance", "finance/expenses"]
        expense_type = payload.get("expense_type", "").lower()
        if "travel" in expense_type:
            scopes.append("finance/travel")
        if "entertainment" in expense_type:
            scopes.append("finance/entertainment")
            scopes.append("compliance/anti-bribery")

        jurisdiction = payload.get("jurisdiction", "")
        if jurisdiction:
            scopes.append(f"finance/expenses/{jurisdiction.lower()}")

        return list(dict.fromkeys(scopes))

    def render_for_llm(self, facts: dict[str, Any], format: PromptFormat = PromptFormat.FULL) -> str:
        """Format the expense/transaction as prompt context."""
        return _build_narrative(facts)

    def format_prompt_context(self, payload: dict[str, Any]) -> str:
        """Legacy alias for render_for_llm."""
        return self.render_for_llm(payload)

    def extract_features(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract transaction-specific features for rule selection."""
        return {
            "expense_type": payload.get("expense_type", ""),
            "amount": payload.get("amount"),
            "has_receipt": payload.get("receipt_attached", False),
            "jurisdiction": payload.get("jurisdiction", ""),
        }

    def parse_remediation(self, raw: dict[str, Any]) -> ExpenseRemediation | None:
        """Parse an expense remediation from raw LLM output."""
        desc = raw.get("description", "")
        if not desc and not raw.get("required_documentation"):
            return None
        return ExpenseRemediation(
            type=raw.get("type", "workflow"),
            description=desc,
            required_documentation=raw.get("required_documentation", ""),
            revised_amount=raw.get("revised_amount"),
            approval_level=raw.get("approval_level", ""),
            auto_applicable=False,
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        """Financial data may contain PII."""
        pii = []
        if "employee_id" in payload:
            pii.append("employee_id")
        if "account_number" in payload:
            pii.append("account_number")
        return pii


def _build_narrative(payload: dict[str, Any]) -> str:
    parts = [f"Expense Claim: {payload.get('expense_type', 'general')}"]
    if "amount" in payload:
        currency = payload.get("currency", "JPY")
        parts.append(f"Amount: {payload['amount']} {currency}")
    if "employee_id" in payload:
        parts.append(f"Claimant: {payload['employee_id']}")
    if "date" in payload:
        parts.append(f"Date: {payload['date']}")
    if "description" in payload:
        parts.append(f"Description: {payload['description']}")
    if "attendees" in payload:
        parts.append(f"Attendees: {payload['attendees']}")
    if "receipt_attached" in payload:
        parts.append(f"Receipt: {'Yes' if payload['receipt_attached'] else 'No'}")
    return "\n".join(parts)


# Backward-compatible alias
ExpenseClaimAdapter = TransactionAdapter

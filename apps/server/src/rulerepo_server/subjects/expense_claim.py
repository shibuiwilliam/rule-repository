"""Expense claim subject adapter — handles expense submission evaluations.

Evaluates expense claims against finance and compliance rules.
See: IMPROVEMENT.md Phase 7b
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext


class ExpenseClaimAdapter:
    """Adapter for expense claim evaluations."""

    @property
    def subject_type(self) -> str:
        return "expense_claim"

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

    def format_prompt_context(self, payload: dict[str, Any]) -> str:
        return _build_narrative(payload)


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

"""Context assembler for TransactionSubject.

Extracts context from financial or commercial transactions such as
expense claims, purchase orders, and wire transfers.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation_subject import TransactionSubject


async def assemble_context(subject: TransactionSubject) -> dict[str, Any]:
    """Assemble evaluation context from a transaction subject."""
    context: dict[str, Any] = {
        "kind": "transaction",
        "transaction_type": subject.transaction_type,
        "amount": str(subject.amount),
        "currency": subject.currency,
        "counterparties": subject.counterparties,
        "line_items": subject.line_items,
    }
    if subject.actor_id:
        context["actor_id"] = subject.actor_id
    if subject.occurred_at:
        context["occurred_at"] = subject.occurred_at.isoformat()
    if subject.metadata:
        context["metadata"] = subject.metadata
    return context

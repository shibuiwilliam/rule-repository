"""Context assembler for DecisionRequestSubject.

Extracts context from generic approval requests in workflow and
decision-management systems.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation_subject import DecisionRequestSubject


async def assemble_context(subject: DecisionRequestSubject) -> dict[str, Any]:
    """Assemble evaluation context from a decision request subject."""
    context: dict[str, Any] = {
        "kind": "decision_request",
        "request_type": subject.request_type,
        "description": subject.description,
        "options": subject.options,
        "context_data": subject.context_data,
    }
    if subject.actor_id:
        context["actor_id"] = subject.actor_id
    if subject.metadata:
        context["metadata"] = subject.metadata
    return context

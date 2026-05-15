"""Context assembler for BusinessEventSubject.

Extracts context from business event payloads such as HR events,
attendance records, and workflow transitions.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation_subject import BusinessEventSubject


async def assemble_context(subject: BusinessEventSubject) -> dict[str, Any]:
    """Assemble evaluation context from a business event subject."""
    context: dict[str, Any] = {
        "kind": "business_event",
        "event_type": subject.event_type,
        "payload": subject.payload,
    }
    if subject.actor_id:
        context["actor_id"] = subject.actor_id
    if subject.occurred_at:
        context["occurred_at"] = subject.occurred_at.isoformat()
    if subject.metadata:
        context["metadata"] = subject.metadata
    return context

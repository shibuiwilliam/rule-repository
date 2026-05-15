"""Context assembler for CommunicationSubject.

Extracts context from outbound messages and public artifacts such as
emails, social media posts, and internal chat messages.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation_subject import CommunicationSubject


async def assemble_context(subject: CommunicationSubject) -> dict[str, Any]:
    """Assemble evaluation context from a communication subject."""
    context: dict[str, Any] = {
        "kind": "communication",
        "channel": subject.channel,
        "sender_id": subject.sender_id,
        "recipient_ids": subject.recipient_ids,
        "content": subject.content,
        "attachments": subject.attachments,
    }
    if subject.actor_id:
        context["actor_id"] = subject.actor_id
    if subject.metadata:
        context["metadata"] = subject.metadata
    return context

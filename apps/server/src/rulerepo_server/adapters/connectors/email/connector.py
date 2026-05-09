"""Email connector implementation.

Normalizes IMAP-fetched email messages into Message surface subjects
for evaluation.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.adapters.connectors.base import SubjectConnector


class EmailConnector(SubjectConnector):
    """Connector for email messages fetched via IMAP."""

    @property
    def name(self) -> str:
        return "email"

    @property
    def supported_surfaces(self) -> list[str]:
        return ["message"]

    async def normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """Normalize an email event into a Message surface subject.

        Expects a dict with standard email fields: ``from``, ``to``,
        ``subject``, ``body``, ``date``, ``message_id``.

        Args:
            event: Parsed email data.

        Returns:
            Dict compatible with EvaluationSubjectPayload for the Message surface.
        """
        sender = event.get("from", "unknown")
        recipients = event.get("to", [])
        if isinstance(recipients, str):
            recipients = [recipients]

        return {
            "surface": "message",
            "identifier": event.get("message_id", f"email:{sender}:{event.get('date', '')}"),
            "payload": {
                "content": event.get("body", ""),
                "channel": "email",
                "channel_type": "email",
                "subject_line": event.get("subject", ""),
                "recipients": recipients,
                "cc": event.get("cc", []),
                "attachments": [a.get("filename", "") for a in event.get("attachments", [])],
            },
            "facts": {
                "platform": "email",
                "sender": sender,
                "recipient_count": len(recipients),
                "has_attachments": bool(event.get("attachments")),
            },
            "actor": {
                "kind": "human",
                "identifier": f"email:{sender}",
            },
            "timestamp": event.get("date", datetime.now(UTC).isoformat()),
            "locale": "en",
        }

    async def validate_connection(self) -> bool:
        """Check that IMAP credentials are configured."""
        return all(os.environ.get(var) for var in ("EMAIL_IMAP_HOST", "EMAIL_IMAP_USER", "EMAIL_IMAP_PASSWORD"))

    async def list_event_types(self) -> list[str]:
        return ["incoming_email", "outgoing_email"]

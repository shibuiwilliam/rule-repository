"""Email event payload normalizer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rulerepo_server.gateway.normalizers.base import EventNormalizer
from rulerepo_server.gateway.schemas import NormalizedEvent


class EmailNormalizer(EventNormalizer):
    """Normalizes email webhook payloads into NormalizedEvent.

    Supports: generic email webhook format with from, to, subject, body fields.
    Can be adapted for SendGrid, Mailgun, or custom SMTP webhook formats.
    """

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        """Convert an email webhook payload."""
        sender = payload.get("from", payload.get("sender", "unknown"))
        recipients = payload.get("to", payload.get("recipients", []))
        recipients_str = ", ".join(recipients[:5]) if isinstance(recipients, list) else str(recipients)

        subject = payload.get("subject", "(no subject)")
        body = payload.get("body", payload.get("text", ""))

        return NormalizedEvent(
            source="email",
            event_type="email.received",
            actor=sender,
            subject=f"Email: {subject[:200]}",
            metadata={
                "from": sender,
                "to": recipients_str,
                "subject": subject[:500],
                "body_preview": body[:1000] if isinstance(body, str) else "",
                "has_attachments": bool(payload.get("attachments")),
            },
            raw_payload=payload,
            timestamp=datetime.now(tz=UTC),
        )

"""Message subject — the unit of evaluation for communications.

See CLAUDE.md §14.6.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Message:
    """Subject representing a communication message.

    Attributes:
        channel: Communication channel (e.g., "slack", "email", "teams").
        content: Message text content.
        sender: Sender identifier.
        recipients: List of recipient identifiers.
        channel_name: Name of the channel or thread.
        is_external: Whether the message is external-facing.
        attachments: List of attachment descriptions.
        facts: Additional structured facts.
        timestamp: When the message was sent.
        locale: Locale of the message content.
    """

    channel: str
    content: str = ""
    sender: str = ""
    recipients: list[str] = field(default_factory=list)
    channel_name: str = ""
    is_external: bool = False
    attachments: list[str] = field(default_factory=list)
    facts: dict[str, object] = field(default_factory=dict)
    timestamp: datetime | None = None
    locale: str = "en"

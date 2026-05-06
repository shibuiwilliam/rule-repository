"""Microsoft Teams event payload normalizer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rulerepo_server.gateway.normalizers.base import EventNormalizer
from rulerepo_server.gateway.schemas import NormalizedEvent


class TeamsNormalizer(EventNormalizer):
    """Normalizes Microsoft Teams activity payloads into NormalizedEvent.

    Supports: Bot Framework Activity format for message events.
    """

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        """Convert a Teams activity payload."""
        activity_type = payload.get("type", "message")
        text = payload.get("text", "")
        from_user = payload.get("from", {})
        user_name = from_user.get("name", "unknown")
        conversation = payload.get("conversation", {})
        channel_id = conversation.get("id", "unknown")

        return NormalizedEvent(
            source="teams",
            event_type=activity_type,
            actor=user_name,
            subject=f"Teams message: {text[:200]}",
            metadata={
                "channel_id": channel_id,
                "text": text[:1000],
                "conversation_type": conversation.get("conversationType", "personal"),
                "tenant_id": payload.get("channelData", {}).get("tenant", {}).get("id"),
            },
            raw_payload=payload,
            timestamp=datetime.now(tz=UTC),
        )

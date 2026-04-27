"""Slack event payload normalizer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rulerepo_server.gateway.normalizers.base import EventNormalizer
from rulerepo_server.gateway.schemas import NormalizedEvent


class SlackNormalizer(EventNormalizer):
    """Normalizes Slack event payloads into NormalizedEvent."""

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        """Convert a Slack event payload.

        Supports: message events and Slack Events API format.
        """
        event = payload.get("event", payload)
        event_type = event.get("type", "message")
        subtype = event.get("subtype", "")
        full_type = f"message.{subtype}" if subtype else event_type

        text = event.get("text", "")
        user = event.get("user", "unknown")
        channel = event.get("channel", "unknown")

        return NormalizedEvent(
            source="slack",
            event_type=full_type,
            actor=user,
            subject=f"Slack message in #{channel}: {text[:200]}",
            metadata={
                "channel": channel,
                "text": text[:1000],
                "thread_ts": event.get("thread_ts"),
                "team": payload.get("team_id"),
            },
            raw_payload=payload,
            timestamp=datetime.now(tz=UTC),
        )

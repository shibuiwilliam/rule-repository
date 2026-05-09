"""Slack connector implementation.

Normalizes Slack Events API payloads (message events) into Message surface
subjects for evaluation.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.adapters.connectors.base import SubjectConnector


class SlackConnector(SubjectConnector):
    """Connector for Slack message and channel events."""

    @property
    def name(self) -> str:
        return "slack"

    @property
    def supported_surfaces(self) -> list[str]:
        return ["message"]

    async def normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """Normalize a Slack Events API payload into a Message surface subject.

        Extracts message text, channel, user, and timestamp from the event.

        Args:
            event: Raw Slack event payload (the inner ``event`` object).

        Returns:
            Dict compatible with EvaluationSubjectPayload for the Message surface.
        """
        slack_event = event.get("event", event)
        channel = slack_event.get("channel", "")
        user = slack_event.get("user", "unknown")
        text = slack_event.get("text", "")
        ts = slack_event.get("ts", "")
        thread_ts = slack_event.get("thread_ts")

        return {
            "surface": "message",
            "identifier": f"slack:{channel}:{ts}",
            "payload": {
                "content": text,
                "channel": channel,
                "channel_type": slack_event.get("channel_type", "channel"),
                "thread_ts": thread_ts,
                "attachments": slack_event.get("attachments", []),
            },
            "facts": {
                "platform": "slack",
                "user": user,
                "team": event.get("team_id", ""),
            },
            "actor": {
                "kind": "human",
                "identifier": f"slack:{user}",
            },
            "timestamp": datetime.now(UTC).isoformat(),
            "locale": "en",
        }

    async def validate_connection(self) -> bool:
        """Check that SLACK_BOT_TOKEN is configured."""
        return bool(os.environ.get("SLACK_BOT_TOKEN"))

    async def list_event_types(self) -> list[str]:
        return ["message", "message.channels", "message.groups", "message.im"]

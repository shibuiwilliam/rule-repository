"""Microsoft Teams connector implementation.

Normalizes Microsoft Teams Bot Framework activity events into Message
surface subjects for evaluation.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.adapters.connectors.base import SubjectConnector


class TeamsConnector(SubjectConnector):
    """Connector for Microsoft Teams message events."""

    @property
    def name(self) -> str:
        return "teams"

    @property
    def supported_surfaces(self) -> list[str]:
        return ["message"]

    async def normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """Normalize a Teams Bot Framework activity into a Message surface subject.

        Extracts message text, channel, and sender from the activity payload.

        Args:
            event: Raw Teams Bot Framework activity payload.

        Returns:
            Dict compatible with EvaluationSubjectPayload for the Message surface.
        """
        activity_type = event.get("type", "message")
        sender = event.get("from", {})
        sender_id = sender.get("id", sender.get("aadObjectId", "unknown"))
        sender_name = sender.get("name", "")
        conversation = event.get("conversation", {})
        channel_id = conversation.get("id", event.get("channelId", ""))
        text = event.get("text", "")
        activity_id = event.get("id", "")

        return {
            "surface": "message",
            "identifier": f"teams:{channel_id}:{activity_id}",
            "payload": {
                "content": text,
                "channel": channel_id,
                "channel_type": conversation.get("conversationType", "channel"),
                "mentions": [
                    m.get("mentioned", {}).get("name", "")
                    for m in event.get("entities", [])
                    if m.get("type") == "mention"
                ],
                "attachments": [a.get("name", a.get("contentType", "")) for a in event.get("attachments", [])],
            },
            "facts": {
                "platform": "teams",
                "activity_type": activity_type,
                "sender_name": sender_name,
                "tenant_id": event.get("channelData", {}).get("tenant", {}).get("id", ""),
                "team_id": event.get("channelData", {}).get("team", {}).get("id", ""),
            },
            "actor": {
                "kind": "human",
                "identifier": f"teams:{sender_id}",
                "attributes": {"name": sender_name},
            },
            "timestamp": event.get("timestamp", datetime.now(UTC).isoformat()),
            "locale": event.get("locale", "en"),
        }

    async def validate_connection(self) -> bool:
        """Check that Teams credentials are configured."""
        return all(os.environ.get(var) for var in ("TEAMS_TENANT_ID", "TEAMS_CLIENT_ID", "TEAMS_CLIENT_SECRET"))

    async def list_event_types(self) -> list[str]:
        return ["message", "messageUpdate", "messageDelete", "conversationUpdate"]

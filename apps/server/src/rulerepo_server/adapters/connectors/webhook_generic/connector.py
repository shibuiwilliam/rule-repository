"""Generic webhook connector implementation.

Accepts arbitrary JSON payloads and wraps them as Generic surface subjects.
Useful for custom integrations that do not have a dedicated connector.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rulerepo_server.adapters.connectors.base import SubjectConnector


class WebhookGenericConnector(SubjectConnector):
    """Connector for generic webhook payloads."""

    @property
    def name(self) -> str:
        return "webhook_generic"

    @property
    def supported_surfaces(self) -> list[str]:
        return ["generic"]

    async def normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """Wrap a raw JSON payload as a Generic surface subject.

        The caller may specify ``surface``, ``identifier``, ``actor``,
        and ``locale`` at the top level of the event; otherwise defaults
        are applied.

        Args:
            event: Arbitrary JSON payload.

        Returns:
            Dict compatible with EvaluationSubjectPayload for the Generic surface.
        """
        surface = event.pop("surface", "generic")
        identifier = event.pop("identifier", f"webhook:{datetime.now(UTC).isoformat()}")
        actor = event.pop("actor", None)
        locale = event.pop("locale", "en")
        timestamp = event.pop("timestamp", datetime.now(UTC).isoformat())

        return {
            "surface": surface,
            "identifier": identifier,
            "payload": event,
            "facts": {
                "source_system": "webhook_generic",
            },
            "actor": actor
            or {
                "kind": "system",
                "identifier": "webhook_generic",
            },
            "timestamp": timestamp,
            "locale": locale,
        }

    async def validate_connection(self) -> bool:
        """Generic webhook is always available."""
        return True

    async def list_event_types(self) -> list[str]:
        return ["custom"]

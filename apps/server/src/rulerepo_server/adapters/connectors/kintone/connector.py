"""Kintone connector implementation.

Normalizes Kintone webhook events (record creation, updates, status changes)
into HumanAction and Transaction surface subjects.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.adapters.connectors.base import SubjectConnector


class KintoneConnector(SubjectConnector):
    """Connector for Kintone form and workflow events."""

    @property
    def name(self) -> str:
        return "kintone"

    @property
    def supported_surfaces(self) -> list[str]:
        return ["human_action", "transaction"]

    async def normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """Normalize a Kintone webhook event into a subject.

        Routes to ``transaction`` for apps tagged as financial/procurement,
        and ``human_action`` for HR/workflow apps. Defaults to
        ``human_action`` when the app category is unknown.

        Args:
            event: Raw Kintone webhook payload.

        Returns:
            Dict compatible with EvaluationSubjectPayload.
        """
        app = event.get("app", {})
        app_id = app.get("id", event.get("app_id", "unknown"))
        record = event.get("record", {})
        record_id = record.get("$id", {}).get("value", event.get("record_id", "unknown"))
        event_type = event.get("type", "EDIT_RECORD")

        # Determine surface from app category or explicit flag
        financial_categories = {"expense", "procurement", "invoice", "budget", "payment"}
        app_category = event.get("app_category", "").lower()
        surface = "transaction" if app_category in financial_categories else "human_action"

        creator = record.get("Creator", {}).get("value", {})
        user_code = creator.get("code", event.get("user_code", "unknown"))

        # Flatten record field values
        fields: dict[str, Any] = {}
        for key, val in record.items():
            if isinstance(val, dict) and "value" in val:
                fields[key] = val["value"]

        return {
            "surface": surface,
            "identifier": f"kintone:{app_id}:{record_id}",
            "payload": {
                "app_id": app_id,
                "record_id": record_id,
                "event_type": event_type,
                "fields": fields,
                "action": event_type.lower(),
            },
            "facts": {
                "source_system": "kintone",
                "app_name": app.get("name", ""),
                "app_category": app_category,
                "event_type": event_type,
            },
            "actor": {
                "kind": "human",
                "identifier": f"kintone:{user_code}",
            },
            "timestamp": event.get("timestamp", datetime.now(UTC).isoformat()),
            "locale": event.get("locale", "ja"),
        }

    async def validate_connection(self) -> bool:
        """Check that Kintone connection parameters are configured."""
        return all(os.environ.get(var) for var in ("KINTONE_BASE_URL", "KINTONE_API_TOKEN"))

    async def list_event_types(self) -> list[str]:
        return [
            "ADD_RECORD",
            "EDIT_RECORD",
            "DELETE_RECORD",
            "CHANGE_STATUS",
            "ADD_COMMENT",
        ]

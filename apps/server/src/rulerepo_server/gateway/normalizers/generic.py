"""Generic JSON event normalizer — pass-through for custom integrations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from rulerepo_server.gateway.normalizers.base import EventNormalizer
from rulerepo_server.gateway.schemas import NormalizedEvent


class GenericNormalizer(EventNormalizer):
    """Pass-through normalizer for generic JSON webhook payloads."""

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        """Convert a generic JSON payload.

        Expects optional fields: event_type, actor, subject, metadata.
        Falls back to sensible defaults.
        """
        return NormalizedEvent(
            source="generic",
            event_type=payload.get("event_type", "generic"),
            actor=payload.get("actor"),
            subject=payload.get("subject", "Generic webhook event"),
            metadata=payload.get("metadata", {}),
            raw_payload=payload,
            timestamp=datetime.now(tz=timezone.utc),
        )

"""Base normalizer interface for webhook event normalization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from rulerepo_server.gateway.schemas import NormalizedEvent


class EventNormalizer(ABC):
    """Abstract base for event normalizers. Each source (GitHub, Slack, etc.)
    implements this to produce a NormalizedEvent from raw webhook payloads.
    """

    @abstractmethod
    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        """Convert a raw webhook payload into a NormalizedEvent.

        Args:
            payload: The raw JSON payload from the webhook source.

        Returns:
            A normalized event with source, type, actor, subject, and metadata.
        """
        ...

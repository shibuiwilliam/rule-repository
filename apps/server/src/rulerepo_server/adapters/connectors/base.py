"""SubjectConnector ABC -- the standard contract for external system integration.

See CLAUDE.md 14.7.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SubjectConnector(ABC):
    """Abstract base class for connectors that normalize external events into Subjects.

    Each connector translates events from an external business system
    (Salesforce, Workday, SAP, DocuSign, Slack, etc.) into the universal
    Subject format consumed by the evaluation pipeline.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Connector identifier (e.g., 'workday', 'salesforce')."""
        ...

    @property
    @abstractmethod
    def supported_surfaces(self) -> list[str]:
        """Surfaces this connector can produce subjects for."""
        ...

    @abstractmethod
    async def normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """Normalize an external event into a Subject-compatible payload.

        Args:
            event: Raw event from the external system.

        Returns:
            Dict compatible with EvaluationSubjectPayload construction.
        """
        ...

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Test connectivity to the external system.

        Returns:
            True if connection is healthy.
        """
        ...

    async def list_event_types(self) -> list[str]:
        """List event types this connector can process."""
        return []

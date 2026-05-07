"""Base protocol for business system connectors."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from rulerepo_server.domain.subject import EvaluationSubject


@runtime_checkable
class BusinessSystemConnector(Protocol):
    """Protocol for business system integrations.

    Each connector provides:
    - Webhook payload normalization into an EvaluationSubject
    - Outbound action dispatch (e.g., posting review comments back)
    """

    @property
    def system_name(self) -> str:
        """Name of the business system (e.g., 'freee', 'concur')."""
        ...

    def normalize_webhook(self, payload: dict[str, Any]) -> EvaluationSubject:
        """Normalize an inbound webhook payload into an EvaluationSubject.

        Args:
            payload: Raw webhook payload from the business system.

        Returns:
            An EvaluationSubject ready for the evaluation pipeline.
        """
        ...

    async def dispatch_result(
        self,
        evaluation_id: str,
        verdict: str,
        details: dict[str, Any],
    ) -> None:
        """Send evaluation results back to the business system.

        Args:
            evaluation_id: The evaluation ID for traceability.
            verdict: The verdict string (ALLOW, DENY, etc.).
            details: Additional details to include in the response.
        """
        ...

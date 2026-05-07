"""Expense system connector — webhook receiver for expense submissions.

Supports integration with expense management systems (e.g., Concur, freee).
Normalizes webhook payloads into EXPENSE_CLAIM subjects.

Phase 7d.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.subject import EvaluationSubject, SubjectType

logger = get_logger(__name__)


class ExpenseConnector:
    """Connector for expense management systems."""

    @property
    def system_name(self) -> str:
        return "expense"

    def normalize_webhook(self, payload: dict[str, Any]) -> EvaluationSubject:
        """Normalize an expense webhook into an EXPENSE_CLAIM subject."""
        return EvaluationSubject(
            type=SubjectType.EXPENSE_CLAIM,
            payload={
                "expense_type": payload.get("expense_type", "general"),
                "amount": payload.get("amount", 0),
                "currency": payload.get("currency", "JPY"),
                "employee_id": payload.get("employee_id", ""),
                "date": payload.get("date", ""),
                "description": payload.get("description", ""),
                "receipt_attached": payload.get("receipt_attached", False),
                "attendees": payload.get("attendees"),
                "jurisdiction": payload.get("jurisdiction", "jp"),
            },
            metadata={
                "source_system": self.system_name,
                "report_id": payload.get("report_id", ""),
            },
        )

    async def dispatch_result(
        self,
        evaluation_id: str,
        verdict: str,
        details: dict[str, Any],
    ) -> None:
        """Send result back — post return-for-revision comment if denied."""
        logger.info(
            "expense_dispatch_placeholder",
            evaluation_id=evaluation_id,
            verdict=verdict,
        )

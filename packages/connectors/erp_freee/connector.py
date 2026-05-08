"""freee ERP connector — mock implementation.

Implements both EventSource and Sink protocols for freee accounting
integration.  This mock version returns realistic sample data for
development and testing.  A production implementation would call the
freee API (https://developer.freee.co.jp/).

Polls: journal entries, expense claims, payment requests.
Sends: approval status, compliance flags.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.services.connectors.base import (
    ConnectorConfig,
    ConnectorHealth,
    ConnectorStatus,
    EventCallback,
)

_MOCK_JOURNAL_ENTRIES: list[dict[str, Any]] = [
    {
        "id": "je-001",
        "entry_number": "JE-2026-001234",
        "date": "2026-05-07",
        "description": "Office supplies purchase — Tokyo HQ",
        "amount": 54_000,
        "currency": "JPY",
        "debit_account": "6100",
        "debit_account_name": "Supplies Expense",
        "credit_account": "1100",
        "credit_account_name": "Cash",
        "department": "operations",
        "created_by": "usr-fin-001",
    },
    {
        "id": "je-002",
        "entry_number": "JE-2026-001235",
        "date": "2026-05-07",
        "description": "Client entertainment — Osaka branch",
        "amount": 128_000,
        "currency": "JPY",
        "debit_account": "6400",
        "debit_account_name": "Entertainment Expense",
        "credit_account": "2100",
        "credit_account_name": "Accounts Payable",
        "department": "sales",
        "created_by": "usr-sales-003",
    },
]

_MOCK_EXPENSE_CLAIMS: list[dict[str, Any]] = [
    {
        "id": "exp-001",
        "claim_number": "EXP-2026-0567",
        "employee_id": "emp-001",
        "employee_name": "Tanaka Yuki",
        "department": "engineering",
        "submitted_date": "2026-05-06",
        "total_amount": 32_400,
        "currency": "JPY",
        "status": "pending_approval",
        "items": [
            {
                "description": "Train fare — client visit",
                "amount": 2_400,
                "category": "transportation",
            },
            {
                "description": "Hotel — Osaka business trip",
                "amount": 30_000,
                "category": "accommodation",
            },
        ],
    },
]

_MOCK_PAYMENT_REQUESTS: list[dict[str, Any]] = [
    {
        "id": "pay-001",
        "request_number": "PAY-2026-0089",
        "vendor_name": "Cloud Services Co., Ltd.",
        "amount": 1_200_000,
        "currency": "JPY",
        "due_date": "2026-05-31",
        "status": "pending_approval",
        "department": "it",
        "description": "Monthly cloud infrastructure invoice",
        "invoice_number": "INV-CS-2026-05",
        "requested_by": "usr-it-001",
    },
]


class FreeeConnector:
    """Mock freee ERP connector implementing EventSource and Sink.

    In production, this would authenticate via OAuth2 and call the
    freee accounting API.

    Args:
        config: Connector configuration with freee-specific settings.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        self._config = config
        self._subscriptions: dict[str, EventCallback] = {}

    @property
    def name(self) -> str:
        """Human-readable connector name."""
        return "freee Accounting"

    @property
    def connector_type(self) -> str:
        """Machine-readable connector type."""
        return "erp-freee"

    @property
    def domain(self) -> str:
        """Business domain."""
        return "finance"

    # -- EventSource -------------------------------------------------------

    async def poll_events(
        self,
        since: datetime,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Poll freee for financial events since *since*.

        Returns journal entries, expense claims, and payment requests.
        In production, this would call ``GET /api/1/deals``,
        ``GET /api/1/expense_applications``, etc.

        Args:
            since: Return only events after this timestamp.
            limit: Maximum number of events to return.

        Returns:
            Normalized event dicts.
        """
        events: list[dict[str, Any]] = []

        # Journal entries
        for je in _MOCK_JOURNAL_ENTRIES:
            events.append(
                {
                    "event_type": "journal_entry",
                    "event_id": str(uuid.uuid4()),
                    "source_id": je["id"],
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": {
                        "entry_number": je["entry_number"],
                        "date": je["date"],
                        "description": je["description"],
                        "amount": je["amount"],
                        "currency": je["currency"],
                        "debit_account": je["debit_account"],
                        "debit_account_name": je["debit_account_name"],
                        "credit_account": je["credit_account"],
                        "credit_account_name": je["credit_account_name"],
                        "department": je["department"],
                        "created_by": je["created_by"],
                    },
                }
            )

        # Expense claims
        for exp in _MOCK_EXPENSE_CLAIMS:
            events.append(
                {
                    "event_type": "expense_claim",
                    "event_id": str(uuid.uuid4()),
                    "source_id": exp["id"],
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": {
                        "claim_number": exp["claim_number"],
                        "employee_id": exp["employee_id"],
                        "employee_name": exp["employee_name"],
                        "department": exp["department"],
                        "submitted_date": exp["submitted_date"],
                        "total_amount": exp["total_amount"],
                        "currency": exp["currency"],
                        "status": exp["status"],
                        "item_count": len(exp["items"]),
                        "items": exp["items"],
                    },
                }
            )

        # Payment requests
        for pay in _MOCK_PAYMENT_REQUESTS:
            events.append(
                {
                    "event_type": "payment_request",
                    "event_id": str(uuid.uuid4()),
                    "source_id": pay["id"],
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": {
                        "request_number": pay["request_number"],
                        "vendor_name": pay["vendor_name"],
                        "amount": pay["amount"],
                        "currency": pay["currency"],
                        "due_date": pay["due_date"],
                        "status": pay["status"],
                        "department": pay["department"],
                        "description": pay["description"],
                        "invoice_number": pay["invoice_number"],
                        "requested_by": pay["requested_by"],
                    },
                }
            )

        return events[:limit]

    async def subscribe(self, callback: EventCallback) -> str:
        """Register a webhook callback for real-time events.

        Args:
            callback: Async callable receiving batches of event dicts.

        Returns:
            A subscription ID.
        """
        sub_id = str(uuid.uuid4())
        self._subscriptions[sub_id] = callback
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Cancel a previously registered subscription.

        Args:
            subscription_id: The ID returned by :meth:`subscribe`.
        """
        self._subscriptions.pop(subscription_id, None)

    async def health_check(self) -> ConnectorHealth:
        """Probe freee API connectivity.

        The mock always returns CONNECTED with synthetic latency.

        Returns:
            A ConnectorHealth snapshot.
        """
        start = time.monotonic()
        latency = (time.monotonic() - start) * 1000
        return ConnectorHealth(
            status=ConnectorStatus.CONNECTED,
            last_checked_at=datetime.now(UTC),
            latency_ms=round(latency, 2),
        )

    # -- Sink --------------------------------------------------------------

    async def send_verdict(self, evaluation_result: dict[str, Any]) -> bool:
        """Push an approval verdict back to freee.

        In production, this would update the approval status of a deal
        or expense application via the freee API.

        Args:
            evaluation_result: Normalized evaluation result dict.

        Returns:
            True if accepted.
        """
        return True

    async def send_alert(self, alert: dict[str, Any]) -> bool:
        """Push a compliance flag to freee.

        In production, this would create a note or tag on the relevant
        financial record.

        Args:
            alert: Normalized alert dict.

        Returns:
            True if accepted.
        """
        return True

    async def send_notification(self, notification: dict[str, Any]) -> bool:
        """Push a notification through freee's messaging.

        Args:
            notification: Normalized notification dict.

        Returns:
            True if accepted.
        """
        return True

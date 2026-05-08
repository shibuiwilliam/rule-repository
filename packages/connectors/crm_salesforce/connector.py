"""Salesforce CRM connector — mock implementation.

Implements both EventSource and Sink protocols for Salesforce integration.
This mock version returns realistic sample data for development and
testing.  A production implementation would use the Salesforce REST API
or Bulk API with OAuth2 authentication.

Polls: opportunity updates, contract submissions, account changes.
Sends: compliance alerts, deal approval verdicts.
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

_MOCK_OPPORTUNITIES: list[dict[str, Any]] = [
    {
        "id": "opp-001",
        "name": "Enterprise Platform License — Acme Corp",
        "account_id": "acc-001",
        "account_name": "Acme Corporation",
        "stage": "Negotiation/Review",
        "amount": 2_400_000,
        "currency": "JPY",
        "close_date": "2026-06-30",
        "owner_id": "usr-sales-001",
        "owner_name": "Yamada Taro",
    },
    {
        "id": "opp-002",
        "name": "SaaS Migration — Global Tech",
        "account_id": "acc-002",
        "account_name": "Global Tech Inc.",
        "stage": "Proposal/Price Quote",
        "amount": 8_500_000,
        "currency": "JPY",
        "close_date": "2026-07-15",
        "owner_id": "usr-sales-002",
        "owner_name": "Watanabe Mei",
    },
]

_MOCK_CONTRACTS: list[dict[str, Any]] = [
    {
        "id": "ctr-001",
        "account_id": "acc-001",
        "account_name": "Acme Corporation",
        "contract_number": "CNT-2026-0042",
        "status": "Draft",
        "start_date": "2026-07-01",
        "end_date": "2027-06-30",
        "contract_term_months": 12,
        "total_value": 2_400_000,
        "currency": "JPY",
    },
]


class SalesforceConnector:
    """Mock Salesforce CRM connector implementing EventSource and Sink.

    In production, this would authenticate via OAuth2 (JWT bearer or
    web-server flow) and call the Salesforce REST/SOAP API.

    Args:
        config: Connector configuration with Salesforce-specific settings.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        self._config = config
        self._subscriptions: dict[str, EventCallback] = {}

    @property
    def name(self) -> str:
        """Human-readable connector name."""
        return "Salesforce CRM"

    @property
    def connector_type(self) -> str:
        """Machine-readable connector type."""
        return "crm-salesforce"

    @property
    def domain(self) -> str:
        """Business domain."""
        return "sales"

    # -- EventSource -------------------------------------------------------

    async def poll_events(
        self,
        since: datetime,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Poll Salesforce for CRM events since *since*.

        Returns opportunity updates, contract submissions, and account
        changes.  In production, this would query the Salesforce
        ``/services/data/vXX.X/sobjects/`` endpoints.

        Args:
            since: Return only events after this timestamp.
            limit: Maximum number of events to return.

        Returns:
            Normalized event dicts.
        """
        events: list[dict[str, Any]] = []

        # Opportunity stage change
        for opp in _MOCK_OPPORTUNITIES:
            events.append(
                {
                    "event_type": "opportunity_update",
                    "event_id": str(uuid.uuid4()),
                    "source_id": opp["id"],
                    "account_name": opp["account_name"],
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": {
                        "opportunity_name": opp["name"],
                        "stage": opp["stage"],
                        "amount": opp["amount"],
                        "currency": opp["currency"],
                        "close_date": opp["close_date"],
                        "owner_name": opp["owner_name"],
                        "change": "stage_advanced",
                    },
                }
            )

        # Contract submission
        for ctr in _MOCK_CONTRACTS:
            events.append(
                {
                    "event_type": "contract_submission",
                    "event_id": str(uuid.uuid4()),
                    "source_id": ctr["id"],
                    "account_name": ctr["account_name"],
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": {
                        "contract_number": ctr["contract_number"],
                        "status": ctr["status"],
                        "total_value": ctr["total_value"],
                        "currency": ctr["currency"],
                        "start_date": ctr["start_date"],
                        "end_date": ctr["end_date"],
                        "term_months": ctr["contract_term_months"],
                    },
                }
            )

        # Account change
        events.append(
            {
                "event_type": "account_change",
                "event_id": str(uuid.uuid4()),
                "source_id": "acc-002",
                "account_name": "Global Tech Inc.",
                "timestamp": datetime.now(UTC).isoformat(),
                "data": {
                    "change_type": "credit_rating_update",
                    "old_value": "A",
                    "new_value": "A+",
                    "updated_by": "usr-sales-002",
                },
            }
        )

        return events[:limit]

    async def subscribe(self, callback: EventCallback) -> str:
        """Register a Streaming API / Platform Events subscription.

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
        """Probe Salesforce connectivity.

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
        """Push a deal approval verdict to Salesforce.

        In production, this would update a custom field on the
        Opportunity or create a Chatter post.

        Args:
            evaluation_result: Normalized evaluation result dict.

        Returns:
            True if accepted.
        """
        return True

    async def send_alert(self, alert: dict[str, Any]) -> bool:
        """Push a compliance alert to Salesforce.

        In production, this would create a Task or Platform Event.

        Args:
            alert: Normalized alert dict.

        Returns:
            True if accepted.
        """
        return True

    async def send_notification(self, notification: dict[str, Any]) -> bool:
        """Push a notification to Salesforce (e.g., Chatter post).

        Args:
            notification: Normalized notification dict.

        Returns:
            True if accepted.
        """
        return True

"""Salesforce connector implementation.

Normalizes Salesforce CRM events (opportunity updates, quote approvals,
contract executions) into Transaction and Document surface subjects.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.adapters.connectors.base import SubjectConnector


class SalesforceConnector(SubjectConnector):
    """Connector for Salesforce CRM events."""

    @property
    def name(self) -> str:
        return "salesforce"

    @property
    def supported_surfaces(self) -> list[str]:
        return ["transaction", "document"]

    async def normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """Normalize a Salesforce event into a Transaction or Document subject.

        Routes to the ``transaction`` surface for opportunity and quote events,
        and to ``document`` for attachment and content-version events.

        Args:
            event: Raw Salesforce platform event or outbound message payload.

        Returns:
            Dict compatible with EvaluationSubjectPayload.
        """
        sobject = event.get("sobject", event.get("object_type", ""))
        record = event.get("record", event)
        record_id = record.get("Id", record.get("id", "unknown"))

        # Route document-type events to the document surface
        document_types = {"Attachment", "ContentVersion", "ContentDocument"}
        surface = "document" if sobject in document_types else "transaction"

        owner = record.get("OwnerId", record.get("owner_id", "unknown"))

        return {
            "surface": surface,
            "identifier": f"salesforce:{sobject}:{record_id}",
            "payload": {
                "object_type": sobject,
                "record_id": record_id,
                "fields": {k: v for k, v in record.items() if k not in ("Id", "id", "attributes")},
                "action": event.get("action", event.get("event_type", "update")),
            },
            "facts": {
                "source_system": "salesforce",
                "sobject": sobject,
                "owner": owner,
                "amount": record.get("Amount", record.get("amount")),
                "stage": record.get("StageName", record.get("stage")),
                "account": record.get("AccountId", record.get("account_id")),
            },
            "actor": {
                "kind": "human",
                "identifier": f"salesforce:{owner}",
            },
            "timestamp": record.get(
                "LastModifiedDate",
                record.get("last_modified_date", datetime.now(UTC).isoformat()),
            ),
            "locale": "en",
        }

    async def validate_connection(self) -> bool:
        """Check that Salesforce OAuth credentials are configured."""
        return all(os.environ.get(var) for var in ("SALESFORCE_CLIENT_ID", "SALESFORCE_CLIENT_SECRET"))

    async def list_event_types(self) -> list[str]:
        return [
            "opportunity_update",
            "quote_approval",
            "contract_execution",
            "case_escalation",
            "attachment_upload",
        ]

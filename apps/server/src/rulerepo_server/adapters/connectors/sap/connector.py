"""SAP connector implementation.

Normalizes SAP ERP events (purchase orders, invoices, journal entries,
goods receipts) into Transaction surface subjects for evaluation.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.adapters.connectors.base import SubjectConnector


class SAPConnector(SubjectConnector):
    """Connector for SAP ERP system events."""

    @property
    def name(self) -> str:
        return "sap"

    @property
    def supported_surfaces(self) -> list[str]:
        return ["transaction"]

    async def normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """Normalize an SAP event into a Transaction surface subject.

        Supports document types such as purchase orders, invoices,
        journal entries, and goods receipts.

        Args:
            event: Raw SAP IDoc or OData event payload.

        Returns:
            Dict compatible with EvaluationSubjectPayload for the Transaction surface.
        """
        doc_type = event.get("document_type", event.get("BSART", "unknown"))
        doc_number = event.get("document_number", event.get("EBELN", "unknown"))
        company_code = event.get("company_code", event.get("BUKRS", ""))
        user = event.get("created_by", event.get("ERNAM", "unknown"))

        return {
            "surface": "transaction",
            "identifier": f"sap:{doc_type}:{doc_number}",
            "payload": {
                "document_type": doc_type,
                "document_number": doc_number,
                "company_code": company_code,
                "line_items": event.get("line_items", event.get("items", [])),
                "total_amount": event.get("total_amount", event.get("NETWR")),
                "currency": event.get("currency", event.get("WAERS", "USD")),
                "vendor": event.get("vendor", event.get("LIFNR")),
                "cost_center": event.get("cost_center", event.get("KOSTL")),
            },
            "facts": {
                "source_system": "sap",
                "document_type": doc_type,
                "company_code": company_code,
                "fiscal_year": event.get("fiscal_year", event.get("GJAHR")),
                "posting_date": event.get("posting_date", event.get("BUDAT")),
            },
            "actor": {
                "kind": "human",
                "identifier": f"sap:{user}",
            },
            "timestamp": event.get("timestamp", datetime.now(UTC).isoformat()),
            "locale": "en",
        }

    async def validate_connection(self) -> bool:
        """Check that SAP connection parameters are configured."""
        return all(os.environ.get(var) for var in ("SAP_BASE_URL", "SAP_CLIENT_ID"))

    async def list_event_types(self) -> list[str]:
        return [
            "purchase_order",
            "invoice",
            "journal_entry",
            "goods_receipt",
            "payment",
            "credit_memo",
        ]

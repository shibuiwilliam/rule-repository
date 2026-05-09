"""DocuSign connector implementation.

Normalizes DocuSign Connect webhook events (envelope status changes,
recipient actions) into Contract and Document surface subjects.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from rulerepo_server.adapters.connectors.base import SubjectConnector


class DocuSignConnector(SubjectConnector):
    """Connector for DocuSign e-signature events."""

    @property
    def name(self) -> str:
        return "docusign"

    @property
    def supported_surfaces(self) -> list[str]:
        return ["contract", "document"]

    async def normalize(self, event: dict[str, Any]) -> dict[str, Any]:
        """Normalize a DocuSign Connect event into a Contract or Document subject.

        Routes to ``contract`` for envelope-level events and ``document``
        for individual document-level events.

        Args:
            event: Raw DocuSign Connect webhook payload.

        Returns:
            Dict compatible with EvaluationSubjectPayload.
        """
        envelope = event.get("envelope", event)
        envelope_id = envelope.get("envelopeId", envelope.get("envelope_id", "unknown"))
        status = envelope.get("status", "")
        sender = envelope.get("sender", {})
        sender_email = sender.get("email", event.get("sender_email", "unknown"))

        recipients = envelope.get("recipients", {})
        signers = recipients.get("signers", [])
        parties = [s.get("email", s.get("name", "")) for s in signers]

        documents = envelope.get("documents", [])
        # Use contract surface for envelope events, document for doc-specific
        surface = "document" if event.get("document_id") else "contract"

        return {
            "surface": surface,
            "identifier": f"docusign:{envelope_id}",
            "payload": {
                "envelope_id": envelope_id,
                "status": status,
                "subject": envelope.get("emailSubject", ""),
                "parties": parties,
                "documents": [{"name": d.get("name", ""), "document_id": d.get("documentId", "")} for d in documents],
                "content": event.get("document_content", ""),
            },
            "facts": {
                "source_system": "docusign",
                "envelope_status": status,
                "signer_count": len(signers),
                "document_count": len(documents),
                "sent_date": envelope.get("sentDateTime"),
                "completed_date": envelope.get("completedDateTime"),
            },
            "actor": {
                "kind": "human",
                "identifier": f"docusign:{sender_email}",
            },
            "timestamp": envelope.get(
                "statusChangedDateTime",
                datetime.now(UTC).isoformat(),
            ),
            "locale": "en",
        }

    async def validate_connection(self) -> bool:
        """Check that DocuSign integration key is configured."""
        return bool(os.environ.get("DOCUSIGN_INTEGRATION_KEY"))

    async def list_event_types(self) -> list[str]:
        return [
            "envelope_sent",
            "envelope_delivered",
            "envelope_completed",
            "envelope_declined",
            "envelope_voided",
            "recipient_signed",
            "recipient_declined",
        ]

"""Contract system connector — webhook receiver for contract review events.

Supports integration with contract management systems (e.g., DocuSign,
CloudSign). Normalizes webhook payloads into CONTRACT_CLAUSE subjects.

Phase 7d.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.subject import EvaluationSubject, SubjectType

logger = get_logger(__name__)


class ContractConnector:
    """Connector for contract management systems."""

    @property
    def system_name(self) -> str:
        return "contract"

    def normalize_webhook(self, payload: dict[str, Any]) -> EvaluationSubject:
        """Normalize a contract webhook into a CONTRACT_CLAUSE subject."""
        return EvaluationSubject(
            type=SubjectType.CONTRACT_CLAUSE,
            payload={
                "contract_type": payload.get("contract_type", ""),
                "clause_text": payload.get("clause_text", payload.get("text", "")),
                "clause_type": payload.get("clause_type", ""),
                "counterparty": payload.get("counterparty", ""),
                "governing_law": payload.get("governing_law", ""),
                "review_type": payload.get("review_type", "contract_review"),
            },
            metadata={
                "source_system": self.system_name,
                "document_id": payload.get("document_id", ""),
                "envelope_id": payload.get("envelope_id", ""),
            },
        )

    async def dispatch_result(
        self,
        evaluation_id: str,
        verdict: str,
        details: dict[str, Any],
    ) -> None:
        """Send result back to contract management system."""
        logger.info(
            "contract_dispatch_placeholder",
            evaluation_id=evaluation_id,
            verdict=verdict,
        )

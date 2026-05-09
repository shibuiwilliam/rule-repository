"""Contract surface adapter — evaluates contract clauses against rules.

See CLAUDE.md §14.3 for the Contract Pack specification.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rulerepo_server.domain.evaluation import Surface
from rulerepo_server.services.evaluation.surfaces.base import (
    EvaluationSubjectPayload,
    SurfaceAdapter,
)

_HINTS_FILE = Path(__file__).parent / "prompts" / "contract_hints.txt"


class ContractSurfaceAdapter(SurfaceAdapter):
    """Surface adapter for contract clause evaluation.

    Handles clause text, clause type, parties, and contract metadata.
    """

    @property
    def surface(self) -> Surface:
        return Surface.CONTRACT

    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a contract clause evaluation request.

        Expected payload keys:
            - clause_text: str — the clause to evaluate
            - clause_type: str (e.g., "indemnity", "termination", "confidentiality")
            - parties: list[str] — parties to the contract
            - contract_id: str — contract identifier
            - position: int — clause position in the document
            - locale: str — language of the clause (default "en")
            - document_id: str — source document reference

        Returns:
            EvaluationSubjectPayload with contract-specific fields.
        """
        clause_text = payload.get("clause_text", "")
        clause_type = payload.get("clause_type", "general")
        parties = payload.get("parties", [])
        contract_id = payload.get("contract_id", "unknown")

        parties_str = ", ".join(parties) if parties else "unspecified parties"
        description = f"Contract clause ({clause_type}) between {parties_str}:\n\n{clause_text}"

        facts: dict[str, Any] = {}
        if payload.get("contract_value"):
            facts["contract_value"] = payload["contract_value"]
        if payload.get("governing_law"):
            facts["governing_law"] = payload["governing_law"]
        if payload.get("effective_date"):
            facts["effective_date"] = payload["effective_date"]

        return EvaluationSubjectPayload(
            surface=Surface.CONTRACT,
            identifier=f"contract:{contract_id}/clause:{payload.get('position', 0)}",
            description=description,
            payload={
                "clause_text": clause_text,
                "clause_type": clause_type,
                "parties": parties,
                "position": payload.get("position", 0),
                "document_id": payload.get("document_id"),
            },
            facts=facts,
            locale=payload.get("locale", "en"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from contract type and clause type."""
        scopes: set[str] = set()
        clause_type = payload.get("clause_type", "")
        if clause_type:
            scopes.add(f"legal/contract/{clause_type}")
        scopes.add("legal/contract")
        return sorted(scopes)

    def get_prompt_hints(self) -> str:
        if _HINTS_FILE.exists():
            return _HINTS_FILE.read_text()
        return (
            "You are evaluating a contract clause for compliance with legal and "
            "organizational rules. Focus on legal risks, missing protections, "
            "non-standard terms, and regulatory compliance. Do not provide "
            "file paths or code-level remediations; instead describe the "
            "clause-level issue and suggest revised language."
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        return ["parties"]  # Party names may contain natural person names

    @property
    def default_audit_retention_days(self) -> int:
        return 3650  # 10 years for legal documents

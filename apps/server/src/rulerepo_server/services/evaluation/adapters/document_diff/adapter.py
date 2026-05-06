"""Document diff evaluation domain adapter.

Handles contract and document comparisons, extracting metadata about
contract type, governing law, and clause-level changes for compliance
evaluation.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.contract import ContractScope, ContractType, PartyRole
from rulerepo_server.domain.evaluation import EvaluationContext

# Mapping from contract type to rule scopes
CONTRACT_TYPE_SCOPE_MAP: dict[str, list[str]] = {
    "nda": ["legal/nda", "legal/confidentiality"],
    "msa": ["legal/msa", "legal/general"],
    "sow": ["legal/sow", "legal/procurement"],
    "dpa": ["legal/dpa", "legal/privacy"],
    "lease": ["legal/lease", "legal/property"],
    "sales": ["legal/sales", "legal/commercial"],
    "other": ["legal/general"],
}


class DocumentDiffAdapter:
    """Adapter for document/contract diff evaluation.

    Parses contract metadata and old/new text for clause comparison,
    resolves scopes from contract type, and provides contract-specific
    prompt fragments.
    """

    domain: str = "document_diff"

    async def parse(self, payload: dict[str, Any]) -> EvaluationContext:
        """Parse a document diff payload into EvaluationContext.

        Expected payload keys:
            - contract_type: str (e.g., "nda", "msa")
            - governing_law: str (e.g., "japan", "us-delaware")
            - counterparty_country: str
            - party_role: str (e.g., "disclosing", "receiving", "both")
            - language: str (e.g., "en", "ja")
            - old_text: str (original document text)
            - new_text: str (revised document text)
            - diff: str (optional unified diff of changes)
            - description: str (description of the change)
            - actor: str

        Args:
            payload: Document diff payload dict.

        Returns:
            EvaluationContext with contract metadata in facts.
        """
        contract_scope = _extract_contract_scope(payload)

        # Build facts with contract metadata
        facts: dict[str, Any] = {}
        if contract_scope.contract_type:
            facts["contract_type"] = contract_scope.contract_type.value
        if contract_scope.governing_law:
            facts["governing_law"] = contract_scope.governing_law
        if contract_scope.counterparty_country:
            facts["counterparty_country"] = contract_scope.counterparty_country
        if contract_scope.party_role:
            facts["party_role"] = contract_scope.party_role.value
        if contract_scope.language:
            facts["contract_language"] = contract_scope.language

        # Include document texts
        old_text = payload.get("old_text", "")
        new_text = payload.get("new_text", "")
        if old_text:
            facts["old_text"] = old_text
        if new_text:
            facts["new_text"] = new_text

        # Build narrative
        description = payload.get("description", "")
        contract_type_str = facts.get("contract_type", "document")
        narrative = description or f"Document diff evaluation for {contract_type_str}"

        # Use diff if provided, otherwise generate a simple comparison note
        diff_text = payload.get("diff")
        if not diff_text and old_text and new_text:
            diff_text = f"--- old\n+++ new\nDocument changed from {len(old_text)} to {len(new_text)} characters."

        return EvaluationContext(
            diff=diff_text,
            facts=facts,
            narrative=narrative,
            intent=description or None,
            actor=payload.get("actor"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from contract type and metadata.

        Args:
            payload: Dict with 'contract_type' and optional metadata.

        Returns:
            Deduplicated list of scope strings.
        """
        scopes: set[str] = set()

        contract_type = payload.get("contract_type", "").lower()
        if contract_type in CONTRACT_TYPE_SCOPE_MAP:
            scopes.update(CONTRACT_TYPE_SCOPE_MAP[contract_type])
        else:
            scopes.add("legal/general")

        # Add jurisdiction-based scope if governing law is specified
        governing_law = payload.get("governing_law")
        if governing_law:
            scopes.add(f"legal/jurisdiction/{governing_law.lower()}")

        return sorted(scopes)

    def get_prompt_fragments(self) -> dict[str, str]:
        """Return contract-specific prompt fragments.

        Returns:
            Dict with domain_intro and context_format keys.
        """
        return {
            "domain_intro": (
                "You are evaluating changes to a legal document or contract for "
                "compliance with applicable rules. Focus on clause completeness, "
                "risk identification, regulatory requirements, and contractual "
                "obligations."
            ),
            "context_format": (
                "The input contains contract metadata (type, governing law, party role) "
                "and the old and new text of the document. Evaluate whether the changes "
                "introduce risks, remove required protections, or violate applicable "
                "rules and regulations."
            ),
        }


def _extract_contract_scope(payload: dict[str, Any]) -> ContractScope:
    """Extract a ContractScope from a payload dict.

    Args:
        payload: Dict with contract metadata fields.

    Returns:
        ContractScope instance with available fields populated.
    """
    contract_type = None
    raw_type = payload.get("contract_type", "")
    if raw_type:
        try:
            contract_type = ContractType(raw_type.lower())
        except ValueError:
            contract_type = ContractType.OTHER

    party_role = None
    raw_role = payload.get("party_role", "")
    if raw_role:
        try:
            party_role = PartyRole(raw_role.lower())
        except ValueError:
            pass

    return ContractScope(
        contract_type=contract_type,
        governing_law=payload.get("governing_law"),
        counterparty_country=payload.get("counterparty_country"),
        party_role=party_role,
        language=payload.get("language"),
    )

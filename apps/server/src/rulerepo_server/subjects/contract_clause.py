"""Contract clause subject adapter — handles clause review evaluations.

Evaluates contract clauses against NDA, MSA, and procurement rules.
See: IMPROVEMENT.md Phase 7b
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext


class ContractClauseAdapter:
    """Adapter for contract clause evaluations."""

    @property
    def subject_type(self) -> str:
        return "contract_clause"

    def parse_payload(self, payload: dict[str, Any]) -> EvaluationContext:
        """Parse a contract clause payload into an EvaluationContext."""
        return EvaluationContext(
            facts=payload,
            intent=payload.get("review_type", "contract_review"),
            narrative=_build_narrative(payload),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from contract type and jurisdiction."""
        scopes = ["legal", "legal/contracts"]
        contract_type = payload.get("contract_type", "").lower()
        if contract_type:
            scopes.append(f"legal/contracts/{contract_type}")

        jurisdiction = payload.get("governing_law", payload.get("jurisdiction", ""))
        if jurisdiction:
            scopes.append(f"legal/contracts/{jurisdiction.lower()}")

        return list(dict.fromkeys(scopes))

    def format_prompt_context(self, payload: dict[str, Any]) -> str:
        """Format the contract clause as prompt context."""
        return _build_narrative(payload)


def _build_narrative(payload: dict[str, Any]) -> str:
    """Build a human-readable narrative from contract clause fields."""
    parts = []

    contract_type = payload.get("contract_type", "unknown")
    parts.append(f"Contract Type: {contract_type}")

    if "clause_text" in payload:
        parts.append(f"\nClause Text:\n{payload['clause_text']}")
    if "clause_type" in payload:
        parts.append(f"Clause Type: {payload['clause_type']}")
    if "counterparty" in payload:
        parts.append(f"Counterparty: {payload['counterparty']}")
    if "governing_law" in payload:
        parts.append(f"Governing Law: {payload['governing_law']}")
    if "diff" in payload:
        parts.append(f"\nChanges:\n{payload['diff']}")

    return "\n".join(parts)

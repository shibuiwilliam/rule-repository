"""Clause set subject adapter — handles contract clause review evaluations.

Evaluates contract clauses against NDA, MSA, and procurement rules.
See: CLAUDE.md §12.2
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import ContractClauseRemediation, EvaluationContext
from rulerepo_server.domain.subject import PromptFormat, SubjectKind
from rulerepo_server.subjects.registry import register


@register(SubjectKind.CLAUSE_SET)
class ClauseSetAdapter:
    """Adapter for contract clause evaluations."""

    kind = SubjectKind.CLAUSE_SET

    @property
    def identifier(self) -> str:
        return "clause_set"

    @property
    def subject_type(self) -> str:
        """Backward-compatible alias."""
        return self.kind.value

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

    def render_for_llm(self, facts: dict[str, Any], format: PromptFormat = PromptFormat.FULL) -> str:
        """Format the contract clause as prompt context."""
        return _build_narrative(facts)

    def format_prompt_context(self, payload: dict[str, Any]) -> str:
        """Legacy alias for render_for_llm."""
        return self.render_for_llm(payload)

    def extract_features(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract clause-specific features for rule selection."""
        return {
            "contract_type": payload.get("contract_type", ""),
            "has_clause_text": bool(payload.get("clause_text")),
            "governing_law": payload.get("governing_law", ""),
        }

    def parse_remediation(self, raw: dict[str, Any]) -> ContractClauseRemediation | None:
        """Parse a clause remediation from raw LLM output."""
        revised = raw.get("revised_text") or raw.get("replacement", "")
        if not revised and not raw.get("description"):
            return None
        return ContractClauseRemediation(
            type=raw.get("type", "clause_revision"),
            description=raw.get("description", ""),
            clause_id=raw.get("clause_id", ""),
            revised_text=revised,
            requires_counterparty_consent=raw.get("requires_counterparty_consent", True),
            auto_applicable=False,
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        """Contracts may contain counterparty PII."""
        pii = []
        if "counterparty" in payload:
            pii.append("counterparty")
        if "signatory" in payload:
            pii.append("signatory")
        return pii


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


# Backward-compatible alias
ContractClauseAdapter = ClauseSetAdapter

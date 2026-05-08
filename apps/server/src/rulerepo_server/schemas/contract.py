"""Pydantic schemas for the Contract Evaluation API.

See: ADR 0004, CLAUDE.md §12.2
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ClauseInput(BaseModel):
    """A single clause for evaluation."""

    clause_id: str = Field(..., description="Stable clause identifier (e.g., 'art1')")
    clause_type: str = Field(default="general", description="Clause type (e.g., 'confidentiality', 'payment')")
    text: str = Field(..., min_length=1, description="The clause text")
    heading: str = Field(default="", description="Clause heading")


class ContractEvaluateRequest(BaseModel):
    """Request to evaluate a contract against applicable rules.

    Either provide structured clauses or raw contract text.
    """

    # Structured input
    clauses: list[ClauseInput] | None = Field(
        default=None,
        description="Pre-parsed clauses to evaluate",
    )

    # Raw text input (will be parsed by ContractParser)
    contract_text: str | None = Field(
        default=None,
        description="Raw contract text to parse and evaluate",
    )

    # Contract metadata
    contract_type: str = Field(default="other", description="Contract type (nda, msa, sow, dpa, lease, sales, other)")
    governing_law: str = Field(default="", description="Governing law jurisdiction")
    counterparty_country: str = Field(default="", description="Counterparty's country")
    party_role: str = Field(default="both", description="Party role (disclosing, receiving, both)")
    language: str = Field(default="en", description="Contract language")
    title: str = Field(default="", description="Contract title")

    # Evaluation parameters
    review_type: str = Field(
        default="self_conformance",
        description="Review type: self_conformance, cross_contract, regulatory_compliance, risk_scoring",
    )
    mode: str = Field(default="preflight", description="preflight | posthoc")
    max_rules: int = Field(default=20, ge=1, le=100)
    severity_min: str = Field(default="MEDIUM")


class ClauseVerdictResponse(BaseModel):
    """Verdict for a single clause."""

    clause_id: str
    clause_type: str = "general"
    verdict: str
    confidence: float
    reasoning: str
    issue_description: str = ""
    revised_text: str = ""
    requires_counterparty_consent: bool = True
    risk_level: str = "low"
    rule_verdicts: list[dict[str, Any]] = Field(default_factory=list)


class ContractEvaluateResponse(BaseModel):
    """Response from the contract evaluation API."""

    evaluation_id: str
    contract_verdict: str
    clause_verdicts: list[ClauseVerdictResponse] = Field(default_factory=list)
    critical_clause_ids: list[str] = Field(default_factory=list)
    warning_clause_ids: list[str] = Field(default_factory=list)
    clause_risk_scores: dict[str, float] = Field(default_factory=dict)
    rules_evaluated: int = 0
    rules_violated: int = 0
    model_ids_used: list[str] = Field(default_factory=list)
    total_latency_ms: int = 0
    review_type: str = "self_conformance"

"""Pydantic schemas for the Evaluation API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FileInput(BaseModel):
    """A file to evaluate (path + optional content)."""

    path: str
    content: str | None = None


class EvaluateRequest(BaseModel):
    """Request to evaluate a code change or action against rules."""

    diff: str | None = Field(default=None, description="Unified diff text")
    files: list[FileInput] | None = Field(default=None, description="Files to evaluate")
    facts: dict[str, Any] | None = Field(default=None, description="Free-form context")
    intent: str | None = Field(default=None, description="Description of the change")
    scope: str | None = Field(default=None, description="Rule scope filter")
    repository: str | None = Field(default=None, description="Repository identifier")
    mode: str = Field(default="preflight", description="preflight | posthoc")
    max_rules: int = Field(default=20, ge=1, le=100)
    severity_min: str = Field(default="MEDIUM", description="Minimum severity to evaluate")
    environment: str | None = Field(
        default=None,
        description="Deployment environment for snapshot-based evaluation",
    )
    agent_id: str | None = Field(
        default=None,
        description="AI agent identifier (e.g., 'claude-code', 'cursor', 'copilot')",
    )
    subject_kind: str | None = Field(
        default=None,
        description=(
            "Subject kind for evaluation dispatch "
            "(code_diff, clause_set, event, transaction, creative, decision, identity, document). "
            "Defaults to code_diff when diff is provided."
        ),
    )


class QuickEvaluateRequest(BaseModel):
    """Simplified request for non-code evaluations."""

    action: str = Field(..., min_length=1, max_length=5000, description="Action to evaluate")
    scope: str | None = None


class ApplicableRulesRequest(BaseModel):
    """Request to get rules that apply to given file paths."""

    file_paths: list[str] = Field(default_factory=list)
    repository: str | None = None
    scope: str | None = None


class CodeLocationResponse(BaseModel):
    """A location in code where an issue was found."""

    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    function_name: str | None = None
    snippet: str | None = None


class RemediationResponse(BaseModel):
    """A machine-readable fix that agents or CI can apply automatically."""

    type: str
    file_path: str
    start_line: int
    end_line: int | None = None
    original: str | None = None
    replacement: str | None = None
    description: str = ""
    auto_applicable: bool = False


class RuleVerdictResponse(BaseModel):
    """Per-rule evaluation verdict."""

    rule_id: str
    rule_statement: str
    verdict: str
    confidence: float
    reasoning: str
    issue_description: str = ""
    fix_suggestion: str | None = None
    locations: list[CodeLocationResponse] = Field(default_factory=list)
    remediations: list[RemediationResponse] = Field(default_factory=list)


class ConflictResolutionResponse(BaseModel):
    """Records how a conflict between two rules was resolved during evaluation."""

    rule_a_id: str
    rule_b_id: str
    relationship: str
    winner_id: str
    reason: str
    discarded_verdict: str


class EvaluateResponse(BaseModel):
    """Response from the evaluation API."""

    evaluation_id: str
    overall_verdict: str
    rule_verdicts: list[RuleVerdictResponse] = Field(default_factory=list)
    violations: list[RuleVerdictResponse] = Field(default_factory=list)
    warnings: list[RuleVerdictResponse] = Field(default_factory=list)
    conflict_resolutions: list[ConflictResolutionResponse] = Field(default_factory=list)
    rules_evaluated: int = 0
    rules_passed: int = 0
    rules_violated: int = 0
    rules_uncertain: int = 0
    fix_summary: str | None = None
    remediations: list[RemediationResponse] = Field(default_factory=list)
    auto_fixable_count: int = 0
    model_ids_used: list[str] = Field(default_factory=list)
    total_latency_ms: int = 0
    timestamp: datetime | None = None

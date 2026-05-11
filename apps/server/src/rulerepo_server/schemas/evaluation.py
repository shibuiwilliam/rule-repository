"""Pydantic schemas for the Evaluation API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FileInput(BaseModel):
    """A file to evaluate (path + optional content)."""

    path: str
    content: str | None = None


class EvaluableSchema(BaseModel):
    """Universal evaluation input (RR-004).

    Clients should prefer this form for non-code evaluations.
    Legacy fields (diff, files, facts) remain supported and are
    auto-translated to this form.
    """

    artifact_type: str = Field(
        default="code_diff",
        description="Artifact type determining domain module dispatch.",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Artifact data — structure varies by artifact_type.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (scope, repository, agent_id, etc.).",
    )
    diff_against: dict[str, Any] | None = Field(
        default=None,
        description="Optional previous version for comparison-based evaluation.",
    )


class EvaluateRequest(BaseModel):
    """Request to evaluate a code change or action against rules.

    Supports two input forms:

    1. **Legacy** (backwards compatible): provide ``diff``, ``files``,
       and/or ``facts`` directly.
    2. **Universal** (RR-004): provide an ``evaluable`` object with
       ``artifact_type`` and ``payload``.

    When both are provided, the ``evaluable`` takes precedence.
    """

    # --- Legacy fields (backwards compatible) ---
    diff: str | None = Field(default=None, description="Unified diff text")
    files: list[FileInput] | None = Field(default=None, description="Files to evaluate")
    facts: dict[str, Any] | None = Field(default=None, description="Free-form context")
    intent: str | None = Field(default=None, description="Description of the change")

    # --- Universal form (RR-004) ---
    evaluable: EvaluableSchema | None = Field(
        default=None,
        description="Universal evaluation input. Takes precedence over legacy fields.",
    )

    # --- Common fields ---
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

    def to_evaluable(self) -> EvaluableSchema:
        """Convert this request to the universal Evaluable form.

        If ``evaluable`` is set, returns it directly.
        Otherwise, constructs one from legacy fields.
        """
        if self.evaluable is not None:
            return self.evaluable

        payload: dict[str, Any] = {}
        if self.diff is not None:
            payload["diff"] = self.diff
        if self.files is not None:
            payload["files"] = [f.model_dump() for f in self.files]
        if self.facts is not None:
            payload["facts"] = self.facts
        if self.intent is not None:
            payload["intent"] = self.intent

        metadata: dict[str, Any] = {}
        if self.scope is not None:
            metadata["scope"] = self.scope
        if self.repository is not None:
            metadata["repository"] = self.repository
        if self.agent_id is not None:
            metadata["agent_id"] = self.agent_id

        # Infer artifact type from inputs: only default to code_diff when
        # a diff is actually provided.  Otherwise use "generic" so non-code
        # subjects are not silently coerced into the code path.
        if self.subject_kind:
            artifact_type = self.subject_kind
        elif self.diff is not None:
            artifact_type = "code_diff"
        elif self.facts is not None:
            artifact_type = "generic"
        else:
            artifact_type = "code_diff"
        return EvaluableSchema(
            artifact_type=artifact_type,
            payload=payload,
            metadata=metadata,
        )


class SubjectEvaluateRequest(BaseModel):
    """Surface-aware evaluation request (Phase 8+).

    Accepts a subject payload specific to the surface type specified
    in the URL path. See CLAUDE.md §14.2.3.
    """

    subject: dict[str, Any] = Field(
        ...,
        description="Surface-specific subject payload.",
    )
    mode: str = Field(
        default="preflight",
        description="Evaluation mode: preflight | posthoc | sidecar",
    )
    max_rules: int = Field(default=20, ge=1, le=100)
    severity_min: str = Field(default="MEDIUM")
    scope: str | None = Field(
        default=None,
        description="Rule scope filter. If omitted, the surface adapter resolves it.",
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

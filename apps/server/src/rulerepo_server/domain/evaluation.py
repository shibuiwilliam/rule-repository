"""Domain models for the Subject-Aware Evaluation Engine.

Pure domain objects with no external dependencies.
Per CLAUDE.md §14.2: Subject, Surface, and Actor are the core abstractions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal


class Surface(StrEnum):
    """The kind of thing being evaluated — one of several first-class surfaces.

    Each surface has a corresponding adapter under services/evaluation/surfaces/.
    See PROJECT.md §5.2 and CLAUDE.md §14.2.1.
    """

    CODE = "code"
    CONTRACT = "contract"
    HUMAN_ACTION = "human_action"
    TRANSACTION = "transaction"
    DOCUMENT = "document"
    MESSAGE = "message"
    GENERIC = "generic"


@dataclass(frozen=True)
class Actor:
    """Who is acting or being evaluated — human, system, or AI agent.

    Replaces the legacy ``agent_id`` string field with a structured model
    that works for all actor kinds. See CLAUDE.md §14.2.1.

    Attributes:
        kind: The actor category.
        identifier: Stable identifier (e.g., ``user:E001``, ``agent:claude-code``).
        attributes: Freeform metadata (trust level, department, etc.).
    """

    kind: Literal["human", "system", "agent"]
    identifier: str
    attributes: dict[str, Any] = field(default_factory=dict)


class Verdict(StrEnum):
    """Result of evaluating an action against a rule."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    ALLOW_WITH_CONDITIONS = "ALLOW_WITH_CONDITIONS"
    REQUIRES_DISCLOSURE = "REQUIRES_DISCLOSURE"


@dataclass(frozen=True)
class CodeLocation:
    """A specific location in code where an issue was found."""

    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    function_name: str | None = None
    snippet: str | None = None


@dataclass(frozen=True)
class FileChange:
    """A structured representation of changes to a single file."""

    path: str
    change_type: str  # "added", "modified", "deleted", "renamed"
    language: str | None = None
    diff_hunks: list[str] = field(default_factory=list)
    functions_touched: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvaluationContext:
    """Unified context for rule evaluation — supports code and non-code inputs.

    The Context Assembler builds this from various input modes:
    - Diff mode: accepts unified diff text
    - File mode: accepts file paths + content
    - Facts mode: key-value facts for non-code evaluations
    - Hybrid: diff + facts combined
    """

    # Code change context
    diff: str | None = None
    files_changed: list[FileChange] = field(default_factory=list)
    file_paths: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    repository: str | None = None
    base_branch: str | None = None

    # Intent
    intent: str | None = None
    actor: str | None = None

    # Free-form context (non-code evaluations)
    facts: dict[str, Any] = field(default_factory=dict)
    narrative: str | None = None


@dataclass(frozen=True)
class Remediation:
    """A machine-readable fix for a rule violation.

    Agents and CI pipelines can apply auto_applicable remediations without human
    review. Non-auto remediations require human approval before application.

    Subclasses provide domain-specific remediation semantics.
    """

    type: str  # "replace", "insert", "delete", "add_import", "rename", "workflow", "clause_revision"
    file_path: str = ""
    start_line: int = 0
    end_line: int | None = None
    original: str | None = None
    replacement: str | None = None
    description: str = ""
    auto_applicable: bool = False


@dataclass(frozen=True)
class CodeRemediation(Remediation):
    """Remediation for code changes — file-level patches."""

    pass  # Inherits all fields; type is "replace", "insert", "delete", "add_import", "rename"


@dataclass(frozen=True)
class ContractClauseRemediation(Remediation):
    """Remediation for contract clauses — suggested clause revisions."""

    clause_id: str = ""
    revised_text: str = ""
    requires_counterparty_consent: bool = True


@dataclass(frozen=True)
class HrEventRemediation(Remediation):
    """Remediation for HR events — corrective actions or approvals."""

    action_required: str = ""  # e.g., "obtain_36_agreement", "reduce_overtime", "file_notification"
    deadline_days: int | None = None
    escalation_target: str = ""  # e.g., "department_head", "labor_standards_office"


@dataclass(frozen=True)
class ExpenseRemediation(Remediation):
    """Remediation for expense claims — return for revision or additional approval."""

    required_documentation: str = ""  # e.g., "original_receipt", "manager_approval"
    revised_amount: float | None = None
    approval_level: str = ""  # e.g., "manager", "department_head", "cfo"


@dataclass(frozen=True)
class WorkflowRemediation(Remediation):
    """Remediation that triggers a workflow or approval process."""

    workflow_type: str = ""  # e.g., "approval", "review", "notification", "hold"
    assignee: str = ""
    priority: str = "normal"  # "low", "normal", "high", "urgent"


@dataclass(frozen=True)
class RuleVerdict:
    """The result of evaluating a single rule against the context."""

    rule_id: str
    rule_statement: str
    verdict: Verdict
    confidence: float
    reasoning: str
    issue_description: str = ""
    fix_suggestion: str | None = None
    locations: list[CodeLocation] = field(default_factory=list)
    remediations: list[Remediation] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Aggregated result of evaluating all applicable rules against a context."""

    evaluation_id: str
    overall_verdict: Verdict
    rule_verdicts: list[RuleVerdict]
    rules_evaluated: int
    rules_passed: int
    rules_violated: int
    rules_uncertain: int
    fix_summary: str | None
    model_ids_used: list[str]
    total_latency_ms: int
    conflict_resolutions: list[dict[str, str]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def violations(self) -> list[RuleVerdict]:
        """Only DENY verdicts."""
        return [v for v in self.rule_verdicts if v.verdict == Verdict.DENY]

    @property
    def warnings(self) -> list[RuleVerdict]:
        """Only NEEDS_CONFIRMATION verdicts."""
        return [v for v in self.rule_verdicts if v.verdict == Verdict.NEEDS_CONFIRMATION]


# ---------------------------------------------------------------------------
# Activity Review (two-tier compliance)
# ---------------------------------------------------------------------------


class Relevance(StrEnum):
    """Classification of a rule's relevance to an activity."""

    RELEVANT = "RELEVANT"
    POTENTIALLY_RELEVANT = "POTENTIALLY_RELEVANT"
    NOT_RELEVANT = "NOT_RELEVANT"


@dataclass(frozen=True)
class RuleRelevanceAssessment:
    """Result of assessing a single rule's relevance to an activity."""

    rule_id: str
    rule_statement: str
    modality: str
    severity: str
    relevance: Relevance
    relevance_score: float
    relevance_reason: str = ""


@dataclass
class RoughReviewResult:
    """Aggregated result of Tier 1 rough compliance review."""

    review_id: str
    total_rules_scanned: int
    assessments: list[RuleRelevanceAssessment]
    llm_triage_used: bool
    latency_ms: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def relevant(self) -> list[RuleRelevanceAssessment]:
        return [a for a in self.assessments if a.relevance == Relevance.RELEVANT]

    @property
    def potentially_relevant(self) -> list[RuleRelevanceAssessment]:
        return [a for a in self.assessments if a.relevance == Relevance.POTENTIALLY_RELEVANT]

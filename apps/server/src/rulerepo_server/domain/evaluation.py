"""Domain models for the Code-Aware Evaluation Engine.

Pure domain objects with no external dependencies.
Per CLAUDE_ENHANCE.md §1.3: these live in domain/ and depend on nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class Verdict(StrEnum):
    """Result of evaluating an action or code change against a rule."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"


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
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @property
    def violations(self) -> list[RuleVerdict]:
        """Only DENY verdicts."""
        return [v for v in self.rule_verdicts if v.verdict == Verdict.DENY]

    @property
    def warnings(self) -> list[RuleVerdict]:
        """Only NEEDS_CONFIRMATION verdicts."""
        return [v for v in self.rule_verdicts if v.verdict == Verdict.NEEDS_CONFIRMATION]

"""Data models for the eval harness.

Pure domain types with no external dependencies. These represent golden
test cases, individual evaluation results, domain-level aggregations,
and full harness run reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class GoldenCase:
    """A single golden test case for LLM verdict accuracy measurement.

    Attributes:
        id: Unique case identifier (e.g., "engineering_001").
        domain: Evaluation domain (e.g., "engineering", "hr", "legal").
        subject_kind: The SubjectKind string used for dispatch.
        description: Human-readable description of what this case tests.
        input_payload: Domain-specific input fed to the evaluation service.
        expected_verdict: Expected verdict string (ALLOW, DENY, NEEDS_CONFIRMATION).
        expected_rule_ids: Rule IDs expected to fire for this case.
        expected_reasoning_keywords: Keywords expected in the reasoning text.
        tags: Categorical tags for filtering (e.g., "security", "overtime").
        difficulty: Case difficulty level (easy, medium, hard).
    """

    id: str
    domain: str
    subject_kind: str
    description: str
    input_payload: dict
    expected_verdict: str
    expected_rule_ids: list[str] = field(default_factory=list)
    expected_reasoning_keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    difficulty: str = "medium"


@dataclass
class EvalResult:
    """Result of running a single golden case through the evaluation service.

    Attributes:
        case_id: The GoldenCase.id that was evaluated.
        actual_verdict: Verdict returned by the evaluation service.
        actual_rule_ids: Rule IDs that fired.
        actual_reasoning: Full reasoning text from the LLM.
        match_verdict: Whether actual_verdict matches expected_verdict.
        match_rules: Whether actual_rule_ids matches expected_rule_ids.
        keyword_hits: Count of expected_reasoning_keywords found in reasoning.
        keyword_total: Total expected_reasoning_keywords for this case.
        latency_ms: Wall-clock time for the evaluation call in milliseconds.
        model_id: Model identifier used for this evaluation.
        prompt_version: Content hash of the prompt template used.
        error: Error message if the evaluation failed, None otherwise.
    """

    case_id: str
    actual_verdict: str = ""
    actual_rule_ids: list[str] = field(default_factory=list)
    actual_reasoning: str = ""
    match_verdict: bool = False
    match_rules: bool = False
    keyword_hits: int = 0
    keyword_total: int = 0
    latency_ms: float = 0.0
    model_id: str = ""
    prompt_version: str = ""
    error: str | None = None


@dataclass
class DomainReport:
    """Aggregated evaluation statistics for a single domain.

    Attributes:
        domain: Domain name (e.g., "engineering").
        total: Total cases evaluated.
        correct_verdict: Count of cases where verdict matched.
        precision: Precision of DENY verdicts (true denials / predicted denials).
        recall: Recall of DENY verdicts (true denials / actual denials).
        f1: Harmonic mean of precision and recall.
        avg_latency_ms: Mean latency across all cases in this domain.
        cases: Individual case results.
    """

    domain: str
    total: int = 0
    correct_verdict: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    avg_latency_ms: float = 0.0
    cases: list[EvalResult] = field(default_factory=list)


@dataclass
class HarnessReport:
    """Full report for a complete eval harness run.

    Attributes:
        run_id: Unique identifier for this run.
        timestamp: When the run started.
        domains: Per-domain reports.
        overall_f1: Weighted F1 across all domains.
        prompt_versions: Mapping of domain to prompt version hash.
        model_ids: Distinct model IDs used during the run.
    """

    run_id: str = field(default_factory=lambda: uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    domains: list[DomainReport] = field(default_factory=list)
    overall_f1: float = 0.0
    prompt_versions: dict[str, str] = field(default_factory=dict)
    model_ids: list[str] = field(default_factory=list)

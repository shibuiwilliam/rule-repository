# Subject-Polymorphic Evaluation Engine

Technical guide for the Rule Repository evaluation engine. This is the core product: it accepts code changes (unified diffs, file paths), business events, contract clauses, transactions, or free-form facts, maps them to relevant rules via a subject-agnostic pipeline, and returns per-rule verdicts with domain-specific remediation guidance.

Source code: `apps/server/src/rulerepo_server/services/evaluation/`

---

## Subject Polymorphism

The evaluation engine is **subject-agnostic**. It does not know about code diffs, contract clauses, or HR events directly. Instead, it delegates to subject-specific adapters via the Subject Registry.

### Subject Kinds

Eight subject kinds are supported, each with its own adapter under `services/evaluation/subjects/`:

| SubjectKind | Adapter | Domain | Example Inputs |
|---|---|---|---|
| `CODE_DIFF` | `code_diff_subject.py` | Engineering | Unified diffs, file changes |
| `CLAUSE_SET` | `clause_set_subject.py` | Legal | Contract clauses, NDA terms |
| `EVENT` | `event_subject.py` | HR / Operations | Overtime registrations, leave requests |
| `TRANSACTION` | `transaction_subject.py` | Finance | Expense submissions, purchase orders |
| `CREATIVE` | `creative_subject.py` | Marketing | Ad copy, promotional materials |
| `DECISION` | `decision_subject.py` | Management | Approval decisions, policy exceptions |
| `IDENTITY` | `identity_subject.py` | Compliance | KYC checks, sanctions screening |
| `DOCUMENT` | `document_subject.py` | General | Policy documents, handbooks |

### Subject Registry

The registry uses a `@register(SubjectKind.X)` decorator pattern:

```python
# services/evaluation/subject_registry.py
_REGISTRY: dict[SubjectKind, type[SubjectAdapter]] = {}

def register(kind: SubjectKind):
    def decorator(cls): ...

def resolve(kind: SubjectKind) -> SubjectAdapter:
    return _REGISTRY[kind]()
```

The orchestrator calls `subject_registry.resolve(subject_kind)` once and never branches on the kind directly. Domain logic lives entirely in the adapters.

### Adding a New Subject

1. Define the `facts` schema (Pydantic) for the new domain.
2. Implement `services/evaluation/subjects/<kind>_subject.py` decorated with `@register`.
3. Add prompt templates under `services/evaluation/subjects/prompts/<kind>/`.
4. Implement domain-specific aggregation if needed in `services/evaluation/<kind>_aggregator.py`.
5. Add tests under `tests/evaluation/subjects/test_<kind>_subject.py`.
6. Update `RuleModel.subject_kinds` indexing.

### Backward Compatibility

`EvaluateRequest.subject_kind` defaults to `CODE_DIFF`. Existing callers (CI, GitHub App, Claude Code hooks) see no change.

---

## Pipeline Overview

The evaluation engine is a 4-stage pipeline orchestrated by `EvaluationService` in `services/evaluation/service.py`:

```
Input
  |
  v
SubjectRegistry   (resolve subject adapter for the given subject_kind)
  |
  v
ContextAssembler  (normalize inputs into EvaluationContext)
  |
  v
RuleSelector      (narrow corpus to ~5-20 relevant rules)
  |                supports: environment-based snapshot, federation, or live corpus
  |                filters by subject_kind, classification, scope
  v
EvaluationCore    (LLM-as-Judge per rule, subject-agnostic, concurrent via asyncio.gather)
  |
  v
VerdictAggregator (combine per-rule verdicts, generate fix summary)
  |                conflict-aware aggregation resolves OVERRIDES/DEPENDS_ON
  v
EvaluationResult  (returned to caller, logged to audit)
```

The `EvaluationService.evaluate()` method runs all stages in sequence. It also handles audit logging after aggregation, writing model IDs, latency, file paths, and verdict counts to the audit log via `AuditLogRepository`.

The `evaluate()` method accepts an optional `environment` parameter. When set, the rule selector uses the snapshot deployed to that environment instead of the live rule corpus.

---

## Domain Models

All domain models live in `domain/evaluation.py`. They are pure Python dataclasses with no external dependencies.

### EvaluationContext

The unified input structure built by the Context Assembler. Supports code and non-code evaluation inputs.

```python
@dataclass(frozen=True)
class EvaluationContext:
    # Code change context
    diff: str | None = None                          # Raw unified diff text
    files_changed: list[FileChange] = []             # Parsed file changes
    file_paths: list[str] = []                       # All affected file paths
    languages: list[str] = []                        # Detected languages (sorted)
    repository: str | None = None                    # Repository identifier
    base_branch: str | None = None                   # Base branch name

    # Intent
    intent: str | None = None                        # NL description of the change
    actor: str | None = None                         # Who triggered evaluation

    # Free-form context (non-code evaluations)
    facts: dict[str, Any] = {}                       # Key-value context pairs
    narrative: str | None = None                     # Auto-generated from intent/facts
```

### FileChange

Structured representation of changes to a single file, produced by the diff parser.

```python
@dataclass(frozen=True)
class FileChange:
    path: str                                        # File path (relative)
    change_type: str                                 # "added", "modified", "deleted", "renamed"
    language: str | None = None                      # Detected from extension
    diff_hunks: list[str] = []                       # Individual diff hunks
    functions_touched: list[str] = []                # Best-effort function name extraction
```

### CodeLocation

A specific location in code where an issue was found. Used in `RuleVerdict.locations` to give file:line references.

```python
@dataclass(frozen=True)
class CodeLocation:
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    function_name: str | None = None
    snippet: str | None = None
```

### RuleVerdict

The result of evaluating a single rule against the context. Returned by the Evaluation Core for each rule.

```python
@dataclass(frozen=True)
class RuleVerdict:
    rule_id: str
    rule_statement: str
    verdict: Verdict                                 # ALLOW | DENY | NEEDS_CONFIRMATION
    confidence: float                                # 0.0 to 1.0
    reasoning: str                                   # LLM explanation
    issue_description: str = ""                      # Human-readable issue
    fix_suggestion: str | None = None                # Actionable fix
    locations: list[CodeLocation] = []               # Where in code
```

### EvaluationResult

Aggregated output of the full pipeline. Includes computed properties for filtering verdicts.

```python
@dataclass
class EvaluationResult:
    evaluation_id: str                               # UUID
    overall_verdict: Verdict                         # Worst-case aggregation
    rule_verdicts: list[RuleVerdict]                 # All per-rule results
    rules_evaluated: int
    rules_passed: int                                # ALLOW count
    rules_violated: int                              # DENY count
    rules_uncertain: int                             # NEEDS_CONFIRMATION count
    fix_summary: str | None                          # Numbered fix list
    model_ids_used: list[str]                        # Deduplicated model IDs
    total_latency_ms: int                            # End-to-end pipeline time
    timestamp: datetime                              # UTC

    @property
    def violations(self) -> list[RuleVerdict]:       # Only DENY verdicts
    @property
    def warnings(self) -> list[RuleVerdict]:         # Only NEEDS_CONFIRMATION verdicts
```

### Verdict (enum)

```python
class Verdict(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
```

---

## Stage 1: Context Assembler

**File**: `services/evaluation/context_assembler.py`

The `assemble_context()` function normalizes various input modes into a single `EvaluationContext`.

### Input Modes

| Mode | Triggered when | What it does |
|---|---|---|
| **Diff mode** | `diff` parameter is provided | Parses unified diff via `parse_unified_diff()`. Extracts `FileChange` objects with paths, languages, hunks, and touched functions. |
| **File mode** | `files` parameter is provided | Accepts `[{"path": ..., "content": ...}]` dicts. Detects language from file extension. Creates `FileChange` with `change_type="modified"`. |
| **Facts mode** | `facts` parameter is provided (no diff) | Builds a narrative from key-value pairs. Used for non-code evaluations (policy checks, compliance). |
| **Hybrid** | Both `diff` and `facts` provided | Combines diff-parsed files with facts. Both are available to the evaluation core. |

### Diff Parser (`services/evaluation/diff_parser.py`)

The diff parser is a simple state machine that handles standard `git diff` output. No external dependencies.

**Language detection**: Maps file extensions to language names via `_LANG_MAP` (supports 25+ languages including Python, TypeScript, Go, Rust, Java, etc.).

**Function detection**: Best-effort regex extraction of function/class names from diff text. Patterns cover Python (`def`/`class`), JS/TS (`function`), Go (`func`), and Rust (`fn`).

**Change type detection**: Reads git diff metadata lines (`new file`, `deleted file`, `rename from`) to classify changes.

---

## Stage 2: Rule Selector

**File**: `services/evaluation/rule_selector.py`

The `select_rules()` function narrows the full rule corpus to the relevant subset. It supports three rule source modes and a multi-stage filter pipeline.

### Rule Source Modes

The selector checks these in order, using the first that applies:

1. **Environment mode** (`environment` parameter set): Looks up the active `RuleSetDeploymentModel` for the given environment, fetches the associated `RuleSetSnapshotModel`, and deserializes its `rule_snapshot` via `snapshots/serializer.py`. This gives deterministic evaluation against a pinned rule set. If no active deployment is found, falls through to the default pipeline.

2. **Federation mode** (`federation_id` parameter set): Delegates to `federation/resolver.py` to walk the ancestor chain and apply overrides, producing the effective rule set for that federation node.

3. **Default pipeline** (neither set): Runs the multi-stage filter pipeline below.

### Selection Pipeline (Default)

**Stage 1 -- Scope SQL filter**: Queries PostgreSQL for rules with status `APPROVED` or `EFFECTIVE`. If a scope is provided, filters by `scope.contains([scope])`. Loads up to 500 candidates in a single query.

**Stage 2 -- Severity and modality filter** (in-memory): Removes rules below the minimum severity threshold. In preflight mode, only `MUST` and `MUST_NOT` modalities pass. In posthoc mode, `SHOULD` is also included.

**Stage 3 -- File-path relevance scoring** (in-memory): If the context has file paths or languages, computes a relevance score for each rule based on:
- Scope overlap with file paths (+10.0 per match)
- Scope overlap with languages (+5.0 per match)
- Tag overlap with languages (+3.0 per match)
- Tag overlap with file paths (+2.0 per match)
- Severity bonus (CRITICAL +5, HIGH +3, MEDIUM +1, LOW +0)

Rules are sorted by score descending.

**Stage 4 -- Budget cap**: Returns at most `max_rules` (default 20).

### Performance Target

Stages 1-3 target < 50ms since they are SQL + in-memory operations. Stage 4 (semantic ranking via Elasticsearch vector search) is available as a fallback but is not currently wired into the default pipeline -- the in-memory relevance scoring handles most cases.

### Dedup via Neo4j

Neo4j-based deduplication (removing rules that are superseded or overridden by others in the selected set) is planned but not yet wired into the selector. Currently, superseded rules are excluded by the status filter (only `APPROVED`/`EFFECTIVE` pass).

---

## Stage 3: Evaluation Core

**File**: `services/evaluation/evaluation_core.py`

The core of the engine: evaluates each selected rule against the context using the LLM-as-Judge pattern.

### Model Selection by Severity

Model and thinking level are selected based on rule severity:

| Rule Severity | Model | Thinking Level |
|---|---|---|
| LOW, MEDIUM | `gemini-3-flash-preview` (from `LLM_DEFAULT_MODEL`) | `low` |
| HIGH | `gemini-3-flash-preview` (from `LLM_DEFAULT_MODEL`) | `medium` |
| CRITICAL | `gemini-3.1-pro-preview` (from `LLM_JUDGE_MODEL`) | `high` |

Configuration is centralized in `core/llm.py`. The `LLMConfig` dataclass holds `model_id` and `thinking_level`. Model IDs are read from environment variables, never hardcoded.

### Structured JSON Output

Every LLM call uses `response_mime_type="application/json"` with a `response_json_schema` to enforce structured output. The schema requires:

```json
{
  "verdict": "ALLOW | DENY | NEEDS_CONFIRMATION",
  "confidence": 0.0-1.0,
  "reasoning": "...",
  "issue_description": "...",
  "fix_suggestion": "...",
  "locations": [
    {
      "file_path": "...",
      "start_line": 42,
      "end_line": 45,
      "function_name": "...",
      "snippet": "..."
    }
  ]
}
```

Only `verdict`, `confidence`, and `reasoning` are required fields. The rest are optional.

### Prompt Selection

Prompt templates are organized by subject kind. Each subject adapter owns its prompts under `services/evaluation/subjects/prompts/<kind>/`. The core evaluation pipeline also has shared templates in `services/evaluation/prompts/`:

- `evaluate_code_change.txt` -- Used by `CodeDiffSubject` when `context.diff` is present. Template variables: `rule_statement`, `modality`, `severity`, `diff` (capped at 8000 chars), `file_paths`.
- `evaluate_facts.txt` -- Used for non-code evaluations. Template variables: `rule_statement`, `modality`, `severity`, `narrative`, `facts` (JSON).

Each subject adapter may provide its own `render_for_llm()` method that formats facts in a domain-appropriate way before sending to the LLM.

### Concurrent Execution

The `EvaluationService` dispatches all rule evaluations concurrently using `asyncio.gather()`:

```python
tasks = [evaluate_rule(rule, context, self._gemini_client) for rule in rules]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

Failed tasks are logged and skipped. The aggregator works with whatever verdicts succeeded.

### Error Handling

If an LLM call fails (network error, invalid response, etc.), the rule receives `NEEDS_CONFIRMATION` with confidence 0.0 and the error message in `reasoning`. This ensures failures are surfaced rather than silently allowing.

### Temperature

Temperature is always left at the default 1.0 per CLAUDE.md section 9.3. Lower temperatures degrade Gemini 3 reasoning quality. This is enforced by not setting the temperature parameter in `GenerateContentConfig`.

---

## Stage 4: Verdict Aggregator

**File**: `services/evaluation/verdict_aggregator.py`

The `aggregate_verdicts()` function combines per-rule verdicts into a single `EvaluationResult`.

### Aggregation Logic

The overall verdict follows a worst-case rule:

1. If any rule verdict is `DENY` -> overall verdict is `DENY`
2. Else if any rule verdict is `NEEDS_CONFIRMATION` -> overall verdict is `NEEDS_CONFIRMATION`
3. Else -> overall verdict is `ALLOW`

### Fix Summary Generation

The `_build_fix_summary()` function generates a numbered list from violation and warning verdicts:

```
Fix 2 violation(s):
  1. Define a ProcessRefundRequest Pydantic model
  2. Add type hints to the process_refund function

Review 1 warning(s):
  1. Missing docstring on new public function
```

Only `DENY` verdicts with a `fix_suggestion` and `NEEDS_CONFIRMATION` verdicts with an `issue_description` contribute to the summary.

### Edge Cases

If no rules are selected (empty corpus for the given scope/context), the aggregator returns `ALLOW` with zero rules evaluated. This is also the behavior when no Gemini client is configured.

---

## API Endpoints

All evaluation endpoints are defined in `api/v1/evaluation.py`.

### POST /api/v1/evaluate

Full evaluation pipeline. Accepts:

```json
{
  "subject_kind": "code_diff",
  "diff": "unified diff text",
  "files": [{"path": "src/foo.py", "content": "..."}],
  "facts": {"key": "value"},
  "intent": "Adding refund endpoint",
  "scope": "engineering/python",
  "repository": "payments-api",
  "mode": "preflight",
  "max_rules": 20,
  "severity_min": "MEDIUM",
  "environment": "production"
}
```

The `subject_kind` parameter defaults to `"code_diff"` for backward compatibility. Valid values: `code_diff`, `clause_set`, `event`, `transaction`, `creative`, `decision`, `identity`, `document`.

The `environment` parameter is optional. When set (e.g., `"production"`), the evaluation uses the snapshot deployed to that environment instead of the live rule corpus. This enables reproducible evaluation against a pinned rule set.

Returns `EvaluateResponse` with overall verdict, per-rule verdicts, violations, warnings, fix summary, model IDs used, and latency.

### POST /api/v1/evaluate/quick

Simplified evaluation for non-code actions. Accepts:

```json
{
  "action": "Deploy to production without running tests",
  "scope": "engineering/deployment"
}
```

Internally calls the full pipeline with `facts={"action": action}` and `mode="preflight"`.

### POST /api/v1/evaluate/applicable-rules

Rule discovery without running LLM evaluation. Returns the list of rules that would apply to given file paths. Useful for preflight hooks.

```json
{
  "file_paths": ["src/api/payment.py"],
  "repository": "payments-api",
  "scope": "engineering/python"
}
```

Returns a list of rule dicts (id, statement, modality, severity, scope, tags, rationale).

### GET /api/v1/evaluate/{id}

Retrieve a past evaluation by ID. Currently implemented via the audit log rather than a dedicated evaluation store.

---

## Caching

The evaluation core computes a cache key from `hash(rule_id + version + context_hash + model_id + prompt_version)` via SHA-256. The `_hash_content()` utility in `evaluation_core.py` produces a 16-character hex digest.

Cache storage is in PostgreSQL (via the audit log and evaluation records). Cache invalidation occurs on rule revision -- when a rule is updated, evaluations using the old version are no longer served from cache.

---

## Audit Logging

Every evaluation is logged to the audit log via `AuditLogRepository.append()`. The audit entry includes:

| Field | Content |
|---|---|
| `action` | `"evaluate"` |
| `actor` | Caller identity or `"system"` |
| `resource_type` | `"evaluation"` |
| `resource_id` | The `evaluation_id` (UUID) |
| `details.overall_verdict` | `ALLOW`, `DENY`, or `NEEDS_CONFIRMATION` |
| `details.rules_evaluated` | Number of rules checked |
| `details.rules_violated` | Number of DENY verdicts |
| `details.mode` | `"preflight"` or `"posthoc"` |
| `details.has_diff` | Whether a diff was provided |
| `details.file_paths` | First 10 file paths |
| `details.model_ids` | Deduplicated list of Gemini model IDs used |
| `details.latency_ms` | End-to-end pipeline latency |

The audit log table is append-only with hash chaining (each row links to the previous via a hash column). Updates and deletes are rejected by a PostgreSQL trigger.

---

## Key Implementation Notes

- The diff is capped at 8000 characters before being sent to the LLM to stay within token budgets.
- Modality filter defaults to `["MUST", "MUST_NOT"]` in preflight mode and adds `"SHOULD"` in posthoc mode.
- If no Gemini client is available (missing API key), the pipeline returns `ALLOW` with zero rules evaluated rather than failing.
- All structured logging uses `structlog` with JSON output. Never `print()`.
- Prompt files live in `services/evaluation/prompts/` and are loaded at call time via `_load_prompt()`. They are versioned in git.
- The `environment` parameter flows from the API layer through `EvaluationService.evaluate()` to `rule_selector.select_rules()`, where it triggers snapshot-based rule resolution.

---

## Domain-Specific Engines (Phase 8)

### Contract Clause Engine

**Endpoint**: `POST /api/v1/evaluate/contract` (`api/v1/contract.py`)

The contract engine wraps the standard evaluation pipeline with clause-specific parsing, comparison, and aggregation:

1. **Parse**: `adapters/contract_parser.py` accepts DOCX (via `python-docx`), PDF (via Gemini Files API), or plain text. Delegates to `services/extraction/contract/clause_segmenter.py` for clause identification and `clause_classifier.py` for type detection. Returns a `ParsedContract`.
2. **Compare** (optional): `adapters/contract_compare.py` matches draft clauses against standard clauses by type and semantic similarity (embedding-based). Returns a `ComparisonResult` with per-clause diffs.
3. **Evaluate**: Constructs a `ClauseSetSubject` and routes through `EvaluationService.evaluate(subject_kind=CLAUSE_SET)`.
4. **Aggregate**: `services/evaluation/clause_aggregator.py` collapses clause-level verdicts to a contract-level verdict:
   - Any DENY on a MUST/MUST_NOT rule produces contract-level DENY
   - Any NEEDS_CONFIRMATION on a CRITICAL rule produces contract-level NEEDS_CONFIRMATION
   - Otherwise ALLOW

**Review types** (via `review_type` parameter):
- `self_conformance` — Compare draft clauses against company standard clauses
- `cross_contract` — Detect contradictions with existing contracts
- `regulatory_compliance` — Check clauses against regulatory rules
- `risk_scoring` — Score each clause for risk factors

**Prompt templates**: `services/evaluation/prompts/clause_set/` — `evaluate_clause.txt`, `compare_clauses.txt`, `risk_score_clause.txt`.

All contract remediations have `auto_applicable=false` by default.

### Event Engine with Temporal Modes

**Endpoint**: `POST /api/v1/evaluate/event` (`api/v1/event.py`)

The event engine extends single-event evaluation with temporal reasoning for HR compliance:

**Evaluation modes** (via `evaluation_mode` parameter):
- `single` (default) — Evaluate the event alone
- `sequence` — Include an `EventWindow` (monthly prior events) as context for cumulative threshold detection (e.g., 45-hour monthly overtime cap)
- `calendar` — Include a `CalendarContext` (annual aggregates) for annual ceiling enforcement (e.g., 720-hour annual cap, 36-Agreement thresholds)

**Domain types** (`domain/event_sequence.py`):
- `EventEvaluationMode` — enum: `SINGLE`, `SEQUENCE`, `CALENDAR`
- `EventRecord` — a historical event with type, date, value, unit
- `EventWindow` — time-bounded window with events and pre-computed aggregates (total, count, average)
- `CalendarContext` — fiscal year aggregates: YTD overtime, monthly breakdown, 36-Agreement status
- `SequenceContext` — combined wrapper for both window and calendar

**Prompt templates**: `services/evaluation/prompts/event/` — `evaluate_sequence.txt`, `evaluate_calendar.txt`.

The caller provides temporal context. In production, HR system adapters (Workday, SmartHR, freee HR) query recent events and aggregates.

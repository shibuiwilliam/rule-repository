# Evaluation Engine

The Subject-Polymorphic Evaluation Engine is the core product capability. It accepts code changes, contract clauses, HR events, financial transactions, communications, or free-form facts as input, maps them to relevant rules in the corpus, and returns structured verdicts with actionable remediation. Eight subject kinds and seven evaluation surfaces allow the same pipeline to handle any domain.

## Pipeline

The evaluation runs through five stages:

```
Context Assembly  -->  Rule Selection  -->  Kind Dispatch  -->  LLM Judgment  -->  Verdict Aggregation
                                              │
                                              ├── COMPUTATIONAL (with constraints) → Deterministic Evaluator → PASS/FAIL (skip LLM)
                                              ├── COMPUTATIONAL (no constraints) → regex fallback → LLM if INDETERMINATE
                                              ├── PROCEDURAL → state-transition check → LLM if INDETERMINATE
                                              ├── DEFINITIONAL → always ALLOW (no LLM)
                                              ├── PRINCIPLE → always ALLOW (no LLM)
                                              └── NORMATIVE → LLM Judgment (existing path)
```

### 1. Context Assembly

Accepts three kinds of input (any combination):

- **Diffs**: unified diff text is parsed into structured `FileChange` objects with language detection and function extraction.
- **Files**: file paths with optional content, used for scope matching and context.
- **Facts**: a free-form dictionary of key-value pairs describing the situation.

All inputs are combined into an evaluation context that the subsequent stages consume.

### 2. Rule Selection

Narrows the full rule corpus to a manageable set of 5--20 relevant rules:

1. **Metadata filtering**: scope, severity minimum, modality, tags, and effective date.
2. **Semantic ranking**: the remaining candidates are ranked by relevance to the evaluation context using vector similarity.

The metadata stage runs in under 50ms. The full selection is designed to avoid sending irrelevant rules to the LLM.

### 3. Kind Dispatch (Hybrid Evaluation)

Before sending rules to the LLM, the batch evaluator partitions them by `kind` (see `kind_dispatch.py`):

- **NORMATIVE** rules proceed to the LLM batch evaluation (stage 4).
- **COMPUTATIONAL** rules with structured `constraints` are evaluated by the **DeterministicEvaluator** (`deterministic/evaluator.py`). This layer checks numeric thresholds (`amount <= 100000`), date comparisons, and enum validations against the subject's facts. If all constraints pass → ALLOW (confidence 0.95, no LLM call). If any fail → DENY (confidence 0.95, no LLM call). If the relevant facts are missing → INDETERMINATE, and the rule falls through to the LLM.
- **COMPUTATIONAL** rules without constraints fall back to a regex-based threshold extraction from the rule statement, then heuristic matching against fact keys.
- **PROCEDURAL** rules check for ordering constraints against `steps`/`sequence` facts.
- **DEFINITIONAL** rules always return ALLOW — they define terms, not constraints.
- **PRINCIPLE** rules always return ALLOW — they are evaluated through their derived normative rules.

This dispatch reduces LLM token consumption significantly for quantitative rules (expense caps, overtime limits, date deadlines) while preserving LLM judgment for normative interpretation.

**Constraint types** (stored as JSONB on rules):
- `NumericConstraint`: `{field_path, operator, threshold, unit}` — e.g., `{field_path: "monthly_overtime_hours", operator: "<=", threshold: 45, unit: "hours"}`
- `DateConstraint`: `{field_path, operator, reference_date}`
- `EnumConstraint`: `{field_path, allowed_values}`
- `LookupConstraint`: `{field_path, lookup_table, key_column, result_column}` — table-driven lookups evaluated by the `lookup_evaluator`

### 4. LLM Judgment (Batched)

All selected NORMATIVE rules (and INDETERMINATE computational rules) are sent to Gemini in a **single batched API call** using structured JSON output. The batch evaluator selects a **surface-specific prompt template** based on the `surface` field of the evaluation context (e.g., `evaluate_batch_contract.txt` for contracts, `evaluate_batch_transaction.txt` for transactions). Each surface template defines its own location format and remediation kinds. The prompt lists every rule alongside the subject content and requests an array of per-rule verdicts.

**Tiered model strategy:**

| Scenario | Model | Thinking Level |
|---|---|---|
| Batch call (all rules) | Gemini 3 Flash | medium |
| Pro confirmation (DENY + CRITICAL only) | Gemini 3.1 Pro | high |
| Single-rule fallback | Severity-based (Flash or Pro) | low / medium / high |

If the batch call fails (API error, token budget exceeded, response parsing failure), the system falls back transparently to per-rule concurrent evaluation via `asyncio.gather()`.

Each rule judgment produces: a verdict (ALLOW, DENY, or NEEDS_CONFIRMATION), a confidence score, reasoning, issue description, fix suggestion, and domain-specific locations (code file/line, contract clause references, transaction JSON paths, document spans, or message segments depending on the surface).

See [Batched Evaluation](batch-evaluation.md) for full architectural details.

### 3b. Evaluation Persistence

After LLM judgment, each per-rule verdict is persisted to the `evaluations` table. This enables fast analytics queries without parsing audit log JSON. The intelligence dashboard and analytics endpoints query this table with a fallback to audit log for historical data.

### 4. Verdict Aggregation

Per-rule verdicts are combined:

- Any **DENY** produces an overall DENY.
- Any **NEEDS_CONFIRMATION** (with no DENY) produces an overall NEEDS_CONFIRMATION.
- All **ALLOW** produces an overall ALLOW.

The aggregator also builds a fix summary that consolidates all fix suggestions.

## What It Accepts

The `POST /api/v1/evaluate` endpoint accepts:

| Field | Type | Description |
|---|---|---|
| `diff` | string | Unified diff text |
| `files` | list | File paths with optional content |
| `facts` | dict | Free-form context key-value pairs |
| `intent` | string | Description of the change or action |
| `scope` | string | Rule scope filter |
| `repository` | string | Repository identifier for scope matching |
| `mode` | string | `preflight` (before action) or `posthoc` (after action) |
| `max_rules` | int | Maximum rules to evaluate (1--100, default 20) |
| `severity_min` | string | Minimum severity to include (default MEDIUM) |

## What It Returns

| Field | Description |
|---|---|
| `overall_verdict` | ALLOW, DENY, or NEEDS_CONFIRMATION |
| `rule_verdicts` | Per-rule verdicts with confidence, reasoning, code locations, and remediations |
| `violations` | Subset of rule_verdicts where verdict is DENY |
| `warnings` | Subset of rule_verdicts where verdict is NEEDS_CONFIRMATION |
| `remediations` | Machine-readable fix objects (type, file_path, start_line, original, replacement, auto_applicable) |
| `auto_fixable_count` | Number of remediations safe for automatic application |
| `fix_summary` | Consolidated fix suggestions across all violations |
| `evaluation_id` | Unique ID for audit trail lookup |
| `rules_evaluated` | Count of rules evaluated |
| `rules_passed` / `rules_violated` / `rules_uncertain` | Verdict counts |
| `model_ids_used` | Which Gemini models were invoked |
| `total_latency_ms` | End-to-end evaluation latency |

## Shadow Mode (Rule Maturity)

Rules with `maturity_level=experimental` operate in shadow mode: if the LLM returns DENY, the evaluation engine downgrades the verdict to NEEDS_CONFIRMATION and prefixes the reasoning with `[SHADOW]`. This means experimental rules observe but never block. Rules automatically promote to `stable` and then `proven` based on their false-positive rate (managed by the `auto_promote_rules` background worker).

## Additional Endpoints

- **`POST /api/v1/evaluate/quick`**: simplified evaluation for non-code actions. Accepts an `action` string and optional `scope`.
- **`POST /api/v1/evaluate/applicable-rules`**: returns rules that apply to given file paths without running evaluation. Useful for rule discovery.

See [Evaluate API](../api/evaluate.md) for request/response examples.

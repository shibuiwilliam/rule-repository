# ADR 0004: Contract Clause Engine

## Status

Accepted

## Context

Phase 7 introduced Subject Polymorphism and the `ClauseSetSubject` adapter skeleton. Phase 8 requires a full Contract Clause Engine that can parse contracts, compare clauses against standards, aggregate clause-level verdicts, and return clause-scoped remediations.

The existing infrastructure includes:
- `domain/contract.py` — `ContractType`, `PartyRole`, `ContractScope`
- `subjects/contract_clause.py` — `ClauseSetAdapter` registered for `SubjectKind.CLAUSE_SET`
- `services/extraction/contract/` — `clause_segmenter`, `clause_classifier`, `reference_resolver`
- `domain/evaluation.py` — `ContractClauseRemediation` extending `Remediation`

What's missing:
- `adapters/contract_parser.py` — DOCX/PDF clause extraction with structure preservation
- `adapters/contract_compare.py` — semantic clause-level diffing
- `services/evaluation/clause_aggregator.py` — clause-by-clause verdict aggregation to contract-level verdict
- Evaluation modes: self-conformance, cross-contract conflict, regulatory compliance, risk scoring
- Prompt templates for clause evaluation
- `POST /api/v1/evaluate/contract` endpoint

## Decision

### 1. Contract Parser Adapter

`adapters/contract_parser.py` provides a `ContractParser` class that:

- Accepts DOCX via `python-docx` (extracts text with structure preservation — headings, lists, tables)
- Accepts PDF via Gemini Files API (OCR with `media_resolution_medium`)
- Accepts plain text (direct pass-through)
- Delegates to `services/extraction/contract/clause_segmenter.py` for clause identification
- Delegates to `services/extraction/contract/clause_classifier.py` for clause type detection
- Returns a `ParsedContract` containing `SegmentedDocument` + classified clauses + metadata

### 2. Contract Comparator Adapter

`adapters/contract_compare.py` provides a `ContractComparator` class that:

- Takes a draft contract (parsed) and a standard contract (parsed or rule-backed standard clauses)
- Matches clauses by type and semantic similarity (embedding-based matching via the LLM provider)
- Returns a `ComparisonResult` with per-clause diffs: matched pairs, unmatched draft clauses, missing standard clauses
- Each diff includes a similarity score and the specific deviation description

### 3. Clause Aggregator

`services/evaluation/clause_aggregator.py`:

- Takes a list of `RuleVerdict` objects scoped to individual clauses
- Aggregates to a contract-level verdict:
  - Any DENY on a MUST/MUST_NOT rule → contract-level DENY
  - Any NEEDS_CONFIRMATION on a CRITICAL rule → contract-level NEEDS_CONFIRMATION
  - Otherwise ALLOW
- Produces a `clause_verdict_map: dict[str, list[RuleVerdict]]` for the UI to display per-clause

### 4. Evaluation Modes

The contract evaluation endpoint accepts a `review_type` parameter:

- `self_conformance` — Compare draft clauses against the company's standard clauses (rules with `subject_kinds` including `clause_set`)
- `cross_contract` — Detect contradictions with existing contracts (requires rule corpus search)
- `regulatory_compliance` — Check clauses against applicable regulations (rules scoped to `legal/regulatory/*`)
- `risk_scoring` — Score each clause for risk level (uncapped liability, exclusive jurisdiction, IP assignment)

All modes produce `ContractClauseRemediation` with `auto_applicable=false` by default.

### 5. API Endpoint

`POST /api/v1/evaluate/contract` is a convenience endpoint that:

1. Accepts a contract body (text, or file upload reference) with metadata
2. Parses it via `ContractParser`
3. Constructs a `ClauseSetSubject` with the parsed clauses
4. Routes to `EvaluationService.evaluate()` with `subject_kind=clause_set`
5. Post-processes with `ClauseAggregator`
6. Returns `ContractEvaluateResponse` with contract-level verdict + per-clause breakdown

### 6. Prompt Templates

Prompt templates under `services/evaluation/subjects/prompts/clause_set/`:
- `evaluate_clause.md` — evaluate a single clause against a rule
- `compare_clauses.md` — compare a draft clause against a standard clause
- `risk_score_clause.md` — score a clause for risk factors

Templates are owned by the `ClauseSetAdapter`, not the orchestrator.

## Consequences

- Contract review flows end-to-end: upload → parse → evaluate → clause verdicts → remediations
- The existing extraction pipeline (segmenter, classifier, resolver) is reused
- The evaluation orchestrator remains subject-agnostic
- `auto_applicable=false` on all contract remediations by default (safe posture)
- The UI can render per-clause verdicts using the `clause_verdict_map`

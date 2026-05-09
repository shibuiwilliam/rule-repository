# Phase 8 Backlog — Domain Engines and Discovery

> Ordered work items for Phase 8. Each stream produces one or more PRs.
> Phase 7 is [COMPLETE]. This phase builds on Subject Polymorphism, Department/Capacity, and Classification foundations.

---

## Status: IN PROGRESS

Started: 2026-05-08

### Completed (2026-05-08)

- Stream A: Contract Clause Engine — ADR accepted, parser, comparator, clause aggregator, prompt templates, API endpoint, unit tests
- Stream B: Event Engine Temporal Modes — ADR accepted, domain types, sequence/calendar modes, prompt templates, API endpoint, unit tests
- Stream C (partial): Document Discovery — DocumentSource/IncrementalSource protocols, contract corpus analyzer, contract DOCX source upgraded
- Stream D (partial): Domain-Aware UX — route groups for legal/hr/finance/marketing with layouts, contract review page, event review page

---

## Stream A — Contract Clause Engine

The first non-engineering evaluation engine. Operates on `ClauseSetSubject` from Phase 7.

| # | Work Item | Size | PR | Status |
|---|---|---|---|---|
| A1 | ADR `0004-contract-clause-engine.md` | S | 884fe95 | DONE |
| A2 | `adapters/contract_parser.py` — DOCX/PDF clause extraction with structure preservation | M | 884fe95 | DONE |
| A3 | `adapters/contract_compare.py` — semantic clause-level diffing | M | 884fe95 | DONE |
| A4 | `services/evaluation/clause_aggregator.py` — clause-by-clause verdict → contract-level verdict | M | 884fe95 | DONE |
| A5 | Upgrade `ClauseSetSubject` with full prompt templates under `subjects/prompts/clause_set/` | M | 884fe95 | DONE |
| A6 | Evaluation modes: self-conformance, cross-contract conflict, regulatory compliance, risk scoring | L | 884fe95 | DONE |
| A7 | `POST /api/v1/evaluate/contract` endpoint | S | 884fe95 | DONE |
| A8 | Unit tests (mocked LLM) + integration tests | M | 884fe95 | DONE |

**Definition of Done:**
- A contract draft (DOCX/PDF) can be uploaded, parsed into clauses, evaluated against standard-clause rules, and return clause-scoped verdicts with proposed rewrites.
- `clause_remediation` extends `Remediation` with `auto_applicable=false` by default.
- Clause aggregator collapses clause verdicts to a contract-level verdict.
- All existing tests pass; new tests cover all four evaluation modes.

---

## Stream B — Event Engine Sequence/Calendar Modes

Extends the existing `EventSubject` (single-event mode from Phase 7) with temporal reasoning.

| # | Work Item | Size | PR | Status |
|---|---|---|---|---|
| B1 | ADR `0005-event-engine-temporal-modes.md` | S | 884fe95 | DONE |
| B2 | `EventWindow` and `SequenceContext` domain types | S | 884fe95 | DONE |
| B3 | Sequence-aware evaluation mode — monthly accumulations in rule context | M | 884fe95 | DONE |
| B4 | Calendar-aware evaluation mode — annual ceilings, 36-Agreement thresholds | M | 884fe95 | DONE |
| B5 | `POST /api/v1/evaluate/event` update to accept `mode` parameter (single/sequence/calendar) | S | 884fe95 | DONE |
| B6 | HR system adapter stubs: `adapters/hr_systems/{workday,smarthr,freee_hr}.py` | M | | PENDING |
| B7 | Unit tests per mode + integration test with HR attendance pack | M | 884fe95 | DONE |

**Definition of Done:**
- Sequence mode evaluates a monthly overtime window (e.g., 46th cumulative hour triggers violation).
- Calendar mode evaluates annual ceilings (e.g., 720-hour annual cap).
- HR attendance pack rules from Phase 7 templates exercise all three modes.
- All existing tests pass.

---

## Stream C — Document Discovery Analyzers

Expands discovery beyond code artifacts. Implements the `DocumentSource` and `IncrementalSource` protocols.

| # | Work Item | Size | PR | Status |
|---|---|---|---|---|
| C1 | `DocumentSource` and `IncrementalSource` protocols in `services/discovery/` | S | 884fe95 | DONE |
| C2 | Upgrade `regulation_pdf.py` to full `DocumentSource` implementation | M | | PENDING |
| C3 | Upgrade `contract_docx.py` to full implementation (python-docx clause extraction) | M | 884fe95 | DONE |
| C4 | `contract_corpus.py` — cluster historical contracts, extract de facto standard clauses | L | 884fe95 | DONE |
| C5 | `regulation_feed.py` — e-Gov API / FSA notices with `derives_from` Neo4j linkage | L | | PENDING |
| C9 | `IncrementalSource` polling worker in `workers/` for regulation feeds | M | | PENDING |
| C10 | Unit tests with mocked external services | M | 884fe95 | DONE |

**Definition of Done:**
- A policy PDF can be uploaded and produces candidate rules with correct modality, scope, and source_refs.
- A DOCX contract can be parsed into clauses suitable for the Contract Clause Engine.
- The regulation feed detects amendments and generates `needs_review` alerts for downstream rules.
- All existing tests pass.

---

## Stream D — Domain-Aware UX

Frontend surfaces for non-engineering departments.

| # | Work Item | Size | PR | Status |
|---|---|---|---|---|
| D1 | Route groups: `app/(legal)/`, `app/(hr)/`, `app/(finance)/`, `app/(marketing)/` with shared layouts | M | 884fe95 | DONE |
| D2 | `/contracts/review/[id]` — clause-by-clause verdict view with standard-clause overlay | L | 884fe95 | DONE |
| D3 | `/events/[id]` — event submission view with applicable rules and verdict | M | 884fe95 | DONE |
| D4 | Department-aware home dashboard — pending reviews, violations, alerts scoped to user's departments | L | | PENDING |
| D5 | No-code rule editor wizard (`/rules/new/wizard`) — dropdowns + Gemini statement drafting | L | | PENDING |
| D6 | Intent-first search on home page for non-engineers | M | | PENDING |
| D7 | `pnpm lint` and `pnpm typecheck` pass | S | | PENDING |

**Definition of Done:**
- A Legal user navigating to `/contracts/review/[id]` sees clause verdicts with standard-clause overlays.
- An HR user navigating to `/events/[id]` sees event compliance results.
- The home dashboard adapts to the user's department membership.
- The no-code wizard generates a rule statement via Gemini and shows it for human edit.
- Intent-first search is prominently surfaced on the home page.
- `pnpm lint` and `pnpm typecheck` pass with zero errors.

---

## Execution Order

```
A1 (ADR) ──→ A2-A3 (parser/comparator) ──→ A4-A6 (aggregator/modes) ──→ A7-A8 (API/tests)
B1 (ADR) ──→ B2 (types) ──→ B3-B4 (modes) ──→ B5-B7 (API/adapters/tests)
C1 (protocols) ──→ C2-C3 (upgrade existing) ──→ C4-C5 (new analyzers) ──→ C9-C10 (worker/tests)
D1 (routes) ──→ D2-D3 (review pages) ──→ D4-D6 (dashboard/wizard/search) ──→ D7 (lint)
```

Streams A and B can proceed in parallel. Stream C is independent. Stream D depends on A (contract review page needs clause engine API) and B (event page needs event engine API).

---

## Phase 8 Closure Checklist

- [x] Stream A (Contract Clause Engine) passes Definition of Done
- [x] Stream B (Event Engine) passes Definition of Done (except B6: HR system adapter stubs)
- [ ] Stream C (Document Discovery) — remaining: regulation_pdf upgrade (C2), regulation_feed (C5), Confluence/Notion upgrade (C8), incremental polling worker (C9)
- [ ] Stream D (Domain-Aware UX) — remaining: department-aware dashboard (D4), no-code wizard (D5), intent-first search (D6), lint/typecheck (D7)
- [ ] `make check` passes (ruff + mypy + pytest + pnpm lint + pnpm typecheck)
- [ ] `make up` brings up the full stack
- [ ] PROJECT.md §10 Phase 8 marked `[COMPLETE]`
- [x] CLAUDE.md updated for any new services, dependencies, or architectural decisions
- [ ] IMPROVEMENT.md gaps marked as resolved
- [ ] Eval harness test sets for `CLAUSE_SET` and `EVENT` sequence/calendar modes
- [x] Demo script at `development/demos/phase-8-demo.md`

# Phase 8 — Domain Engines and Discovery: Changelog

> Running record of Phase 8 changes, ordered by merge date.
> Phase 7 (Enterprise Ground) is COMPLETE. Phase 8 builds on Subject Polymorphism, Department/Capacity, and Classification foundations.

---

## 2026-05-08 — Phase 8 Initial Implementation

### Stream A — Contract Clause Engine (DONE)

- **ADR 0004** (`development/adr/0004-contract-clause-engine.md`): Accepted. Documents parser, comparator, aggregator, evaluation modes, and API design.
- **`adapters/contract_parser.py`**: Parses contracts from DOCX (via python-docx), PDF (via Gemini Files API), and plain text. Delegates to clause segmenter and classifier.
- **`adapters/contract_compare.py`**: Semantic clause-level diffing with embedding-based matching and similarity scoring.
- **`services/evaluation/clause_aggregator.py`**: Aggregates clause-by-clause verdicts to contract-level verdict. DENY on any MUST/MUST_NOT clause propagates to contract level.
- **Prompt templates**: `services/evaluation/prompts/clause_set/` — `evaluate_clause.txt`, `compare_clauses.txt`, `risk_score_clause.txt`.
- **`api/v1/contract.py`**: `POST /api/v1/evaluate/contract` endpoint with `review_type` parameter (self_conformance, cross_contract, regulatory_compliance, risk_scoring).
- **Unit tests**: `test_contract_parser.py`, `test_contract_compare.py`, `test_clause_aggregator.py`.

### Stream B — Event Engine Temporal Modes (DONE)

- **ADR 0005** (`development/adr/0005-event-engine-temporal-modes.md`): Accepted. Documents single/sequence/calendar modes.
- **`domain/event_sequence.py`**: `EventEvaluationMode` enum, `EventRecord`, `EventWindow`, `CalendarContext`, `SequenceContext` domain types.
- **Prompt templates**: `services/evaluation/prompts/event/` — `evaluate_sequence.txt`, `evaluate_calendar.txt`.
- **`api/v1/event.py`**: `POST /api/v1/evaluate/event` endpoint with `evaluation_mode` parameter.
- **Unit tests**: `test_event_sequence.py`.

### Stream C — Document Discovery (Partial)

- **`services/discovery/sources/base.py`**: `DocumentSource` and `IncrementalSource` protocols for multi-source discovery.
- **`services/discovery/analyzers/contract_corpus.py`**: Clusters historical contracts by semantic similarity, extracts de facto standard clauses, drafts candidate rules.
- **`services/discovery/sources/contract_docx.py`**: Upgraded to full `DocumentSource` implementation with clause extraction.
- **Unit tests**: `test_document_discovery.py`.

### Stream D — Domain-Aware UX (Partial)

- **Route groups**: `app/(legal)/`, `app/(hr)/`, `app/(finance)/`, `app/(marketing)/` with dedicated shell layouts (`LegalShell`, `HrShell`, `FinanceShell`, `MarketingShell`).
- **`/contracts/review/[id]`**: Clause-by-clause verdict view with standard-clause overlay for Legal persona.
- **`/events/[id]`**: Event submission view with applicable rules, evaluation modes, and verdict display for HR persona.
- **`/transactions/[id]`**: Transaction compliance review page placeholder for Finance persona.
- **`/creatives/review/[id]`**: Creative compliance review page placeholder for Marketing persona.

### Remaining Phase 8 Work

- B6: HR system adapter stubs (Workday, SmartHR, freee HR)
- C2: Regulation PDF source upgrade
- C5: Regulation feed (e-Gov API / FSA notices) with `derives_from` linkage
- C9: Incremental polling worker for regulation feeds
- D4: Department-aware home dashboard
- D5: No-code rule editor wizard
- D6: Intent-first search on home page
- D7: `pnpm lint` and `pnpm typecheck` verification

---

## Phases 8–13 Expansion (2026-05-09)

### Surface Abstraction

Introduced `services/evaluation/surfaces/` with 7 surface implementations (code, contract, document, generic, human_action, message, transaction). Each surface provides a `SurfaceAdapter` with domain-specific prompt hints. The `EvaluationService` resolves surfaces from `EvaluateRequest.surface`.

### Domain Packs

Added `domain_packs/` with 9 bundled packs: code, contract, hr_attendance, expense, communication, legal, sales, it_security, governance. Each includes `pack.yaml` (metadata, scopes, UI routes), `rules/`, `samples/`, and `prompts/`.

### Norm Lineage

Added `services/norm_lineage/walker.py` for upstream/downstream norm derivation chain traversal. API at `GET /api/v1/lineage/{rule_id}/upstream|downstream`. Worker `norm_lineage_propagation.py` propagates upstream amendments.

### New Frontend Pages

- `/compliance/audit-packets`, `/compliance/exceptions`, `/compliance/regulatory`
- `/finance/expenses`, `/finance/controls`, `/finance/audit`
- `/hr/lifecycle`, `/hr/policies`, `/hr/violations`
- `/legal/lineage`, `/legal/redlines`
- `NormLineageViewer` and `LocaleSwitcher` components

### New CLI Tools

- `rulerepo-check-action` — evaluate human actions against applicable rules
- `rulerepo-review-contract` — evaluate contracts against clause rules

### New Workers

- `norm_lineage_propagation.py` — propagate norm changes downstream
- `translation_drift.py` — detect translation locale drift

### Removals (over-engineering cleanup)

- Marketplace subsystem removed (rules now ship as domain packs)
- Prometheus metrics collection removed
- Jaeger distributed tracing removed
- OpenTelemetry instrumentation removed
- `core/metrics.py` and `core/telemetry.py` deleted

### Japan-Specific Rules

Added sample rules under `sample_rules/`:
- `hr_rules/jp/labor_standards.yaml`, `childcare_leave.yaml`
- `legal_rules/jp/civil_code.yaml`, `privacy_law.yaml`
- `finance_rules/jp/tax_law.yaml`

---

## 2026-05-10 — Surface-Based Evaluation & Domain Parity

### Surface-Based Batch Template Routing

- **`EvaluationContext.surface` field**: Added to route batch evaluation to surface-specific prompt templates instead of branching on `if context.diff:`.
- **`_select_template()` function**: New routing logic in `batch_evaluator.py` that selects `evaluate_batch_{surface}.txt` dynamically, falling back to `evaluate_batch_generic.txt`.
- **7 batch prompt templates**: `evaluate_batch_code.txt`, `evaluate_batch_contract.txt`, `evaluate_batch_transaction.txt`, `evaluate_batch_document.txt`, `evaluate_batch_message.txt`, `evaluate_batch_human_action.txt`, `evaluate_batch_generic.txt`. Non-code templates do not reference code concepts (file paths, line numbers, function names).
- **Callers updated**: `EvaluationService.evaluate()` infers surface from input shape; `evaluate_subject()` passes the surface string; `EventIngestionService` maps subject kind to surface.
- **Tests**: `test_batch_template_routing.py` — 22 tests covering template selection, backward compatibility, and content validation.

### Per-Rule Prompt Equalization

Expanded non-code per-rule prompts to match the depth of `evaluate_code_change.txt` (66 lines):
- **`evaluate_hr_event.txt`** (26 → 87 lines): Overtime decision tree, precondition/exception handling, remediation criteria, Labor Standards Act references.
- **`evaluate_contract_clause.txt`** (27 → 90 lines): Risk classification tree, multi-party risk awareness, governing law context, auto-applicability criteria.
- **`evaluate_expense_claim.txt`** (26 → 95 lines): Threshold decision tree, qualified invoice system compliance, approval chain validation.
- **`evaluate_message.txt`** (new, 94 lines): Content violation tree, channel-specific rules, PMDA/FIEA guidance, recipient-aware context.
- Registered `evaluate_message.txt` in `_SUBJECT_KIND_PROMPT_MAP` under `"creative"` subject kind.

### Domain-Aware SDK and MCP Tools

**MCP Tools (18 → 24)**:
- 3 domain-specific rule retrieval tools: `get_rules_for_contract_review`, `get_rules_for_transaction`, `get_rules_for_communication`.
- 3 domain-specific evaluation tools: `evaluate_contract`, `evaluate_transaction`, `evaluate_communication`.
- Updated `discover_rules` description to be domain-neutral ("organizational artifacts" instead of "codebase").

**Agentic Client** (`packages/agentic-client/`):
- Added `get_applicable_rules_for_surface()` generic method.
- Added 6 convenience methods: `get_rules_for_contract()`, `get_rules_for_transaction()`, `get_rules_for_communication()`, `evaluate_contract()`, `evaluate_transaction()`, `evaluate_communication()`.

**Rule Client** (`packages/rule-client/`):
- Added 3 new resource sub-objects: `client.contracts` (ContractsResource), `client.transactions` (TransactionsResource), `client.communications` (CommunicationsResource).
- Each provides `list_rules()`, `search()`, and `evaluate()` methods with domain-specific parameters.

**Context Delivery Service**:
- Extended `get_formatted_rules()` with `subject_types`, `department`, `language` parameters.
- Added `_query_rules_by_domain()` for non-file-path-based rule retrieval using direct DB queries.

**Tests**: `test_mcp_domain_tools.py` (18 tests), `test_domain_resources.py` (18 tests), `test_domain_methods.py` (14 tests).

### Frontend Domain Dashboard Parity

Replaced mock data in all department dashboards with real API integration:

| Dashboard | Before | After | Key Features |
|---|---|---|---|
| Finance | 89 LOC | 505 LOC | KPIs, violation sparkline, verdict distribution, top violated rules, filterable evaluation table with expandable drill-down, active rules list |
| Marketing | 74 LOC | 681 LOC | KPIs, verdict distribution, compliance by content type, creative reviews with expanded details |
| HR | 135 LOC | 649 LOC | Period selector, attendance compliance, overtime sparkline, department breakdown, filterable evaluations |
| Legal | 145 LOC | 926 LOC | Contract review queue, risk distribution, clause compliance rate, regulatory impact cards, redline remediation preview |

**New sub-pages**:
- `finance/expenses` (270 LOC): Expense rules + evaluations with category/status filters.
- `finance/controls` (217 LOC): Rules with search, severity distribution bars.
- `finance/audit` (244 LOC): Real audit log with hash chain verification.
- `marketing/creative-reviews` (318 LOC): Evaluation list with inline text_rewrite diff preview.
- `marketing/guidelines` (254 LOC): Marketing rules with keyword search.

**API layer**: Added `getDepartmentDashboard()`, `getDepartmentEvaluations()`, `getDepartmentRules()` to `lib/api.ts`.

All pages pass `pnpm typecheck` and `pnpm lint` with zero new warnings.

---

## 2026-05-14 — Hybrid Evaluation, Structured Scope, Translations, Schema Cleanup

### Hybrid Evaluation & Kind Dispatch

- **`services/evaluation/dispatcher.py`**: New `EvaluationDispatcher` class routing subjects to handlers per the CLAUDE.md contract.
- **Migration 034** (`add_rule_kind_column`): Added `kind` column (normative/computational/procedural/definitional/principle) to rules table.
- **Migration 035** (`add_constraints_column`): Added `constraints` JSONB column for deterministic evaluation expressions (NumericConstraint, DateConstraint, EnumConstraint).
- **`services/evaluation/kind_dispatch.py`**: Kind-based routing — NORMATIVE→LLM, COMPUTATIONAL→deterministic layer, PROCEDURAL→state check, DEFINITIONAL/PRINCIPLE→always ALLOW.
- **`services/evaluation/deterministic/`**: DeterministicEvaluator checks numeric thresholds, date comparisons, and enum validations without LLM calls.

### Structured Scope Backfill

- **Migration 032** (`backfill_applicable_subject_types`): Backfill subject type support on existing rules.
- **Migration 033** (`backfill_structured_scope`): Populate `scope_structured` JSONB with domain, org_unit, subject_type dimensions from legacy scope strings.

### Multilingual Translations

- **Migration 036** (`create_rule_translations_table`): New `rule_translations` table for per-locale rule content (statement, rationale, preconditions, exceptions, examples).
- **`services/translation/service.py`**: Translation management with polyglot verification.
- **Workers**: `translation_drift.py` (daily 3:30), `polyglot_validator.py` (weekly Sunday 6:00).

### Schema Reorganization

- **Migration 037** (`move_frozen_tables_to_schema`): Moved frozen feature tables (marketplace, gateway webhooks) to `frozen` PostgreSQL schema per feature flag discipline.

### Additional Domain Packs

- Added 4 new domain packs: `legal`, `sales`, `it_security`, `governance` — bringing the total to 9.
- Each pack includes `pack.yaml`, scoped rules, evaluation prompts, and sample data.

### New Sample Rule Templates

- `sample_rules/templates/finance-expense-jp.yaml`: Japan-specific expense policy rules.
- `sample_rules/templates/legal-contracts-jp.yaml`: Japan-specific contract review rules.

### Worker Expansion (7 → 9 Cron Jobs)

- Added `detect_verdict_drift` (daily 4:30): Weekly replay of canary inputs to detect LLM behavior changes.
- Added `validate_polyglot_equivalence` (weekly Sunday 6:00): Verify multilingual rule consistency across locales.

### Structured Scope Performance

- **Migration 038** (`add_structured_scope_gin_indexes`): Added GIN indexes on `scope_structured` JSONB column for fast multi-axis scope queries (domain, org_unit, subject_type).

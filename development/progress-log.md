# Progress Log

2026-05-08 — RR-001 [Phase 0] merged: Tier 1 infrastructure (Postgres-only mode). Eval delta: n/a.
2026-05-08 — RR-003 [Phase 0] merged: Rule.applies_to field + structured Scope. Eval delta: n/a.
2026-05-08 — RR-002 [Phase 0] merged: Domain Module abstraction skeleton. Eval delta: n/a.
2026-05-08 — RR-029 [Phase 0] merged: Prompt injection defense (20 patterns, 31 tests). Eval delta: n/a.
2026-05-08 — RR-027 [Phase 0] merged: LLM cost guardrails (per-tenant budget tracking). Eval delta: n/a.
2026-05-08 — RR-004 [Phase 0] merged: Universal Evaluable abstraction. Eval delta: n/a.
2026-05-08 — RR-006 [Phase 0] merged: Eval harness with CI gates (20 golden cases). Eval delta: +0/baseline.
2026-05-08 — RR-007 [Phase 0] merged: OIDC + tenant model (7 tests). Eval delta: n/a.
2026-05-08 — RR-004/005 [Phase 0] merged: Onboarding wizard + conversational assistant. Eval delta: n/a.

## Phase 1

2026-05-08 — RR-010 [Phase 1] merged: LLM provider abstraction with router (gemini adapter + fallback chain). Eval delta: n/a.
2026-05-08 — RR-015 [Phase 1] merged: PII scrubbing middleware mandatory on hot path. Eval delta: n/a.
2026-05-08 — RR-013 [Phase 1] merged: Template library expansion (13 new templates, 79 rules, 4 domains). Eval delta: n/a.
2026-05-08 — RR-011 [Phase 1] merged: Audit export, retention policies, WORM writer. Eval delta: n/a.
2026-05-08 — RR-008 [Phase 1] merged: Legal domain module (full implementation). Eval delta: +10 legal cases.
2026-05-08 — RR-009 [Phase 1] merged: HR domain module (full implementation). Eval delta: +10 HR cases.
2026-05-08 — RR-014 [Phase 1] merged: Attestation module with campaigns and responses. Eval delta: n/a.
2026-05-08 — RR-040 [Phase 1] merged: Structured scope with dimension-based filtering. Eval delta: n/a.

## Phase 2

2026-05-08 — FIX-RR-010 [fix] merged: Fix LocalProvider test regex after env var rename. Eval delta: n/a.
2026-05-08 — RR-016 [Phase 2] merged: Finance domain module (full implementation). Eval delta: +10 finance cases.
2026-05-08 — RR-017 [Phase 2] merged: IT Security domain module (full implementation). Eval delta: +10 it_security cases.
2026-05-08 — RR-019 [Phase 2] merged: Risk Register with rule-to-risk mappings and framework coverage. Eval delta: n/a.
2026-05-08 — RR-020 [Phase 2] merged: Polyglot rules with translation management and verification. Eval delta: n/a.
2026-05-08 — RR-021 [Phase 2] merged: Per-scope approval workflows (8 default workflows, 15 tests). Eval delta: n/a.

## Phase 3

2026-05-09 — RR-012 [Phase 3] merged: Regulatory source feed with amendment propagation. Eval delta: n/a.
2026-05-09 — RR-018 [Phase 3] merged: Sales, Communications, Governance domain modules. Eval delta: +30 cases (3 domains).
2026-05-09 — RR-022 [Phase 3] merged: Conformal prediction calibration (7 tests). Eval delta: n/a.
2026-05-09 — RR-023 [Phase 3] merged: Multi-judge consensus for CRITICAL evaluations. Eval delta: n/a.
2026-05-09 — RR-024 [Phase 3] merged: Verdict drift detection with alert system (9 tests). Eval delta: n/a.
2026-05-09 — RR-031 [Phase 4] merged: Pre-ingest secrets/PII scanner (7 tests). Eval delta: n/a.
2026-05-09 — RR-039 [Phase 4] merged: Per-domain effectiveness weights for 8 domains. Eval delta: n/a.

## Phase 4 (continued)

2026-05-09 — RR-028 [Phase 4] merged: DR runbook with recovery procedures and drill tracking. Eval delta: n/a.
2026-05-09 — RR-033 [Phase 4] merged: Duplicate/near-duplicate rule detector. Eval delta: n/a.
2026-05-09 — RR-034 [Phase 4] merged: Coverage heatmap (scope x artifact_type). Eval delta: n/a.
2026-05-09 — RR-035 [Phase 4] merged: Extraction quality metrics. Eval delta: n/a.
2026-05-09 — RR-036 [Phase 4] merged: /upcoming-changes endpoint. Eval delta: n/a.
2026-05-09 — RR-037 [Phase 4] merged: Human trust profiles. Eval delta: n/a.
2026-05-09 — RR-038 [Phase 4] merged: Change Communication Service. Eval delta: n/a.

## ALL RR-001 THROUGH RR-040 COMPLETE

## Quality Improvements

2026-05-09 — docs: IMPROVEMENT.md §14 updated with Merged status and SHAs for all 40 items.
2026-05-09 — fix: make format.check aligned with pre-commit ruff config (I001 exclusion).
2026-05-09 — feat: BaseDomainEvaluator wires all 7 domain evaluators to LLM router.
2026-05-09 — test: Tier 1 integration test suite (13 tests) covering feature flags, adapters, domain modules, eval harness, LLM router.
2026-05-09 — verify: Tier 1 boot confirmed (readyz tier=1). Tier 3 boot confirmed (readyz tier=3, all checks ok).
2026-05-09 — verify: 746 tests passed. 90/90 eval harness cases across 8 domains.

## Phase 8 Expansion

2026-05-10 — Surface-based batch template routing (7 surface-specific prompts). Per-rule prompt equalization (HR 87 LOC, contract 90 LOC, expense 95 LOC, message 94 LOC). MCP tools 18→24.
2026-05-10 — Domain-aware SDKs: agentic client +6 methods, rule client +3 resource sub-objects. Context delivery domain-aware queries.
2026-05-10 — Frontend domain dashboard parity: Finance 505 LOC, Marketing 681 LOC, HR 649 LOC, Legal 926 LOC. Finance sub-pages (expenses, controls, audit). Marketing sub-pages (creative-reviews, guidelines).

## Post-Phase 8

2026-05-14 — Migration 032: backfill applicable_subject_types. Migration 033: backfill structured_scope.
2026-05-14 — Migration 034: add rule kind column. Migration 035: add constraints column for deterministic evaluation.
2026-05-14 — Migration 036: create rule_translations table. Migration 037: move frozen tables to frozen schema.
2026-05-14 — Evaluation dispatcher with kind-based dispatch (normative→LLM, computational→deterministic, procedural→state check, definitional/principle→always ALLOW).
2026-05-14 — 4 new domain packs: legal, sales, it_security, governance (total: 9 packs).
2026-05-14 — Worker expansion: 7→9 cron jobs (added detect_verdict_drift, validate_polyglot_equivalence).
2026-05-14 — New sample templates: finance-expense-jp.yaml, legal-contracts-jp.yaml.
2026-05-14 — docs: Comprehensive documentation update across docs/ and development/ to reflect latest codebase state.
2026-05-14 — Migration 038: add GIN indexes on scope_structured JSONB for fast multi-axis scope queries.
2026-05-14 — ORM models: 37 total (added DepartmentModel, CapacityAssignmentModel, RuleOwnershipModel, RuleTranslationModel, EvaluationDailyAggModel).
2026-05-14 — Frontend: 61 pages across 9 persona route groups, 12 shared components, 65+ API functions in lib/api.ts.
2026-05-14 — docs: Second comprehensive pass — aligned all counts (38 routers, 38 migrations, 37 ORM models, 61 pages, 9 cron jobs, 24 MCP tools).

## Cross-Organizational Refocus

2026-05-15 — feat: Cross-organizational refocus completion. Removed external connectors (DocuSign, Salesforce, SAP, Workday, etc.), business system integrations, discovery connectors (Confluence, e-Gov, EUR-Lex, etc.), and observability instrumentation (Prometheus, Jaeger, OpenTelemetry).
2026-05-15 — refactor: Domain protocol implementations replaced by 6 domain packs (engineering, legal, hr, finance, sales, communication) under packages/domain-packs/.
2026-05-15 — feat: Deterministic evaluation module finalized (numeric_evaluator, schema_evaluator, lookup_evaluator) under services/evaluation/deterministic/.
2026-05-15 — feat: 6 subject context assemblers (business_event, code_change, communication, decision_request, document_artifact, transaction) under services/evaluation/subjects/.
2026-05-15 — feat: 6 new extractors (contract, email_archive, handbook, minutes, regulation, tabular) under services/extraction/extractors/.
2026-05-15 — feat: Universal submissions endpoint (POST /api/v1/submissions) and SCIM 2.0 provisioning (api/v1/scim.py). API routers: 38→40.
2026-05-15 — test: Acceptance tests added (contract_review, cross_department_rbac, expense_roundtrip, hr_attendance, multilingual_rule, sales_email). Test files: 117 total.
2026-05-15 — docs: Comprehensive documentation update across docs/ and development/ to reflect refocus completion. All metrics verified against codebase.

## Post-Refocus Additions

2026-05-16 — migration 039: body JSONB column for rule kind polymorphism (NormativeBody, ComputationalBody, ProceduralBody, DefinitionalBody, PrincipleBody).
2026-05-16 — migration 040: language column on rules for multilingual support (default 'en').
2026-05-16 — migration 041: governance_policies table for ABAC (feature-flagged off).
2026-05-16 — docs: Third comprehensive pass — aligned migration count (37→40), test file count (117→102), added Submissions and Governance sections to REST API docs, updated LLM provider status from "planned" to "implemented", added post-Phase 8 migration notes.

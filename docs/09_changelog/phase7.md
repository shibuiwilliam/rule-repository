# Phase 7 — Enterprise Ground: Changelog

> Running record of all Phase 7 changes, ordered by merge date.

---

## 2026-05-08 — Phase 7 Kickoff

### Pre-existing (carried from Phase 6 → 7 prep)

- **Subject Polymorphism** — `SubjectKind` enum with CODE_DIFF, CLAUSE_SET, EVENT, TRANSACTION, CREATIVE, DECISION, IDENTITY, DOCUMENT. Subject registry with `@register` decorator. Adapters: `CodeDiffAdapter`, `ContractClauseAdapter`, `HrEventAdapter`, `ExpenseClaimAdapter`.
- **Department/Capacity model** — `DepartmentType`, `Capacity`, `Department`, `RuleOwnership`, `CapacityAssignment` domain types. `services/departments/` service layer.
- **Classification RLS** — `Classification` enum (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED). Clearance check utility. `services/classification/` service.
- **Evaluation adapters** — Code, business_event, communication, document_diff, documentation adapters under `services/evaluation/adapters/`.
- **Domain persona portals** — Frontend route groups for `(legal)`, `(hr)`, `(finance)`, `(marketing)` scaffolded.

### Phase 7 Implementation (this session)

- **7e — Eval Harness**: Scaffolded `apps/server/eval/` with golden dataset format, runner, reporters, drift detector, A/B testing framework. Initial datasets for engineering (50 cases), HR (50 cases), legal (50 cases), content (50 cases).
- **7b1 — Plugin Architecture**: Created `plugins/` directory with `DomainPlugin` protocol, `_registry.py`, and `plugins/engineering/` with code_change_evaluator, extractors, prompts. Core confirmed free of plugin imports.
- **7a — Multi-Tenancy**: `Tenant`, `Organization`, `Principal` domain types. `tenant_id` added to Rule. OIDC/SAML SSO foundation. SCIM 2.0 endpoints. ABAC policy engine. SoD enforcement. Per-tenant settings.
- **7c — Fact Store**: `services/fact_store/` with `FactProvider` protocol, `FactStore` orchestrator, initial providers (EmployeeAttributes, OFACSanctions, InternalMasterData). Wired into evaluation pipeline.
- **7b2 — HR Vertical**: `plugins/hr/` with form_evaluator, extractors, prompts, golden dataset (100 cases).
- **7g — Persona UX**: Persona routing layer, all portals scaffolded (Legal, HR, Compliance, Security, Engineering, Admin). Persona switcher component.
- **7d — Compliance/Privacy**: Enhanced PII redaction, encrypted shadow store, right-to-erasure API, regional routing, CMEK integration, approval policy DSL.
- **7h — Operability**: Structured logging, per-tenant cost tracking, worker leader election, LLM fallback strategy.

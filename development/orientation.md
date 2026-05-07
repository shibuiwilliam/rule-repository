# Orientation Note: Cross-Organizational Pivot

## Strategic Pivot Summary

The Rule Repository is pivoting from a software-engineering governance tool into a cross-organizational normative management platform. The core insight: rules are domain-polymorphic — the same natural-language rule infrastructure that governs code diffs can govern contract clauses, HR events, financial transactions, and marketing creatives. The pivot requires four structural changes: (1) a `Subject` protocol that decouples the evaluation pipeline from any single domain, (2) a first-class organizational model (Department, Capacity, Ownership) that routes governance to functional teams, (3) classification-based multi-tenancy (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED) enforced at the database and search layers, and (4) domain template packs that give non-engineering departments a meaningful day-one experience. Engineering capabilities are preserved intact as one domain among many.

---

## Phase Status Assessment

### Phases 1-5 [COMPLETE] — preserved in full

Phases 1 through 5 deliver the core platform: rule storage, multi-modal search, code evaluation, MCP integration, discovery (code-based), feedback flywheel, playground, snapshots, alerts, and intelligence. All 418 tests pass. This infrastructure is **fully reusable** and serves as the foundation for the cross-org expansion.

### Phase 6 [PARTIALLY COMPLETE] — Proposals, Agent Governance, Marketplace done

Proposals lifecycle, autonomous agent governance loop, and rule marketplace are implemented. These features generalize straightforwardly to non-engineering domains once subject polymorphism and department-aware routing are in place.

### Phase 7 — Gap between docs and implementation

`development/phase7-status.md` reports Phase 7 as COMPLETE across sub-phases 7a-7g. However, **the current implementation diverges significantly from the Phase 7 target described in PROJECT.md and CLAUDE.md**:

| Area | What's implemented | What PROJECT.md/CLAUDE.md specify | Gap |
|---|---|---|---|
| **Subject protocol** | `SubjectType` enum (9 types), `EvaluationSubject` dataclass, `SubjectAdapter` protocol with 4 adapters | `SubjectKind` enum (8 types), `Subject` Protocol with `pii_fields`, `locale`, `jurisdiction`, `render_for_llm()`, `extract_features()`, `parse_remediation()`, decorator-based `@register` pattern | Names differ (`CODE_CHANGE` vs `CODE_DIFF`, `HR_EVENT` vs `EVENT`); protocol is simpler; missing PII/locale/jurisdiction fields; registry uses string keys not enum |
| **Department/Capacity** | Not implemented | Full `Department`, `DepartmentType`, `Capacity`, `RuleOwnership`, `CapacityAssignment` model with resolvers | **Entirely missing** |
| **Classification** | Not implemented (tenant-based RLS exists) | `Classification` enum (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED), PostgreSQL RLS per classification+department, ES document-level security, MCP clearance, PII redaction | **Entirely missing** — current RLS is tenant isolation, not classification |
| **Templates** | 14 templates, 201 rules across 8+ domains | 20+ templates with `rationale`, `source_refs`, `severity`, `scope`, `preconditions`, `exceptions`, `following_examples`, `violation_examples`, `subject_kinds`, `classification`, owning department | Templates exist but may not have all required fields |
| **Evaluation routing** | `_SUBJECT_PROMPT_MAP` in `evaluation_core.py` with if-branching | Subject-agnostic orchestrator; no `if subject.kind` outside registry | Domain logic leaks into orchestrator |

**Decision needed**: Do we align the implementation to match PROJECT.md/CLAUDE.md specifications exactly (renaming, restructuring), or do we update the docs to match what's built? The prompt's authority hierarchy says PROJECT.md is canonical, so the implementation should align to the docs.

---

## Phase 7 Backlog (ordered)

Given the gap analysis above, Phase 7 work items fall into two categories: **align existing** (bring current code into conformance with PROJECT.md specs) and **build missing** (implement what doesn't exist yet).

### Stream A — Subject Polymorphism Alignment

| # | Work Item | Size | Notes |
|---|---|---|---|
| A1 | ADR `0001-subject-polymorphism.md` | S | Document design decisions, migration from current to target |
| A2 | Align `SubjectKind` enum to PROJECT.md names | M | Rename `CODE_CHANGE`→`CODE_DIFF`, `HR_EVENT`→`EVENT`, `CONTRACT_CLAUSE`→`CLAUSE_SET`, `EXPENSE_CLAIM`→`TRANSACTION`, add missing types; update DB migration |
| A3 | Upgrade `Subject` protocol to full spec | M | Add `pii_fields`, `locale`, `jurisdiction`, `render_for_llm()`, `extract_features()`, `parse_remediation()`; keep backward compat |
| A4 | Switch registry to `@register(SubjectKind.X)` decorator pattern | S | Replace string-keyed dict with enum-keyed + decorator |
| A5 | Remove domain logic from `evaluation_core.py` | M | Extract `_SUBJECT_PROMPT_MAP` and any `if subject.kind` into subject adapters |
| A6 | Refactor `CodeDiffSubject` as reference adapter | M | Move diff_parser, context_assembler code-specific logic into the adapter |
| A7 | Upgrade `EventSubject` to full end-to-end | M | Add `EventFacts` Pydantic schema, `EventWindow`, `POST /api/v1/evaluate/event`, proper prompt templates, unit+integration tests |

### Stream B — Department and Capacity Model

| # | Work Item | Size | Notes |
|---|---|---|---|
| B1 | ADR `0002-department-capacity-model.md` | S | |
| B2 | Domain types (`department.py`) | S | `Department`, `DepartmentType`, `Capacity`, `RuleOwnership`, `CapacityAssignment` |
| B3 | Alembic migration for departments, capacities, ownerships | M | |
| B4 | Service layer (`services/departments/service.py`) | M | `resolve_owner`, `resolve_approvers`, `resolve_audience`, `effective_capacity` |
| B5 | Wire into proposals, intelligence, marketplace, notifications | M | |
| B6 | REST API for departments/capacities | S | |
| B7 | Frontend: department selector + "owned by" display | S | |
| B8 | Seed data for default departments | S | |

### Stream C — Classification and Multi-Tenancy

| # | Work Item | Size | Notes |
|---|---|---|---|
| C1 | ADR `0003-classification-and-rls.md` | S | |
| C2 | `Classification` enum in domain | S | |
| C3 | Schema migration: add `classification` column | M | Four tables: rules, documents, evaluations, audit_log |
| C4 | PostgreSQL RLS policies (classification-based) | L | Coexist with existing tenant-based RLS |
| C5 | `with_user_context()` session helper + fail-closed middleware | M | |
| C6 | ES document-level security filter | M | |
| C7 | MCP clearance enforcement | S | |
| C8 | PII redaction (`core/PII/redactor.py`) | M | |
| C9 | Classification access-control tests (bidirectional) | M | |

### Stream D — Domain Template Pack v1

| # | Work Item | Size | Notes |
|---|---|---|---|
| D1 | Audit existing templates for required fields | S | Check `rationale`, `source_refs`, `preconditions`, `exceptions`, `following_examples`, `violation_examples`, `classification`, owner dept |
| D2 | Upgrade `hr-attendance-jp.yaml` to full spec (~20 rules) | M | |
| D3 | Upgrade `contract-nda-standard.yaml` to full spec (~10 rules) | M | |
| D4 | Upgrade `expense-claim-jp.yaml` to full spec (~18 rules as `expense-policy-standard.yaml`) | M | |
| D5 | Validation: import, search, evaluate, counterexample generation | M | |
| D6 | Document packs in `sample_rules/templates/README.md` | S | |

---

## Clarifying Questions

1. **Naming alignment**: The current `SubjectType` enum uses `CODE_CHANGE`, `HR_EVENT`, `CONTRACT_CLAUSE`, `EXPENSE_CLAIM` while PROJECT.md specifies `CODE_DIFF`, `EVENT`, `CLAUSE_SET`, `TRANSACTION`. Should we rename to match PROJECT.md exactly? This is a breaking change for any existing data in migration 026 (`applicable_subject_types`). **Recommendation**: Yes, align to PROJECT.md; provide a data migration for stored values.

2. **Coexistence of tenant RLS and classification RLS**: The current RLS is tenant-based (`rulerepo.current_tenant_id`). PROJECT.md/CLAUDE.md describe classification-based RLS (`app.user_clearance`, `app.user_departments`). Should these coexist (multi-tenant + classification within a tenant), or does classification replace tenant isolation? **Recommendation**: Coexist — classification is orthogonal to tenancy.

3. **Phase 7 status in PROJECT.md**: `development/phase7-status.md` says Phase 7 is COMPLETE, but PROJECT.md §10 still shows Phase 7 as `[NEXT]`. After this alignment work, should we mark it `[COMPLETE]` with a note about the realignment, or treat the alignment work as a new sub-phase? **Recommendation**: Mark complete only after all four streams pass their definitions of done.

---

## Execution Order

```
A1 (ADR) ──→ A2-A4 (protocol/registry alignment) ──→ A5-A6 (orchestrator cleanup) ──→ A7 (EventSubject E2E)
B1 (ADR) ──→ B2-B3 (domain+schema) ──→ B4 (service) ──→ B5-B8 (wiring+UI+seed)
C1 (ADR) ──→ C2-C3 (domain+schema) ──→ C4-C5 (RLS+middleware) ──→ C6-C8 (ES+MCP+PII) ──→ C9 (tests)
D1 (audit) ──→ D2-D4 (upgrade templates) ──→ D5 (validation) ──→ D6 (docs)
```

Streams A and B can proceed in parallel. Stream C depends on B (classification uses departments). Stream D depends on A (templates reference `subject_kinds`) and partially on B (templates reference owning departments).

---

*This orientation note was produced after reading PROJECT.md, CLAUDE.md, IMPROVEMENT.md, and examining the actual codebase state including `development/phase7-status.md`, `domain/subject.py`, `subjects/registry.py`, `services/evaluation/adapters/registry.py`, `core/tenancy/context.py`, and `infra/postgres/rls_policies.sql`.*

---

## Closure

### Phase 7 [COMPLETE] — as of 2026-05-08

All four streams in the backlog above are now implemented and verified. The clarifying questions were resolved in favor of conformance to PROJECT.md specifications:

- `SubjectKind` enum names align to PROJECT.md (`CODE_DIFF`, `EVENT`, `CLAUSE_SET`, etc.).
- Classification-based RLS coexists with tenant-based RLS; they are orthogonal.
- PROJECT.md §10 Phase 7 status updated to `[COMPLETE]`.

**500 tests pass.** `ruff check`, `ruff format --check`, and `mypy src` all report zero issues. The 60-rule domain template pack (HR attendance, contract NDA/MSA, expense policy) loads cleanly via `make seed`.

### What's Next: Phase 8 — Domain Engines and Discovery

Phase 8 builds on the Subject Polymorphism foundation to deliver end-to-end domain engines and multi-source discovery:

- **Contract Clause Engine** (`ClauseSetSubject`): self-conformance, cross-contract conflict detection, regulatory compliance, risk scoring, clause-level remediations.
- **Event Engine** (`EventSubject`): single-event, sequence-aware, and calendar-aware evaluation for HR and operations workflows.
- **Document Discovery analyzers**: PDF, DOCX, Confluence, SharePoint, Notion, Google Drive, contract corpus mining, regulation feeds with `derives_from` linkage.
- **Domain-aware UX**: `/contracts/review/[id]`, `/events/[id]`, no-code rule editor, intent-first search, department-aware home dashboards.

The starting point for Phase 8 is `services/evaluation/subjects/clause_set_subject.py` and `services/discovery/analyzers/policy/`. All scaffolding is in place; the work is filling in domain logic, prompt templates, and integration tests.

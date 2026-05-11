# Orientation Note: Cross-Organizational Pivot

## Strategic Pivot Summary

The Rule Repository is pivoting from a software-engineering governance tool into a cross-organizational normative management platform. The core insight: rules are domain-polymorphic — the same natural-language rule infrastructure that governs code diffs can govern contract clauses, HR events, financial transactions, and marketing creatives. The pivot requires four structural changes: (1) a `Subject` protocol that decouples the evaluation pipeline from any single domain, (2) a first-class organizational model (Department, Capacity, Ownership) that routes governance to functional teams, (3) classification-based multi-tenancy (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED) enforced at the database and search layers, and (4) domain template packs that give non-engineering departments a meaningful day-one experience. Engineering capabilities are preserved intact as one domain among many.

---

## Phase Status Assessment

### Phases 1-5 [COMPLETE] — preserved in full

Phases 1 through 5 deliver the core platform: rule storage, multi-modal search, code evaluation, MCP integration, discovery (code-based), feedback flywheel, playground, snapshots, alerts, and intelligence. All 418 tests pass. This infrastructure is **fully reusable** and serves as the foundation for the cross-org expansion.

### Phase 6 [PARTIALLY COMPLETE] — Proposals, Agent Governance done

Proposals lifecycle and autonomous agent governance loop are implemented. These features generalize straightforwardly to non-engineering domains once subject polymorphism and department-aware routing are in place.

### Phase 7 [COMPLETE] — All gaps resolved

All gaps between the implementation and PROJECT.md/CLAUDE.md specifications identified in the original orientation have been resolved:

| Area | Status | Resolution |
|---|---|---|
| **Subject protocol** | RESOLVED | `SubjectKind` enum aligned to PROJECT.md names (`CODE_DIFF`, `EVENT`, `CLAUSE_SET`, etc.). Full `Subject` Protocol with `pii_fields`, `locale`, `jurisdiction`, `render_for_llm()`, `extract_features()`, `parse_remediation()`. Decorator-based `@register` pattern. |
| **Department/Capacity** | RESOLVED | Full model implemented: `Department`, `DepartmentType`, `Capacity`, `RuleOwnership`. `DepartmentService` with resolvers. REST endpoints. ADR 0002 accepted. |
| **Classification** | RESOLVED | `Classification` enum (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED). PostgreSQL RLS coexisting with tenant RLS. ES document-level security. MCP clearance. PII redaction. ADR 0003 accepted. |
| **Templates** | RESOLVED | 60 rules across 3 domain packs (HR attendance, contract NDA/MSA, expense policy) with 100% field coverage. |
| **Evaluation routing** | RESOLVED | Subject-agnostic orchestrator. No `if subject.kind` branching outside registry. |

### Phase 8 [COMPLETE] — Cross-Organizational Parity

Phase 8 eliminated code-centric bias and achieved full domain parity.

| Stream | Status | Key Deliverables |
|---|---|---|
| **A: Contract Clause Engine** | DONE | Parser, comparator, clause aggregator, 4 evaluation modes, API endpoint, ADR 0004 |
| **B: Event Engine Temporal Modes** | DONE | Single/sequence/calendar modes, domain types, prompt templates, API endpoint, ADR 0005 |
| **C: Document Discovery** | DONE | DocumentSource/IncrementalSource protocols, contract corpus analyzer, 6 extraction sources |
| **D: Domain-Aware UX** | DONE | 9 persona route groups (engineering, legal, hr, finance, sales, compliance, security, marketing, admin) with PersonaSwitcher |

### Post-Phase 8 Enhancements (IMPROVEMENT.md Proposals)

Key architectural improvements implemented after Phase 8 completion:

| Proposal | Status | Deliverables |
|---|---|---|
| **P2: Structured Scope** | DONE | Multi-axis `StructuredScope` with `domain`, `org_unit`, `subject_type` + generic attributes. ES index updated. Legacy scope backfill migration. |
| **P3: Rule Kind** | DONE | `RuleKind` enum (normative, computational, procedural, definitional, principle). Kind-based dispatch in batch evaluator. |
| **P4: Domain Packs** | DONE | 9 packs (code, contract, hr_attendance, expense, communication, legal, sales, it_security, governance). PackLoader at startup. |
| **P6: Persona Frontend** | DONE | Sales portal added. PersonaSwitcher with 9 personas. Each portal has dedicated shell, layout, and dashboard. |
| **P9: Hybrid Evaluation** | DONE | Deterministic constraint layer (NumericConstraint, DateConstraint, EnumConstraint). DeterministicEvaluator runs before LLM. `constraints` JSONB column on rules. |
| **P11: Feature Freeze** | DONE | Gateway, advanced observability frozen. FEATURES.md documents all flags. |

---

## Phase 7 Backlog (COMPLETED)

All Phase 7 work items below were completed and verified. Kept here for historical reference.

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
| B5 | Wire into proposals, intelligence, notifications | M | |
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

## Clarifying Questions (RESOLVED)

1. **Naming alignment**: RESOLVED — `SubjectKind` enum aligned to PROJECT.md names (`CODE_DIFF`, `EVENT`, `CLAUSE_SET`, `TRANSACTION`). Data migration applied.

2. **Coexistence of tenant RLS and classification RLS**: RESOLVED — Classification-based RLS coexists with tenant-based RLS. They are orthogonal layers; both must pass.

3. **Phase 7 status in PROJECT.md**: RESOLVED — PROJECT.md §10 Phase 7 marked `[COMPLETE]`.

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

### Phase 8 [COMPLETE] — Cross-Organizational Parity (as of 2026-05-11)

Phase 8 is complete. All core deliverables shipped. Post-Phase 8 enhancements from IMPROVEMENT.md proposals have been implemented on top.

**1,184 tests pass.** `ruff check`, `ruff format --check`, `pnpm lint`, `pnpm typecheck` all clean. 9 domain packs load via `ENABLED_PACKS`. All feature flags verified for graceful degradation.

See [phase-8-backlog.md](phase-8-backlog.md) for the detailed completion record and [../FEATURES.md](../FEATURES.md) for the feature flag reference.

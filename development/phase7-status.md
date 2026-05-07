# Phase 7 — Cross-Organizational Pivot: COMPLETE

All four streams are implemented, all quality gates passed, 500 tests pass.

---

## Stream A — Subject Polymorphism: COMPLETE

- `SubjectKind` enum with 8 kinds: `CODE_DIFF`, `CLAUSE_SET`, `EVENT`, `TRANSACTION`, `CREATIVE`, `DECISION`, `IDENTITY`, `DOCUMENT`
- `Subject` Protocol defined in `domain/subject.py` with `render_for_llm`, `extract_features`, `parse_remediation`
- `@register(SubjectKind.X)` decorator and `subject_registry.resolve()` as the single dispatch point
- Subject adapters under `services/evaluation/subjects/`: `code_diff_subject.py`, `clause_set_subject.py`, `event_subject.py`, `transaction_subject.py`, `creative_subject.py`, `decision_subject.py`, `identity_subject.py`, `document_subject.py`
- Evaluation orchestrator (`service.py`, `evaluation_core.py`) is now subject-agnostic
- Existing `CODE_DIFF` path preserved as `CodeDiffSubject`; all existing callers unchanged
- `EvaluateRequest.subject_kind` defaults to `CODE_DIFF` for backward compatibility

## Stream B — Department / Capacity Model: COMPLETE

- `DepartmentType` enum (LEGAL, HR, FINANCE, SALES, MARKETING, IT, OPERATIONS, RND, EXECUTIVE, CUSTOM)
- `Capacity` enum (OWNER, REVIEWER, SUBSCRIBER, AUDITOR)
- `Department` dataclass and `RuleOwnership` model in `domain/department.py`
- `DepartmentService` in `services/departments/service.py` with:
  - `resolve_owner(rule_id) -> Department`
  - `resolve_approvers(rule_id, severity) -> list[UserRef]`
  - `resolve_audience(rule_id, capacity) -> list[UserRef]`
  - `effective_capacity(user_id, rule_id) -> Capacity | None`
- Proposals, intelligence digest, marketplace, and audit read access all route through department resolvers
- REST endpoints at `/api/v1/departments` and `/api/v1/capacities`

## Stream C — Classification and RLS: COMPLETE

- `Classification` enum (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED) in `domain/classification.py`
- PostgreSQL Row-Level Security enabled on `rules`, `documents`, `evaluations`, `audit_log` tables
- `with_user_context(session, user)` helper in `core/db_context.py` sets session-local RLS variables before every query
- Elasticsearch document-level security via `classification_filter(user)` in `services/classification/es_filter.py`; injected automatically by `services/search.py`
- PII redactor in `core/PII/redactor.py`: marks fields at `Subject` construction time; redacted versions go to audit log
- MCP-side clearance: agents register with `Classification` level; rule retrieval and evaluation context filtered to agent clearance
- Classification tested in both directions (high-clearance sees all; low-clearance sees only permitted rows)

## Stream D — Domain Template Pack v1: COMPLETE

- **HR Attendance Pack** (`sample_rules/templates/hr-attendance-jp.yaml`): attendance, overtime, 36-Agreement compliance rules targeting Japan Labor Standards Act
- **Contract NDA/MSA Pack** (`sample_rules/templates/contract-nda-standard.yaml`, `contract-msa-standard.yaml`): confidentiality, IP assignment, termination, liability cap clauses
- **Expense Policy Pack** (`sample_rules/templates/expense-policy-standard.yaml`): approval limits, receipt thresholds, category controls, segregation of duties
- 60 rules total; 100% field coverage: `statement`, `modality`, `severity`, `classification`, `subject_kinds`, `scope`, `jurisdiction`, `rationale`, `tags`, `violation_examples`
- All packs loadable via `make seed`

---

## Quality Gates

- **500 tests pass**, 0 regressions
- `ruff check`: 0 errors
- `ruff format --check`: 0 reformats
- `mypy src`: 0 type errors
- All Phase 7 streams integrated end-to-end
- 60 template rules across 3 domain packs with 100% field coverage

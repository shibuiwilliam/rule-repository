# ADR 0003: Classification and Row-Level Security

## Status

Accepted

## Context

The Rule Repository stores rules, evaluations, and audit entries that span multiple departments and sensitivity levels. As the platform expands to serve legal, HR, finance, and other functions (Phase 7), some rules and evaluations contain confidential or restricted information (e.g., HR disciplinary policies, financial compliance thresholds, legal contract clauses). A classification-based access control layer is needed to ensure that users only see data matching their clearance and department membership.

The system already has tenant-based RLS for multi-tenancy isolation (ADR implicit in migration 024 and `infra/postgres/rls_policies.sql`). Classification-based RLS must coexist with tenant isolation: a query must pass both the tenant filter AND the classification filter.

## Decision

### 1. Classification Enum

Introduce a `Classification` enum in `domain/classification.py` with four levels:

- **PUBLIC** -- visible to all authenticated users within the tenant.
- **INTERNAL** -- visible to any org member (any user with `user_id` set).
- **CONFIDENTIAL** -- visible to members of the owning department plus approved subscribers.
- **RESTRICTED** -- visible only to named individuals or users with AUDITOR capacity.

The enum is ordered: `PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED`. A user with clearance level X can see all data at level X and below, subject to department membership checks for CONFIDENTIAL and RESTRICTED.

### 2. Database Column

Add a `classification VARCHAR(20) NOT NULL DEFAULT 'internal'` column to:

- `rules` -- the primary classified resource.
- `evaluations` -- evaluation results inherit sensitivity from the evaluated subject.
- `audit_log` -- audit entries may reference classified data.

Default is `internal` to maintain backward compatibility with existing data.

### 3. PostgreSQL RLS Policies

Classification RLS policies coexist with the existing tenant isolation policies. Both layers must pass for a row to be visible. The classification policies use session variables:

- `app.user_id` -- the authenticated user's ID.
- `app.user_clearance` -- the user's maximum clearance level.
- `app.user_departments` -- comma-separated list of department IDs the user belongs to.

Policy logic per classification level:

- **PUBLIC**: visible if `app.user_id` is set (authenticated).
- **INTERNAL**: visible if `app.user_id` is set (same as PUBLIC for org members).
- **CONFIDENTIAL**: visible if the user belongs to the rule's owning department OR has AUDITOR capacity for that department.
- **RESTRICTED**: visible if the user has OWNER or AUDITOR capacity in the owning department.

### 4. Elasticsearch Document-Level Security

Every search query includes a classification filter derived from the user's clearance and department membership. The filter is injected by `services/classification/es_filter.py` and must not be bypassed.

### 5. PII Redaction

Subjects declare PII fields at construction time via `pii_fields: list[str]` (JSON paths into `facts`). A `redact_pii()` function in `core/pii/redactor.py` replaces marked fields with `[REDACTED]` placeholders before logging or external transmission. This complements the pattern-based PII sanitizer already in `core/pii/__init__.py`.

### 6. Session Context Helper

A `with_user_context()` async function in `core/db_context.py` sets the RLS session variables before any classified query. All queries against classified tables MUST call this first. The helper uses parameterized queries to prevent SQL injection.

## Consequences

- All existing rules default to `internal` classification, preserving current behavior.
- Tenant-based RLS and classification-based RLS are independent layers; both must pass.
- Adding a new classification level requires updating the enum, RLS policies, ES filters, and tests.
- Every endpoint that returns classified data must verify that the session context is set. Tests must verify both directions (high clearance sees all, low clearance is restricted).
- The PII redactor is field-path-based (explicit marking), not pattern-based. It complements the existing regex-based sanitizer.

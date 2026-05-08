# ADR 003: Classification and Row-Level Security

**Status:** Accepted

**Date:** 2026-05-08

## Context

The Rule Repository stores data with varying sensitivity levels across multiple tenants. Rules, evaluations, and audit entries need access control that goes beyond simple role-based checks -- classification-based Row-Level Security (RLS) must ensure that users only see data matching their clearance level and department membership.

## Decision

We use PostgreSQL Row-Level Security with four classification levels (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`). Every query session sets three variables via `with_user_context()`:

- `app.user_id` -- the authenticated user
- `app.user_clearance` -- the user's maximum classification clearance
- `app.user_departments` -- comma-separated department IDs

RLS policies on `rules`, `evaluations`, and `audit_log` tables enforce that:

- `PUBLIC` rows are visible to all authenticated users within the tenant
- `INTERNAL` rows are visible to any tenant member
- `CONFIDENTIAL` rows are visible to department members and approved subscribers
- `RESTRICTED` rows are visible only to named individuals or users with `AUDITOR` capacity

Classification-based RLS coexists with tenant-based RLS. Both layers must pass for a row to be visible.

## Consequences

- Every database query must call `with_user_context()` first -- direct queries bypass classification
- Elasticsearch queries must include a matching classification filter via `services/classification/es_filter.py`
- The audit log itself is subject to classification -- auditors access it through a separate connection pool
- Performance impact is minimal since RLS is index-backed on `tenant_id` and `classification`

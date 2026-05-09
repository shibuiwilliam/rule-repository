# ADR 0002: Department and Capacity Model

## Status

Accepted

## Context

The Rule Repository was originally engineering-centric: rules belonged to "projects" and governance was managed through a simple owner/approver model on each rule's `governance` JSONB field. As the platform expands to serve legal, HR, finance, sales, marketing, and operations functions (Phase 7 cross-organizational pivot), we need a first-class organizational model that:

1. Maps real departments to rule ownership.
2. Defines user capacities (roles relative to a department) that drive approval workflows, notification fan-out, and access control.
3. Supports hierarchical departments (e.g., "Legal > IP" or "Engineering > Platform").
4. Enables department-aware routing of proposals, digests, and audit access.
5. Decouples organizational structure from project structure (a department may own rules across many projects).

The existing `governance.owner` string field is insufficient: it has no referential integrity, no concept of delegation, and no way to resolve "who are all the reviewers for rules owned by Legal?"

## Decision

### 1. Domain Types

Introduce four domain types in `domain/department.py`:

- **`DepartmentType`** — enum of well-known department categories (legal, hr, finance, sales, marketing, it, operations, rnd, executive, custom).
- **`Capacity`** — enum of user roles relative to a department: `owner`, `reviewer`, `subscriber`, `auditor`. These are not global roles; a user may be an `owner` in Legal and a `subscriber` in Finance.
- **`Department`** — frozen dataclass representing an organizational unit with optional parent (tree structure), head user, cost center, and locale.
- **`RuleOwnership`** — frozen dataclass binding a rule to an owning department with optional delegation to specific users.
- **`CapacityAssignment`** — frozen dataclass binding a user to a department with a specific capacity and optional rule filter (scope narrowing).

### 2. Persistence

Three new tables:

- `departments` — stores department metadata with self-referential `parent_id` FK.
- `capacity_assignments` — stores user-to-department capacity bindings with optional JSONB `rule_filter`.
- `rule_ownerships` — stores rule-to-department ownership with JSONB `delegated_to` array.

### 3. Service Layer

`DepartmentService` in `services/departments/service.py` provides:

- CRUD for departments and capacity assignments.
- `resolve_owner(rule_id)` — returns the owning department.
- `resolve_approvers(rule_id, severity)` — returns user IDs with `owner` or `reviewer` capacity in the owning department. For CRITICAL severity, includes the department head.
- `resolve_audience(rule_id, capacity)` — returns user IDs with the given capacity for the owning department.
- `effective_capacity(user_id, rule_id)` — returns the highest capacity a user holds for the rule's owning department.

### 4. Integration Points

- **Proposals**: route to `resolve_approvers()` instead of reading `governance.approvers`.
- **Intelligence digests**: group by department, send to each department's reviewers.
- **Audit**: read access uses `Capacity.AUDITOR` plus classification clearance.
- **Notifications**: fan-out uses `resolve_audience()`.

### 5. Identity Source

In production, departments and capacity assignments are populated from an identity provider (Okta, Azure AD, Google Workspace) via SCIM sync. In development, they are populated via `make seed` or the API.

## Consequences

- All department-aware features depend on the `departments` and `capacity_assignments` tables being populated.
- The existing `governance.owner` field on `RuleModel` remains for backward compatibility but is secondary to `rule_ownerships`.
- Adding a new department type requires only adding to the `DepartmentType` enum; no code changes in the service layer.
- Capacity-based access control is additive to classification-based RLS (Phase 7 Stream C).

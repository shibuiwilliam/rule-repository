# Project Entity — Implementation Plan

> Status: **COMPLETED**
> Date: 2026-04-29

---

## 1. Problem Statement

The Rule Repository had no top-level organizational unit. All rules, documents, snapshots, and other resources existed in a single flat namespace, making it impossible to separate rule sets for different purposes (e.g., "Web Coding Rules" vs. "HR Policy Rules").

## 2. Design Decisions

- **Project is NOT Federation.** Federation handles hierarchical rule inheritance (org->team->project overrides). Project is simpler: a flat list of workspaces that scope all resources.
- **Query-parameter scoping** (`?project_id=...`) rather than URL path nesting (`/projects/{id}/rules`). Preserves all existing endpoint contracts without breaking changes.
- **Default project** (`00000000-0000-0000-0000-000000000001`) for existing data. All pre-existing rows are backfilled during migration.
- **LLM cache stays global** — same inputs produce same outputs regardless of project.
- **Child tables inherit project scope** through their parent FK (e.g., extractions inherit from documents, test cases from rules).

## 3. What Was Implemented

### Database (Phase 1)
- **New table:** `projects` (id UUID PK, name, description, created_at, updated_at)
- **New column:** `project_id` UUID FK added to 7 tables: `rules`, `documents`, `discovery_scans`, `corrections`, `rule_set_snapshots`, `enforcement_policies`, `alerts`
- **Migration:** `012_add_projects.py` — creates table, inserts default project, adds columns as nullable, backfills, sets NOT NULL, adds indexes
- **ORM:** `ProjectModel` class added to `models.py`

### Backend CRUD (Phase 2)
- `schemas/project.py` — ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
- `services/project_service.py` — ProjectService (create, get, list, update)
- `api/v1/projects.py` — POST/GET/GET{id}/PATCH endpoints
- Registered in `api/v1/__init__.py`

### Backend Wiring (Phase 3)
- `rule_repo.py` — `list_rules()` accepts `project_id` filter
- `rule_service.py` — `create_rule()` and `list_rules()` accept and pass `project_id`
- `schemas/rule.py` — `RuleResponse` includes `project_id`
- All 7 API routers updated with `project_id: str | None = Query(default=None)`: rules, search, extraction, discovery, feedback, snapshots, alerts, intelligence
- ES index template updated with `project_id: keyword` field
- ES documents include `project_id` in indexed data

### Frontend (Phase 4)
- `lib/project-context.tsx` — ProjectProvider + useProject() hook, persists selection to localStorage
- `app/(dashboard)/ProjectSelector.tsx` — dropdown in sidebar
- `app/(dashboard)/projects/page.tsx` — project management page (list, create, switch)
- `app/(dashboard)/layout.tsx` — wraps all pages in ProjectProvider, adds project selector and Settings nav section
- `lib/api.ts` — Project interface, CRUD functions, `getRules()` accepts `projectId`
- `rules/page.tsx` — accepts `project_id` search param

## 4. Files Changed

| Type | Files |
|---|---|
| New | `alembic/versions/012_add_projects.py`, `schemas/project.py`, `services/project_service.py`, `api/v1/projects.py`, `lib/project-context.tsx`, `ProjectSelector.tsx`, `projects/page.tsx` |
| Modified | `models.py` (ProjectModel + 7 FK columns), `rule_repo.py`, `rule_service.py`, `schemas/rule.py`, `api/v1/__init__.py`, `api/v1/rules.py`, `api/v1/search.py`, `api/v1/extraction.py`, `api/v1/discovery.py`, `api/v1/feedback.py`, `api/v1/snapshots.py`, `api/v1/alerts.py`, `api/v1/intelligence.py`, `intelligence/service.py`, `infra/elasticsearch/rules-index-template.json`, `lib/api.ts`, `layout.tsx`, `rules/page.tsx` |

## 5. Validation
- 142 Python unit tests pass
- Zero TypeScript errors in new files
- Zero ESLint errors in new files
- Ruff warnings are pre-existing B008 (standard FastAPI `Depends()` pattern)

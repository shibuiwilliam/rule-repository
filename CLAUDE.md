# CLAUDE.md

> Operational guide for Claude Code when working on the **Rule Repository** project.
> For the project vision, domain model, and roadmap, see **PROJECT.md**.
> For diagnosis and improvement plan, see **IMPROVEMENT.md**.

This file is the working contract between you (Claude Code) and the project. Read it before making changes. When in doubt, follow the rules in this file over your prior conventions.

The current focus is **Phase 7+**: pivoting the architecture from engineering-centric to genuinely cross-organizational. Treat that direction as primary. Engineering capabilities continue to ship, but as one domain among many — not the whole product.

---

## Table of Contents

1. [Project at a Glance](#1-project-at-a-glance)
2. [Tech Stack](#2-tech-stack)
3. [Repository Layout](#3-repository-layout)
4. [Quick Start](#4-quick-start)
5. [Common Commands](#5-common-commands)
6. [Coding Conventions](#6-coding-conventions)
7. [Backend Architecture](#7-backend-architecture)
8. [Frontend Notes](#8-frontend-notes)
9. [Gemini API Integration](#9-gemini-api-integration)
10. [Data Layer](#10-data-layer)
11. [Subject Polymorphism Patterns](#11-subject-polymorphism-patterns)
12. [Domain Evaluation Engine Patterns](#12-domain-evaluation-engine-patterns)
13. [Department and Capacity Patterns](#13-department-and-capacity-patterns)
14. [Classification, PII, and Multi-Tenancy](#14-classification-pii-and-multi-tenancy)
15. [Compliance-Grade Audit Patterns](#15-compliance-grade-audit-patterns)
16. [Multi-Source Discovery Patterns](#16-multi-source-discovery-patterns)
17. [Multi-Source Feedback Loop Patterns](#17-multi-source-feedback-loop-patterns)
18. [Multilingual and Jurisdiction Patterns](#18-multilingual-and-jurisdiction-patterns)
19. [Testing](#19-testing)
20. [Environment Variables](#20-environment-variables)
21. [Important Rules for Claude Code](#21-important-rules-for-claude-code)
22. [References](#22-references)

---

## 1. Project at a Glance

The Rule Repository is a cross-organizational normative management platform. It stores natural-language rules and makes them searchable, evaluable, and enforceable across legal, HR, finance, sales, marketing, IT, operations, and engineering functions.

**This repository is a monorepo** containing the backend server, frontend, Python client SDKs, CLI tools, MCP server, and local dev infrastructure. The first deliverable is a fully working local stack via **Docker Compose**.

**The current strategic priority is the cross-organizational pivot** described in IMPROVEMENT.md: introduce subject polymorphism, model the organization as a first-class entity, expand discovery to non-code artifacts, ship domain template packs, and harden the audit layer to compliance grade. Read PROJECT.md §10 (roadmap) for the phase plan.

---

## 2. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend | **Python 3.13** + FastAPI | Library management with **uv** |
| Frontend | **TypeScript**, **React 19**, **Next.js 15**, **Tailwind CSS** | Library management with **pnpm** |
| Python clients | **Python 3.13** (Rule Client, Agentic Rule Client, CLI) | Library management with **uv** |
| LLM | **Gemini 3 Flash** (`gemini-3-flash-preview`) and **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`) | via `google-genai` SDK; pluggable provider layer planned |
| Document parsing / OCR | **Gemini Files API** + document understanding | PDF, DOCX, text, markdown |
| Relational DB | **PostgreSQL 17** with `pgvector` and **Row-Level Security** | rules, revisions, audit log, departments, classifications |
| Search | **Elasticsearch 8.x** with kNN + BM25 + document-level security | full-text + hybrid search |
| Graph DB | **Neo4j 5.x** | rule relationships and provenance lineage |
| Job queue | **arq** + **Redis 7** | background tasks (health scoring, recommendations, correction analysis, regulation feeds) |
| WORM storage | **S3 Object Lock** / **Azure Immutable Blob** / **GCS Bucket Lock** | pluggable backend for compliance-grade audit |
| Public anchoring | **Sigstore Rekor** (default) | hash chain anchoring |
| MCP | **FastMCP** (mcp >= 1.9), 12+ tools | agent integration |
| Local orchestration | **Docker Compose** | dev + integration tests |

Do **not** introduce additional frameworks or services without updating PROJECT.md and this file in the same change.

---

## 3. Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                          # FastAPI backend
│   │   ├── pyproject.toml
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/                  # REST/Intent/Evaluate/Gateway/MCP routers
│   │   │   ├── core/                    # config, logging, errors, auth, middleware,
│   │   │   │                            #   PII, classification context
│   │   │   ├── domain/                  # Pure domain types
│   │   │   │   ├── rule.py
│   │   │   │   ├── subject.py           # Subject protocol, SubjectKind enum
│   │   │   │   ├── department.py        # Department, Capacity, RuleOwnership
│   │   │   │   ├── classification.py    # Classification enum, clearance
│   │   │   │   ├── verdict.py
│   │   │   │   ├── evaluation.py        # Remediation, RuleVerdict
│   │   │   │   ├── audit.py             # AuditEntry
│   │   │   │   ├── evidence.py          # EvidenceRef
│   │   │   │   ├── proposal.py
│   │   │   │   └── agent.py
│   │   │   ├── services/
│   │   │   │   ├── evaluation/          # subject-agnostic orchestrator
│   │   │   │   │   ├── service.py       #   pipeline orchestrator
│   │   │   │   │   ├── batch_evaluator.py
│   │   │   │   │   ├── evaluation_core.py
│   │   │   │   │   ├── rule_selector.py
│   │   │   │   │   ├── verdict_aggregator.py
│   │   │   │   │   ├── conflict_aggregator.py
│   │   │   │   │   ├── graph_resolver.py
│   │   │   │   │   ├── impact_preview.py
│   │   │   │   │   ├── subject_registry.py   # NEW — SubjectKind dispatch
│   │   │   │   │   └── subjects/             # NEW — per-domain Subject adapters
│   │   │   │   │       ├── code_diff_subject.py
│   │   │   │   │       ├── clause_set_subject.py
│   │   │   │   │       ├── event_subject.py
│   │   │   │   │       ├── transaction_subject.py
│   │   │   │   │       ├── creative_subject.py
│   │   │   │   │       ├── decision_subject.py
│   │   │   │   │       ├── identity_subject.py
│   │   │   │   │       └── document_subject.py
│   │   │   │   ├── extraction/          # multi-source rule extraction
│   │   │   │   ├── discovery/           # multi-source discovery
│   │   │   │   │   ├── service.py
│   │   │   │   │   ├── github_importer.py
│   │   │   │   │   ├── analyzers/
│   │   │   │   │   │   ├── code/        # claude_md, linter_config, code_patterns
│   │   │   │   │   │   └── policy/      # NEW — pdf, docx, contract_corpus,
│   │   │   │   │   │                    #   confluence, sharepoint, notion,
│   │   │   │   │   │                    #   regulation_feed
│   │   │   │   │   └── pattern_detector.py
│   │   │   │   ├── feedback/            # multi-source feedback loop
│   │   │   │   │   ├── service.py
│   │   │   │   │   ├── pr_capture.py
│   │   │   │   │   ├── contract_capture.py    # NEW
│   │   │   │   │   ├── decision_capture.py    # NEW
│   │   │   │   │   ├── audit_capture.py       # NEW
│   │   │   │   │   ├── deal_capture.py        # NEW
│   │   │   │   │   ├── dispute_capture.py     # NEW
│   │   │   │   │   ├── explicit_capture.py    # NEW
│   │   │   │   │   ├── correction_analyzer.py
│   │   │   │   │   └── auto_drafter.py        # subject-aware
│   │   │   │   ├── intelligence/        # health, effectiveness, digest, comparison
│   │   │   │   ├── context_delivery/    # MCP context delivery + scope registry
│   │   │   │   ├── federation/          # org/team/project hierarchy
│   │   │   │   ├── departments/         # NEW — Department/Capacity service
│   │   │   │   ├── classification/      # NEW — RLS context, clearance enforcement
│   │   │   │   ├── audit/               # NEW — hash chain, WORM mirror, anchor
│   │   │   │   ├── playground/          # subject-aware sandbox
│   │   │   │   ├── snapshots/
│   │   │   │   ├── proposals/
│   │   │   │   ├── agent_governance/
│   │   │   │   ├── marketplace/
│   │   │   │   ├── search.py
│   │   │   │   ├── rule_service.py
│   │   │   │   └── intent.py
│   │   │   ├── adapters/                # external systems
│   │   │   │   ├── postgres.py
│   │   │   │   ├── elasticsearch.py
│   │   │   │   ├── neo4j.py
│   │   │   │   ├── gemini.py
│   │   │   │   ├── files.py
│   │   │   │   ├── llm/                 # NEW — pluggable LLMProvider impls
│   │   │   │   │   ├── base.py
│   │   │   │   │   ├── gemini.py
│   │   │   │   │   ├── anthropic.py     # future
│   │   │   │   │   └── openai.py        # future
│   │   │   │   ├── audit_storage/       # NEW — pluggable WORM
│   │   │   │   │   ├── base.py
│   │   │   │   │   ├── s3_object_lock.py
│   │   │   │   │   ├── azure_immutable.py
│   │   │   │   │   └── gcs_bucket_lock.py
│   │   │   │   ├── evidence_storage/    # NEW — content-addressed evidence
│   │   │   │   ├── timestamp_authority/ # NEW — hash anchoring (Rekor)
│   │   │   │   ├── contract_parser.py   # NEW — clause extraction
│   │   │   │   ├── contract_compare.py  # NEW — semantic clause diff
│   │   │   │   ├── hr_systems/          # NEW — Workday, SmartHR, etc.
│   │   │   │   ├── erp/                 # NEW — SAP, freee会計, etc.
│   │   │   │   └── integrations/        # NEW — Confluence, SharePoint, etc.
│   │   │   ├── mcp/                     # MCP server (tools, resources, prompts)
│   │   │   ├── gateway/                 # webhook normalizers, policy engine
│   │   │   ├── integrations/            # GitHub webhook, CI formatters, regulator export
│   │   │   ├── workers/                 # arq cron jobs
│   │   │   └── schemas/                 # Pydantic request/response models
│   │   ├── alembic/                     # migrations
│   │   └── tests/
│   └── frontend/                        # Next.js 15, React 19, TS, Tailwind (pnpm)
│       └── app/                         # App Router
│           ├── (dashboard)/             # default home + rules + search +
│           │                            #   intelligence + marketplace + ...
│           ├── (legal)/                 # NEW — legal department UI surface
│           │                            #   /contracts/review/[id]
│           ├── (hr)/                    # NEW — HR department UI surface
│           │                            #   /events/[id]
│           ├── (finance)/               # NEW — finance department UI
│           │                            #   /transactions/[id]
│           └── (marketing)/             # NEW — marketing UI
│                                        #   /creatives/review/[id]
├── packages/
│   ├── rule-client/                     # Python SDK
│   ├── agentic-client/                  # Python evaluation SDK
│   └── cli/                             # rulerepo-check, rulerepo-hook,
│                                        #   rulerepo-ingest, rulerepo-export,
│                                        #   rulerepo-context, rulerepo-init
├── sample_rules/
│   ├── coding_rules/                    # existing
│   ├── company_rules/                   # existing
│   ├── sales_team_rules/                # existing
│   ├── hr_rules/                        # NEW
│   ├── legal_rules/                     # NEW
│   ├── finance_rules/                   # NEW
│   └── templates/                       # YAML rule templates
│       ├── python-fastapi.yaml          # existing
│       ├── typescript-react.yaml        # existing
│       ├── security-owasp.yaml          # existing
│       ├── api-design.yaml              # existing
│       ├── testing-standards.yaml       # existing
│       ├── hr-attendance-jp.yaml        # NEW (Phase 7)
│       ├── hr-overtime-jp.yaml          # NEW
│       ├── hr-leave-jp.yaml             # NEW
│       ├── expense-policy-standard.yaml # NEW (Phase 7)
│       ├── procurement-segregation.yaml # NEW
│       ├── contract-nda-standard.yaml   # NEW (Phase 7)
│       ├── contract-msa-standard.yaml   # NEW
│       ├── contract-subcontract-jp.yaml # NEW
│       ├── marketing-keihyohou.yaml     # NEW
│       ├── marketing-yakkihou.yaml      # NEW
│       ├── aml-kyc-baseline.yaml        # NEW
│       ├── bribery-fcpa-jp.yaml         # NEW
│       ├── data-privacy-japan.yaml      # NEW
│       ├── data-privacy-gdpr.yaml       # NEW
│       └── inhouse-aiuse-policy.yaml    # NEW
├── infra/                               # Dockerfiles, init SQL with RLS,
│                                        #   ES templates, Neo4j constraints
├── scripts/                             # seed_data, reconcile_graph,
│                                        #   reindex_elasticsearch, generate_claude_md,
│                                        #   anchor_audit_log
├── development/                         # technical docs
│   └── adr/                             # Architecture Decision Records
├── docs/                                # mkdocs site
├── docker-compose.yml
├── Makefile
├── .pre-commit-config.yaml
├── PROJECT.md                           # vision, domain model, roadmap
├── IMPROVEMENT.md                       # diagnosis and improvement plan
└── CLAUDE.md                            # this file
```

When adding a new package, place it under `apps/` (deployable apps) or `packages/` (libraries). Update `pyproject.toml` (uv workspace) or `pnpm-workspace.yaml` accordingly.

---

## 4. Quick Start

The whole stack must come up with one command. If your changes break this, fix it before continuing.

```bash
cp .env.example .env            # then fill in GEMINI_API_KEY
make up                         # or: docker compose up --build -d
```

Expected services after `up`:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | REST + Intent + Evaluate + Gateway |
| API docs (OpenAPI) | http://localhost:8000/docs | FastAPI Swagger UI |
| Frontend | http://localhost:3000 | Next.js dev server |
| MCP Server | http://localhost:8001 | Streamable-HTTP MCP for agents |
| PostgreSQL | localhost:5432 | `ruledb` |
| Elasticsearch | http://localhost:9200 | search index |
| Neo4j Browser | http://localhost:7474 | rule graph |
| Redis | localhost:6379 | job queue (arq) |
| arq-worker | — | background task processor |

The frontend talks to the backend over `NEXT_PUBLIC_API_BASE_URL`. The Python clients talk to the backend over `RULEREPO_SERVER_URL`. Optional WORM storage is configured via `AUDIT_WORM_BACKEND` (off by default in dev).

---

## 5. Common Commands

### Backend (apps/server)

```bash
cd apps/server
uv sync
uv run uvicorn rulerepo_server.main:app --reload
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "..."
```

### Frontend (apps/frontend)

```bash
cd apps/frontend
pnpm install
pnpm dev
pnpm build && pnpm start
pnpm lint
pnpm test
pnpm typecheck
```

### Python SDKs and CLI (packages/*)

```bash
cd packages/rule-client
uv sync
uv run pytest
uv build
```

```bash
rulerepo-check --diff "$(git diff origin/main...HEAD)" --format github-actions
rulerepo-hook preflight --file src/api/handler.py --agent-id claude-code
rulerepo-hook posthoc --file src/api/handler.py
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python
rulerepo-export --project backend-api --output rules.yaml
rulerepo-context update --file CLAUDE.md
```

### MCP Server

```bash
uv run rulerepo-mcp                                  # stdio (local, for Claude Code)
MCP_TRANSPORT=streamable-http uv run rulerepo-mcp    # HTTP (remote agents)
```

### Whole repo (from root)

```bash
make help                       # show all targets
make up
make down
make reset                      # tear down + wipe volumes
make seed                       # load sample rules and templates
make precommit.install
make test
make check                      # format + lint + test
docker compose logs -f server
```

---

## 6. Coding Conventions

### Python (server, clients, CLI)

- **Python 3.13**. Use modern syntax: built-in generics (`list[str]`, `dict[str, int]`), `match` where it improves clarity.
- **Type hints are mandatory** on all public functions. mypy must pass on `src/`.
- **Formatter and linter**: `ruff` (both linting and formatting). Configure via `pyproject.toml`. No `black`, no `isort` (ruff covers both).
- **Naming**: snake_case for functions/vars, PascalCase for classes, SCREAMING_SNAKE_CASE for constants. Module names lowercase.
- **Docstrings**: Google style. Required on all public APIs.
- **Errors**: define a project-specific exception hierarchy under `rulerepo_server.errors` / `rulerepo.errors`. Never raise bare `Exception`.
- **Logging**: `structlog` with JSON output. Never `print()` outside of one-off scripts.
- **Pydantic** for all data validation at API boundaries. Use Pydantic v2 idioms.
- **Tests**: `pytest` + `pytest-asyncio`. Aim for unit tests on pure logic, integration tests against the docker-compose stack.

### TypeScript (frontend)

- **Strict TS**: `"strict": true` in `tsconfig.json`. No `any` without justification.
- **App Router** (Next.js 14+ idioms). Server Components by default, Client Components only when needed.
- **Tailwind**: prefer utility classes over custom CSS. Centralize design tokens in `tailwind.config.ts`.
- **State**: prefer Server Components and URL state. For client state, `zustand`. For server-state caching, `@tanstack/react-query`.
- **Components**: PascalCase files, one component per file unless tightly coupled.
- **API calls**: generated TypeScript client from the backend's OpenAPI spec (`openapi-typescript` + `openapi-fetch`). Do not hand-write types that already exist in the API contract.
- **Linting**: ESLint + Prettier. `pnpm lint` must pass.

### Commits and branches

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- Branch from `main`. Open PRs even for solo work — keeps history reviewable.
- One ADR per significant architectural decision in `development/adr/`.

---

## 7. Backend Architecture

The server is a single FastAPI application. Key API namespaces:

- `/api/v1/rules`, `/api/v1/search`, `/api/v1/extraction`, `/api/v1/discover`
- `/api/v1/evaluate`, `/api/v1/intent`
- `/api/v1/gateway`
- `/api/v1/intelligence`
- `/api/v1/feedback`, `/api/v1/federations`
- `/api/v1/departments`, `/api/v1/capacities` (NEW)
- `/api/v1/classifications` (NEW)
- `/api/v1/audit`, `/api/v1/audit/export` (audit-grade endpoints, RESTRICTED access)
- `/api/v1/playground`, `/api/v1/snapshots`, `/api/v1/alerts`
- `/api/v1/proposals`, `/api/v1/agent-governance`, `/api/v1/marketplace`
- `/api/v1/integrations` (NEW — connector management)

**Layering rule**: `api` depends on `services`. `services` depends on `domain` and `adapters`. `domain` depends on nothing else in the project. Do not import upward.

**Async**: the API layer is fully async. DB calls use `asyncpg` (or `sqlalchemy[asyncio]`), Elasticsearch via the async client, Neo4j via the official async driver, Gemini via `google-genai`.

**Subject-agnostic orchestration**: `services/evaluation/service.py` does not know about code diffs, contract clauses, or transactions. It calls `subject_registry.resolve(subject_kind)` to obtain the correct adapter, then orchestrates the pipeline. Adding a new domain means adding a new `Subject` adapter, not modifying the orchestrator.

**Department-aware governance**: `services/proposals/`, `services/intelligence/`, and notification fan-out always go through `services/departments/` to resolve owners, approvers, and audiences.

---

## 8. Frontend Notes

The frontend is the operator console. It now serves multiple departments, not only engineering.

- **Default dashboard** (`app/(dashboard)/page.tsx`) shows a department-aware home: pending reviews, top violations, alerts, and trends scoped to the user's department(s).
- **Department-specific surfaces** under `app/(legal)/`, `app/(hr)/`, `app/(finance)/`, `app/(marketing)/` provide domain-tailored review pages.
- **No-code rule editor** (`/rules/new/wizard`) lets non-engineers author rules using dropdowns; Gemini drafts the `statement` and shows it for human review.
- **Intent-first search** is surfaced on the home page for non-engineers; advanced search modalities are still available.
- **Graph view** (Neo4j-backed) renders using `react-flow`. Pick one library and stick with it.

When adding a new department surface, follow the existing `(dashboard)` route group conventions: route group name in parentheses, shared `layout.tsx` for navigation, dedicated pages within.

---

## 9. Gemini API Integration

The LLM layer is the heart of this system. Get this right.

### 9.1 SDK

- **Use `google-genai`** (the new unified SDK). Do **not** use the deprecated `google-generativeai`.
- Install via uv: `uv add google-genai httpx`.

### 9.2 Models

Two models are in primary use:

| Use case | Model ID | Why |
|---|---|---|
| High-throughput, routine tasks (search ranking, simple extraction, classification) | `gemini-3-flash-preview` | fast, cheap |
| High-stakes judgment (rule extraction QC, conflict detection, evaluation of CRITICAL rules) | `gemini-3.1-pro-preview` | strongest reasoning |

Centralize model selection in `core/llm.py`. Never hardcode model IDs in business logic — always read from config.

### 9.3 Domain-adaptive model selection (Phase 10)

When implemented, model choice is `(subject_kind, severity, historical_disagreement_rate) → model`. The selection function lives in `services/evaluation/model_router.py` and reads disagreement statistics from `EvaluationRecordModel`. Existing callers should accept a `model_hint: ModelTier | None` and let the router decide.

### 9.4 Mandatory rules when calling Gemini

- **Do NOT change `temperature`** away from the default (1.0). Lower temperatures degrade Gemini 3 reasoning quality and can cause loops.
- Use **`thinking_level`** (not the legacy `thinking_budget`). Valid values: `minimal`, `low`, `medium`, `high`. Default to `low` for high-throughput, `high` for judgment tasks.
- For function calling, **thought signatures must be cycled through** every turn. The `google-genai` SDK and standard chat history handle this automatically — do not strip signatures.
- For PDFs in document processing, set `media_resolution: "media_resolution_medium"` (560 tokens/page). Going higher rarely helps OCR.
- Use **structured output** (`response_mime_type="application/json"` + `response_json_schema`) for any call that must return parsed data. Do not regex out fields from free-form text.

### 9.5 Document ingestion (PDF, DOCX, text, markdown)

- **PDFs**: upload via the **Files API** (`client.files.upload(...)`) for documents > a few pages. Files API is free, files persist 48 hours, max 50 MB / 1000 pages.
- For small / one-shot PDFs, inline `Part.from_bytes(data=..., mime_type='application/pdf')` is fine.
- **DOCX**: parse with `python-docx` first, then pass extracted text/structure to Gemini. Do not pass DOCX bytes to Gemini directly (it does not render them meaningfully).
- **Text and markdown**: pass as plain text. Gemini's native document understanding renders only PDFs visually; markdown and text are taken as raw input.
- Each PDF page is roughly 258 tokens for image content; extracted native text is included free.
- The extraction pipeline (`services/extraction/`) wraps these calls; do not bypass it from random parts of the codebase.

### 9.6 Cost and latency discipline

- Cache LLM responses by `hash(inputs + model + prompt_version)` in Postgres. Invalidate on rule revision.
- Use `gemini-3.1-flash-lite-preview` only if explicitly approved.
- Long-context calls (rule corpus + large doc) should use **context caching** for repeated reuse.
- Batched evaluation (one Gemini call covering multiple rules) is the default for the evaluation pipeline; per-rule fallback exists but is the slow path.

### 9.7 Determinism, audit, and prompt versioning

- Every LLM call that produces a verdict, a candidate rule, or a relationship suggestion **must** log: model ID, prompt version (a content hash), inputs, outputs, latency, timestamp. This goes to the audit log.
- Prompts live in `services/<area>/prompts/` as standalone `.txt` or `.md` files, versioned in git. No inline prompt strings scattered across the codebase.
- When you change a prompt, the prompt's content hash changes, which invalidates response caches and produces a new audit-log lineage.

### 9.8 Pluggable LLM provider

The default provider is Gemini via `adapters/llm/gemini.py`. The `LLMProvider` Protocol in `adapters/llm/base.py` allows alternative providers. Self-hosted, Anthropic, and OpenAI implementations are planned for regulated-industry deployments. **Do not assume Gemini specifics** in `services/`; route through `LLMProvider`.

---

## 10. Data Layer

### 10.1 PostgreSQL (system of record)

- Stores rules, revisions, source documents, evaluations, audit log, departments, capacities, ownerships, classifications, federations, snapshots, proposals, agent profiles, marketplace packages.
- Migrations: `alembic`. One head per branch; rebase migrations before merging.
- The audit log table is **append-only**. Enforced with a Postgres trigger that rejects updates and deletes. Hash chain column links each row to the previous.
- **Row-Level Security** is enabled on all classification-bearing tables: `rules`, `documents`, `evaluations`, `audit_log`. Each session must set `current_user_id`, `current_user_clearance`, and `current_user_departments` before issuing queries. The session helpers live in `core/db_context.py`. **Never run a query without setting these.**

### 10.2 Elasticsearch (search)

- Index `rules` with: `statement` (analyzed), `tags`, `scope`, `modality`, `effective_period`, `classification`, `embedding` (dense_vector), `subject_kinds`, `locale`, `jurisdiction`.
- Use BM25 + kNN hybrid scoring. Rerank top-k with the LLM only when the user requests "smart" search.
- **Document-level security** is mandatory: every search query must include the user's classification clearance and department membership as a filter. Helper: `services/classification/es_filter.py`.
- Re-index on rule revision.

### 10.3 Neo4j (relationship graph)

- One node label: `Rule`. Node `id` matches the Postgres rule ID.
- Relationships: `REFINES`, `OVERRIDES`, `CONFLICTS_WITH`, `DEPENDS_ON`, `DERIVES_FROM`, `SUCCEEDS`, `LOCALIZES`. Direction matters and is documented in PROJECT.md §5.4.
- Postgres is the source of truth for rule existence; Neo4j is a derived projection of relationships. If they disagree, Postgres wins and Neo4j is rebuilt.
- Provide a reconciler script (`scripts/reconcile_graph.py`).
- Classification is checked at the API gateway, not in Cypher. Neo4j responses must be filtered by classification before being returned to the client.

### 10.4 WORM Audit Storage (compliance grade)

- Pluggable backends in `adapters/audit_storage/`. Default in dev: disabled. In staging/production for `RESTRICTED` and `CONFIDENTIAL` audit entries: required.
- The audit service writes to PostgreSQL first (for transaction atomicity), then asynchronously mirrors to WORM. Mirror failures generate `audit_mirror_failed` alerts.
- Hash chain heads are anchored periodically to a transparency log via `adapters/timestamp_authority/` (Sigstore Rekor by default). Anchor receipts are themselves stored in the audit log.

### 10.5 Evidence Storage

- Content-addressed evidence in `adapters/evidence_storage/`. Default backend: S3-compatible object store with object lock for `RESTRICTED` evidence.
- Evidence references in `EvaluationRecord.evidence_refs` are hashes; tampering is detectable.

---

## 11. Subject Polymorphism Patterns

This is the most important architectural concept in Phase 7+. Read this section in full before touching the evaluation pipeline.

### 11.1 The `Subject` Protocol

```python
# domain/subject.py
class SubjectKind(str, Enum):
    CODE_DIFF = "code_diff"
    CLAUSE_SET = "clause_set"
    EVENT = "event"
    TRANSACTION = "transaction"
    CREATIVE = "creative"
    DECISION = "decision"
    IDENTITY = "identity"
    DOCUMENT = "document"

class Subject(Protocol):
    kind: SubjectKind
    identifier: str
    facts: dict[str, Any]
    attachments: list[Attachment]
    locale: str | None
    jurisdiction: str | None
    pii_fields: list[str]   # JSON paths into `facts`

    def render_for_llm(self, format: PromptFormat) -> str: ...
    def extract_features(self) -> dict[str, Any]: ...
    def parse_remediation(self, raw: dict) -> Remediation | None: ...
```

### 11.2 Subject Registry

```python
# services/evaluation/subject_registry.py

_REGISTRY: dict[SubjectKind, type[SubjectAdapter]] = {}

def register(kind: SubjectKind):
    def decorator(cls: type[SubjectAdapter]) -> type[SubjectAdapter]:
        _REGISTRY[kind] = cls
        return cls
    return decorator

def resolve(kind: SubjectKind) -> SubjectAdapter:
    try:
        return _REGISTRY[kind]()
    except KeyError as e:
        raise UnsupportedSubjectKindError(kind) from e
```

Each adapter under `services/evaluation/subjects/` decorates itself with `@register(SubjectKind.CLAUSE_SET)` etc.

### 11.3 Adding a new Subject

1. Define the `facts` schema (Pydantic) for the new domain.
2. Implement `services/evaluation/subjects/<kind>_subject.py` decorated with `@register`.
3. Add prompt templates under `services/evaluation/subjects/prompts/<kind>/`.
4. Implement domain-specific aggregation (if simple verdict union is insufficient) in `services/evaluation/<kind>_aggregator.py`.
5. Add evaluation tests under `tests/evaluation/subjects/test_<kind>_subject.py`.
6. Update `RuleModel.subject_kinds` indexing to include the new kind.
7. Document in `PROJECT.md §6.3`.

### 11.4 Migration from CODE_DIFF

The existing code path was the only path. Phase 7 isolates it as `CodeDiffSubject` without breaking behavior:

- `EvaluateRequest.subject_kind` defaults to `CODE_DIFF`.
- Existing callers (CI, GitHub App, Claude Code hooks) see no change.
- All 212+ existing tests must remain green during the refactor. Run `make test` before and after.

### 11.5 Common pitfalls

- **Do not** put domain logic in `evaluation_core.py` or `service.py`. They are subject-agnostic.
- **Do not** add `if subject.kind == ...` branching outside of `subject_registry.resolve`.
- **Do not** assume the LLM output structure is the same across subjects. Each subject parses its own response.
- **Do not** share prompt templates across kinds. Each subject owns its prompts.

---

## 12. Domain Evaluation Engine Patterns

Engines are built on Subject Polymorphism. Follow these patterns when adding new ones.

### 12.1 Code Diff Engine

- Subject: `CodeDiffSubject`
- Inputs: unified diff, file paths, language hints
- Aggregator: existing `verdict_aggregator` and `conflict_aggregator`
- Remediation: line-scoped, optionally `auto_applicable`

### 12.2 Contract Clause Engine

- Subject: `ClauseSetSubject` carrying parsed clauses
- Adapter dependencies: `adapters/contract_parser.py` (DOCX/PDF clause extraction), `adapters/contract_compare.py` (semantic clause diff)
- Aggregator: `services/evaluation/clause_aggregator.py` — clauses-by-clause verdicts collapse to a contract-level verdict
- Remediation: clause-scoped `clause_remediation` extending `Remediation`. Mark `auto_applicable=false` by default; auto-applying contract changes is dangerous.

### 12.3 Event Engine

- Subject: `EventSubject` with optional `EventWindow` (sequence context)
- Modes:
  - `single` — evaluate the event alone
  - `sequence` — provide windowed prior events as context
  - `calendar` — provide annual aggregates
- HR system adapters: `adapters/hr_systems/{workday,sap_sf,smarthr,freee_hr}.py` — normalize source events into the canonical `EventFacts` schema.

### 12.4 Transaction Engine

- Subject: `TransactionSubject` with optional graph context
- Compliance is non-negotiable: every evaluation goes through the audit subsystem with WORM mirroring when classification ≥ CONFIDENTIAL.
- ERP adapters under `adapters/erp/`. Each implements `TransactionStream`.

### 12.5 Creative Engine

- Subject: `CreativeSubject` with multi-modal `attachments` (images/videos via Gemini Files API)
- Use `media_resolution: "media_resolution_high"` for image content where claim verification depends on visible text or design details.

### 12.6 Identity Engine

- Subject: `IdentitySubject`
- May call external screening sources (sanctions lists, adverse media via Google Search grounding). External calls go through `adapters/screening/` and are themselves cached and audited.

---

## 13. Department and Capacity Patterns

The functional organization is first-class. Phase 7 introduces these patterns.

### 13.1 Domain Model

```python
# domain/department.py
class DepartmentType(str, Enum):
    LEGAL = "legal"
    HR = "hr"
    FINANCE = "finance"
    SALES = "sales"
    MARKETING = "marketing"
    IT = "it"
    OPERATIONS = "operations"
    RND = "rnd"
    EXECUTIVE = "executive"
    CUSTOM = "custom"

class Capacity(str, Enum):
    OWNER = "owner"
    REVIEWER = "reviewer"
    SUBSCRIBER = "subscriber"
    AUDITOR = "auditor"

@dataclass(frozen=True)
class Department:
    id: str
    name: str
    type: DepartmentType
    parent_id: str | None
    head: UserRef
    cost_center: str | None
    locale: str | None
```

### 13.2 Service Layer

`services/departments/service.py` exposes:

- CRUD for departments and capacities
- `resolve_owner(rule_id) -> Department`
- `resolve_approvers(rule_id, severity) -> list[UserRef]` — multi-approver thresholds derived from severity
- `resolve_audience(rule_id, capacity) -> list[UserRef]` — fan-out for notifications
- `effective_capacity(user_id, rule_id) -> Capacity | None` — for access checks

### 13.3 Integration Points

- `services/proposals/`: routes proposals to `resolve_approvers()`.
- `services/intelligence/digest.py`: groups digest content by department and sends to each department's REVIEWERs.
- `services/marketplace/`: publishing requires `Capacity.OWNER` for the rule's owning department.
- `services/audit/`: read access uses `Capacity.AUDITOR` plus classification clearance.
- `services/notifications/`: fan-out uses `resolve_audience()`.

### 13.4 Identity Source

In production, `Department` and `CapacityAssignment` are typically populated from an identity provider (Okta, Azure AD, Google Workspace) via SCIM. The provider integration lives in `adapters/integrations/identity/` and runs as an arq job (`sync_organization`).

In dev, populate via `make seed` or directly through the API.

---

## 14. Classification, PII, and Multi-Tenancy

Classification is mandatory once Phase 7 ships. There is no "off" mode.

### 14.1 Domain

```python
class Classification(str, Enum):
    PUBLIC = "public"          # readable by all authenticated users
    INTERNAL = "internal"      # readable by org members
    CONFIDENTIAL = "confidential"  # readable by department + approved subscribers
    RESTRICTED = "restricted"  # readable by named individuals or AUDITORs only
```

Every `RuleModel`, `DocumentModel`, `EvaluationRecordModel`, `AuditLogEntryModel` carries `classification`.

### 14.2 PostgreSQL RLS

```sql
ALTER TABLE rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY rules_read_policy ON rules
  FOR SELECT
  USING (
    classification = 'public'
    OR (classification = 'internal' AND current_setting('app.user_id') IS NOT NULL)
    OR (classification IN ('confidential', 'restricted')
        AND owner_department_id = ANY (string_to_array(current_setting('app.user_departments'), ',')))
    OR EXISTS (
      SELECT 1 FROM capacity_assignments
      WHERE department_id = owner_department_id
        AND user_id = current_setting('app.user_id')
        AND capacity IN ('owner', 'auditor')
    )
  );
```

Helper in `core/db_context.py`:

```python
async def with_user_context(session: AsyncSession, user: AuthenticatedUser):
    await session.execute(text(f"SET LOCAL app.user_id = '{user.id}'"))
    await session.execute(text(f"SET LOCAL app.user_departments = '{','.join(user.department_ids)}'"))
    await session.execute(text(f"SET LOCAL app.user_clearance = '{user.clearance.value}'"))
```

**Always use this helper before queries.** Direct queries without setting the session context bypass classification.

### 14.3 Elasticsearch Document-Level Security

Each search call appends a classification filter:

```python
def classification_filter(user: AuthenticatedUser) -> dict:
    return {
        "bool": {
            "should": [
                {"term": {"classification": "public"}},
                # ... INTERNAL/CONFIDENTIAL/RESTRICTED clauses
            ]
        }
    }
```

`services/search.py` injects this filter automatically. **Do not bypass** by constructing raw ES queries elsewhere.

### 14.4 PII Marking and Redaction

Subjects mark PII fields at construction:

```python
EventSubject(
    facts={"employee_id": "E001", "ssn": "...", "overtime_hours": 50},
    pii_fields=["employee_id", "ssn"],
)
```

The redactor (`core/PII/redactor.py`) replaces marked fields with placeholders before logging. The audit log stores redacted versions. The unredacted version exists only in transient memory during evaluation and is cleared after.

### 14.5 MCP Clearance

Agents register with clearance:

```python
register_agent(agent_id="contract-reviewer-1",
               type=AgentType.contract_reviewer,
               clearance=Classification.CONFIDENTIAL)
```

The MCP server filters all rule retrieval and evaluation context by the agent's clearance, in addition to its trust level.

---

## 15. Compliance-Grade Audit Patterns

Audit-grade behavior is mandatory for `RESTRICTED` and `CONFIDENTIAL` evaluations. Best practice for `INTERNAL`. Optional but enabled by default for `PUBLIC`.

### 15.1 Audit Service

```python
# services/audit/service.py

class AuditService:
    async def record_evaluation(self, eval_record: EvaluationRecord) -> AuditEntry:
        # 1. Compute hash chain link from previous entry
        # 2. Insert into PostgreSQL audit_log (atomic with eval insert)
        # 3. If classification ≥ CONFIDENTIAL, queue WORM mirror
        # 4. Return AuditEntry
        ...
```

The `WORM mirror` job runs in arq and writes to the configured backend. Failures generate `audit_mirror_failed` alerts.

### 15.2 Hash Chain

Each audit entry includes:

- `entry_hash` — SHA-256 of (entry_content + previous_entry_hash)
- `previous_entry_hash` — link to chain

A daily cron (`anchor_audit_log`) computes the latest chain head and submits to Sigstore Rekor (or configured timestamp authority). The receipt is stored in `audit_anchor` table.

### 15.3 Separation of Duties

The application's PostgreSQL user has `INSERT` only on `audit_log` and `audit_anchor`. `SELECT` is denied. The `auditor` role has `SELECT` and is granted to AUDITORs via a separate connection pool. **The application code does not query the audit log for normal operations.** Reports are derived through dedicated audit endpoints with capacity-checked access.

### 15.4 Legal Hold

```python
class LegalHoldModel(Base):
    id: str
    scope_filter: dict        # which rules/evaluations are held
    reason: str
    held_by: UserRef
    held_at: datetime
    released_at: datetime | None
```

While a hold is active, matching rules and evaluations cannot be deleted, archived, or modified. The retention worker (`prune_old_evaluations`) skips held entries.

### 15.5 Evidence Attachment

Attaching evidence to an evaluation:

```python
evidence_ref = await evidence_storage.put(content_bytes, classification=Classification.CONFIDENTIAL)
await evaluation_service.attach_evidence(eval_id, evidence_ref)
```

Evidence is content-addressed; the hash is stored on `EvaluationRecord.evidence_refs`. Tampering is detectable on retrieval.

### 15.6 Regulator Export

Adapters under `integrations/regulator_export/`:

- `jsox.py` — J-SOX format (CSV with specific columns)
- `sox.py` — SOX format
- `fsa.py` — Japan FSA examination format
- `gdpr.py` — GDPR Article 30 records

Each takes a scope filter and a date range and produces a downloadable artifact. **All exports are themselves audit-logged.**

---

## 16. Multi-Source Discovery Patterns

Discovery is the cold-start engine. Phase 8 expands beyond code.

### 16.1 The `DocumentSource` Protocol

```python
class DocumentSource(Protocol):
    async def list_documents(self, query: SourceQuery) -> AsyncIterator[Document]: ...
    async def get_content(self, doc_id: str) -> bytes: ...
    async def get_metadata(self, doc_id: str) -> dict: ...

class IncrementalSource(DocumentSource):
    async def changes_since(self, cursor: str) -> AsyncIterator[ChangeEvent]: ...
```

### 16.2 Adding a Policy Analyzer

1. Pick the document type (PDF, DOCX, Confluence page, Notion page, regulation feed).
2. Implement an analyzer in `services/discovery/analyzers/policy/` that takes raw content, calls Gemini with the appropriate extraction prompt, and emits candidate rules.
3. If the source is incremental (Confluence, regulation feed), implement `IncrementalSource` and register a polling job in `workers/`.
4. Add fixtures and unit tests with mocked Gemini.

### 16.3 Regulation Feed Specifics

- e-Gov API and FSA notices have stable IDs and amendment dates.
- Use `derives_from` Neo4j relationships to link internal rules to source regulations.
- When a regulation amends, the worker:
  1. Detects the amendment via the feed.
  2. Identifies all rules with `DERIVES_FROM` to the amended regulation.
  3. Generates `regulation_amendment` alerts to the rule's owning department.
  4. Auto-drafts proposals showing the diff and proposed updates (Gemini-assisted).

### 16.4 Contract Corpus Mining

`contract_corpus.py` analyzes a body of historical contracts to extract de facto standard clauses. Use case: a Legal team has 1000 historical contracts but no codified standard. The analyzer:

1. Clusters clauses by semantic similarity.
2. Identifies high-frequency clause patterns.
3. Drafts candidate standard-clause rules.
4. Routes to Legal department reviewers for approval.

---

## 17. Multi-Source Feedback Loop Patterns

The flywheel is no longer code-only.

### 17.1 The `FeedbackEvent` Protocol

```python
class FeedbackKind(str, Enum):
    CODE_CORRECTION = "code_correction"
    DECISION_OVERRIDE = "decision_override"
    APPROVAL_OVERRIDE = "approval_override"
    EXCEPTION_GRANTED = "exception_granted"
    AUDIT_FINDING = "audit_finding"
    DISPUTE_OUTCOME = "dispute_outcome"
    POLICY_CLARIFICATION = "policy_clarification"
    EXPLICIT_VERDICT_OVERRIDE = "explicit_verdict_override"

class FeedbackEvent(Protocol):
    kind: FeedbackKind
    subject_kind: SubjectKind
    original_verdict: Verdict
    corrected_verdict: Verdict
    reason: str
    correctness_evidence: list[Reference]
```

### 17.2 Capture Implementations

Each capture implementation under `services/feedback/`:

- Detects a feedback event from a source-specific signal (PR diff, contract finalization, exception approval, audit finding, etc.).
- Constructs a `FeedbackEvent` and submits to `services/feedback/service.py`.
- The service stores the event, links it to the originating evaluation, and triggers analysis.

### 17.3 Subject-Aware Auto-Drafting

`auto_drafter.py` clusters feedback events using subject-specific embedding spaces. A code correction cluster does not mix with a clause-revision cluster. Drafts are generated with subject-specific prompts.

### 17.4 Human Review

All auto-drafted rules go through the existing proposal workflow (`services/proposals/`). They are routed to the owning department's REVIEWERs based on subject kind and scope.

---

## 18. Multilingual and Jurisdiction Patterns

Phase 9 requirement.

### 18.1 Locale-Aware Rules

```python
class LocalizedStatement(BaseModel):
    locale: str           # "ja", "en", "ja-JP", etc.
    statement: str
    translated_at: datetime
    translator: UserRef | None
    review_status: TranslationStatus  # PENDING / APPROVED

class Rule(...):
    statement: str                                    # canonical
    locales: dict[str, LocalizedStatement] = {}      # alternates
```

### 18.2 Locale Consistency Cron

`workers/check_locale_consistency.py` runs daily. For each rule with multiple locales, it runs Gemini to assess semantic equivalence. Divergence beyond a threshold raises `conflict_locale` alerts to the owning department.

### 18.3 Locale-Aware Evaluation

`rule_selector.py` prefers rules whose locale matches the subject's. If only the canonical locale exists, fall back gracefully and tag the verdict as `locale_mismatch=true`.

### 18.4 Jurisdiction Filtering

`scope.jurisdiction` is a list of ISO codes (`["JP"]`, `["US", "EU"]`, `["*"]` for global). The selector filters rules by jurisdiction membership of the subject's `jurisdiction` field.

### 18.5 Frontend i18n

Next.js i18n routing with parallel content. Tailwind RTL support if needed.

---

## 19. Testing

- **Unit tests**: pure logic in `domain/`. No external services. Fast.
- **Integration tests**: spin up docker-compose services in CI. Use `testcontainers-python` if running CI without compose.
- **LLM tests**: never call the real Gemini API in unit tests. Use a mock client. For integration, gate behind an env flag (`RULEREPO_LIVE_LLM=1`).
- **Subject-specific tests**: each `SubjectKind` has dedicated tests under `tests/evaluation/subjects/test_<kind>_subject.py`.
- **Classification tests**: every endpoint that returns classified data must have a test verifying that low-clearance users cannot read high-classification rows.
- **Audit tests**: every action that should be audit-logged must have a test verifying the hash chain integrity after the action.
- **Frontend tests**: Vitest + React Testing Library for components; Playwright for end-to-end if added later.
- **Eval harness**: a separate test suite per domain that validates LLM-driven features (rule extraction quality, conflict detection precision/recall, contract clause classification, event sequence reasoning) against curated fixtures. Runs nightly, not on every PR.

---

## 20. Environment Variables

All env vars live in `.env.example`. Never commit `.env`. Required for local dev:

```
# Core
GEMINI_API_KEY=...
DATABASE_URL=postgresql+asyncpg://rule:rule@postgres:5432/ruledb
ELASTICSEARCH_URL=http://elasticsearch:9200
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=ruledev1
RULEREPO_SERVER_URL=http://server:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO
LLM_DEFAULT_MODEL=gemini-3-flash-preview
LLM_JUDGE_MODEL=gemini-3.1-pro-preview
CORS_ORIGINS=["http://localhost:3000"]
AUTH_REQUIRED=false

# MCP Server
MCP_TRANSPORT=stdio
MCP_PORT=8001

# Redis / Background Workers
REDIS_URL=redis://redis:6379/0

# GitHub Integration
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=

# Discovery
GITHUB_TOKEN=
CONFLUENCE_BASE_URL=
CONFLUENCE_TOKEN=
SHAREPOINT_TENANT=
SHAREPOINT_CLIENT_ID=
NOTION_TOKEN=
GOOGLE_DRIVE_CREDENTIALS=
EGOV_API_KEY=

# Alerts and Notifications
ALERT_WEBHOOK_URL=
DIGEST_WEBHOOK_URL=
NOTIFICATION_WEBHOOK_URL=
NOTIFICATION_WEBHOOK_TYPE=

# Multi-tenancy
DEFAULT_CLASSIFICATION=internal
RLS_ENFORCE=true

# Audit
AUDIT_WORM_BACKEND=                       # disabled in dev; s3|azure|gcs in prod
AUDIT_WORM_BUCKET=
AUDIT_ANCHOR_BACKEND=rekor
AUDIT_ANCHOR_INTERVAL_HOURS=24

# Identity Provider Sync
IDP_TYPE=                                 # okta | azure_ad | google_workspace
IDP_CLIENT_ID=
IDP_CLIENT_SECRET=
IDP_DOMAIN=

# Integrations (per-system)
WORKDAY_TENANT=
WORKDAY_CLIENT_ID=
SAP_BASE_URL=
SMARTHR_TOKEN=
FREEE_HR_TOKEN=
SALESFORCE_DOMAIN=
SALESFORCE_TOKEN=

# LLM Provider (pluggable)
LLM_PROVIDER=gemini                       # gemini | anthropic | openai | self_hosted
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Marketplace
REGISTRY_URL=
REGISTRY_API_KEY=
PACKAGE_AUTO_UPDATE_ENABLED=false

# Agent Governance
AGENT_TRUST_PROMOTION_ENABLED=true
AGENT_MASTERY_THRESHOLD=0.9
AGENT_PATTERN_MIN_EVIDENCE=10
```

When you add a new env var, update `.env.example` in the same change.

---

## 21. Important Rules for Claude Code

These are non-negotiable. Violating them breaks the system or wastes review time.

1. **Read PROJECT.md and IMPROVEMENT.md before designing anything new.** Domain decisions belong there, not here.
2. **Run linters, formatters, and type checkers before claiming a task is done.** `ruff`, `mypy`, `pnpm lint`, `pnpm typecheck`. CI will reject otherwise.
3. **Never commit secrets.** No API keys, no DB passwords, nothing in code. Use `.env` and `.env.example`.
4. **Never tweak Gemini `temperature`.** Default 1.0 stays.
5. **Never use deprecated Gemini params.** Use `thinking_level`, not `thinking_budget`. Use `google-genai`, not `google-generativeai`.
6. **Never bypass the Subject Registry.** All evaluation flows through `subject_registry.resolve(subject_kind)`. No `if subject.kind == ...` branching outside that registry.
7. **Never bypass the extraction pipeline** to call Gemini directly from random services. There is one place per domain that talks to Gemini for ingestion.
8. **Never write to the audit log table from application code.** Only the audit service writes, and only through the audit-log adapter that enforces hash chaining.
9. **Never query data without setting RLS context.** Use `with_user_context()` before every query against classified tables. Direct queries are an access-control bug.
10. **Never make Postgres, Elasticsearch, and Neo4j disagree silently.** If you write to one, write to the others through the same service. Reconcilers exist as scripts, not as runtime escape hatches.
11. **Never delete rules.** Use `effective_period.valid_until` to retire them. Past evaluations must remain re-explainable.
12. **Never delete audit entries.** Even after retention expiry, archive to cold storage with the chain head preserved. Legal hold trumps retention.
13. **Never put domain logic in `evaluation_core.py` or `service.py`.** These are subject-agnostic. Domain logic belongs in `services/evaluation/subjects/`.
14. **Never hardcode model IDs.** Use `core/llm.py` config or the `LLMProvider` interface.
15. **Never hardcode Department or Capacity assumptions.** Use `services/departments/` resolvers.
16. **Never assume a single locale or jurisdiction.** Use `Rule.locales` and `scope.jurisdiction`.
17. **Keep `make up` working.** If your change breaks the local stack, fix it before merging. The local stack is the developer onboarding path.
18. **Update PROJECT.md, CLAUDE.md, and ADRs** when introducing a new dependency, service, or architectural decision. Code without doc updates does not ship.
19. **Prefer fewer dependencies.** Every added library is a long-term cost. Justify additions in the PR description.
20. **Write structured logs, not `print`.** Logs are operational data.
21. **Tests for LLM-driven features must mock the LLM** unless the test is explicitly an eval test.
22. **Tests for classification must verify both directions**: high-clearance users see all data; low-clearance users see only what they should.
23. **When unsure, ask.** Open an issue or a draft PR with the question. Do not guess on domain semantics — wrong rules are worse than no rules.

---

## 22. References

- Gemini 3 developer guide: https://ai.google.dev/gemini-api/docs/gemini-3
- Gemini document processing: https://ai.google.dev/gemini-api/docs/document-processing
- Gemini Files API: https://ai.google.dev/gemini-api/docs/files
- Semantic Governance (conceptual inspiration): https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/policies/configure-semantic-governance
- Sigstore Rekor (transparency log): https://docs.sigstore.dev/logging/overview/
- PostgreSQL Row-Level Security: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Elasticsearch document-level security: https://www.elastic.co/guide/en/elasticsearch/reference/current/document-level-security.html
- uv: https://docs.astral.sh/uv/
- pnpm: https://pnpm.io/
- FastAPI: https://fastapi.tiangolo.com/
- Next.js App Router: https://nextjs.org/docs/app
- Neo4j Python driver: https://neo4j.com/docs/api/python-driver/current/
- arq: https://arq-docs.helpmanual.io/

---

*This file is a contract. If you (Claude Code) find a conflict between this file and the user's request, surface the conflict and ask. Do not silently override.*

# CLAUDE.md

> Operational guide for Claude Code when working on the **Rule Repository** project.
> For the project vision, domain model, and roadmap, see **PROJECT.md**.

This file is the working contract between you (Claude Code) and the project. Read it before making changes. When in doubt, follow the rules in this file over your prior conventions.

**Phase 7 — Enterprise Ground is COMPLETE.** The Rule Repository has been repositioned from "engineering-leaning organizational tool" to "true cross-organization norm management platform" with plugin architecture, multi-tenancy, fact store, eval harness, connector hub, compliance layer, persona UX, and operability. The next focus is **Phase 8 — Vertical Expansion**.

---

## 1. Project at a Glance

The Rule Repository stores natural-language rules across multiple business domains (legal, HR, finance, engineering, marketing, procurement, security) and makes them searchable, evaluable, and enforceable through LLM-assisted services and SDKs. See `PROJECT.md` for the full design.

**This repository is a monorepo** containing the backend server, frontend, Python client SDKs, CLI tools, an MCP server, connectors, and the eval harness. The first deliverable for any new domain is a fully working local stack via **Docker Compose**.

The architecture is layered:

```
┌──────────────────────────────────────────┐
│  Domain-Neutral Core                     │  ← does not know about code, contracts, or HR
│  (Storage, Search, Orchestrator,         │
│   Fact Store, Audit, Tenant, Eval        │
│   Harness, Governance)                   │
├──────────────────────────────────────────┤
│  Domain Plugins                          │  ← engineering, hr, legal, finance, marketing, etc.
│  (Evaluators, Extractors, Prompts,       │
│   Connectors, Persona UX, Golden Sets)   │
├──────────────────────────────────────────┤
│  Integration Surface                     │  ← REST, MCP, CLI, SDKs, Connector webhooks
└──────────────────────────────────────────┘
```

**Layering rule**: dependencies flow downward only. Plugins consume the core; the integration surface consumes both. **The core never imports from any plugin.** This is non-negotiable.

---

## 2. Tech Stack (authoritative)

| Layer | Technology | Notes |
|---|---|---|
| Backend | **Python 3.13** + FastAPI | Library management with **uv** |
| Frontend | **TypeScript**, **React 19**, **Next.js 15**, **Tailwind CSS** | Library management with **pnpm** |
| Python clients | **Python 3.13** (Rule Client, Agentic Rule Client) | Library management with **uv** |
| LLM | **Gemini 3 Flash** (`gemini-3-flash-preview`) and **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`) | via `google-genai` SDK |
| Document parsing / OCR | **Gemini Files API** + document understanding | PDF, text, markdown |
| Relational DB | **PostgreSQL 17** with Row-Level Security | rules, tenants, revisions, audit log |
| Search | **Elasticsearch 8** | full-text + hybrid search |
| Graph DB | **Neo4j 5** | rule relationships |
| Job Queue | **arq** + **Redis 7** | Background tasks |
| Identity | **OIDC**, **SAML 2.0**, **SCIM 2.0** | SSO and provisioning |
| Secrets | Pluggable (Vault, AWS SM, GCP SM) | never `.env` in production |
| Observability | OpenTelemetry, Prometheus, Grafana | exported via OTLP |
| Local orchestration | **Docker Compose** (3 tiers) | Tier 1: PG only; Tier 2: +ES,Redis; Tier 3: +Neo4j,MCP,arq |

Do **not** introduce additional frameworks or services without updating this file and PROJECT.md first.

---

## 3. Repository Layout

The structure reflects the layered architecture: core, plugins, integration, and shared infrastructure are clearly separated.

```
rule-repository/
├── apps/
│   ├── server/                 # FastAPI backend (Python 3.13, uv)
│   │   ├── src/rulerepo_server/
│   │   │   ├── main.py
│   │   │   ├── api/v1/         # REST routers (rules, search, evaluate, intent, intelligence, admin)
│   │   │   ├── core/           # config, logging, errors, auth, middleware, PII, deps, tenant, identity
│   │   │   ├── domain/         # Pure domain objects (Rule, Bundle, Verdict, Tenant, etc.)
│   │   │   ├── services/       # Domain-neutral services (see §7)
│   │   │   ├── plugins/        # Domain plugins (see §15)
│   │   │   │   ├── engineering/
│   │   │   │   ├── hr/
│   │   │   │   ├── legal/
│   │   │   │   ├── finance/
│   │   │   │   └── _registry.py
│   │   │   ├── adapters/       # postgres, elasticsearch, neo4j, gemini, files, vault
│   │   │   ├── mcp/            # MCP server (core tools + plugin-contributed tools)
│   │   │   ├── gateway/        # Webhook enforcement
│   │   │   ├── integrations/   # GitHub App, CI formatters
│   │   │   ├── connectors/     # Business system connectors (HRIS, CRM, ERP, etc.)
│   │   │   ├── schemas/        # Pydantic request/response models
│   │   │   └── workers/        # arq background jobs
│   │   ├── alembic/            # Database migrations
│   │   ├── eval/               # Eval harness (see §17)
│   │   │   ├── datasets/
│   │   │   │   ├── engineering/
│   │   │   │   ├── hr/
│   │   │   │   ├── legal/
│   │   │   │   └── content/
│   │   │   ├── runner.py
│   │   │   ├── reporters/
│   │   │   └── ab_testing/
│   │   └── tests/
│   └── frontend/               # Next.js + TS + Tailwind (pnpm)
│       ├── package.json
│       ├── app/
│       │   ├── (engineering)/  # Engineering persona portal (existing)
│       │   ├── (hr)/           # HR persona portal
│       │   ├── (legal)/        # Legal persona portal
│       │   ├── (compliance)/   # Compliance persona portal
│       │   ├── (security)/     # Security persona portal
│       │   └── (admin)/        # Tenant admin
│       └── components/
├── packages/
│   ├── rule-client/            # Python SDK (thin wrapper over server APIs)
│   ├── agentic-client/         # Python SDK (wraps rule-client + evaluation)
│   ├── cli/                    # CLI tools: rulerepo-check, rulerepo-hook, rulerepo-ingest, rulerepo-export, rulerepo-context, rulerepo-eval
│   └── connectors/             # Connector packages (one directory per connector)
│       ├── hris-workday/
│       ├── hris-smarthr/
│       ├── crm-salesforce/
│       └── ...
├── infra/
│   ├── docker/                 # Dockerfiles
│   ├── postgres/               # init SQL, RLS policies
│   ├── elasticsearch/          # index templates
│   └── neo4j/                  # constraints
├── scripts/                    # seed_data, reconcile_graph, generate_claude_md, eval_run
├── development/                # Internal technical docs
├── docs/                       # mkdocs documentation site (see §8)
├── docker-compose.yml          # Tier 3 (full) by default
├── docker-compose.tier1.yml    # Tier 1 (Postgres only)
├── docker-compose.tier2.yml    # Tier 2 (+ ES, Redis)
├── pyproject.toml              # uv workspace root
├── pnpm-workspace.yaml
├── .env.example
├── PROJECT.md                  # project vision and specification
├── CLAUDE.md                   # this file — operational guide
└── IMPROVEMENT.md              # active improvement backlog
```

When adding a new package, place it under `apps/` (deployable apps), `packages/` (libraries and CLIs), or as a connector under `packages/connectors/`. Update `pyproject.toml` (uv workspace) or `pnpm-workspace.yaml` accordingly.

---

## 4. Quick Start (local dev)

The whole stack must come up with one command at every tier. If your changes break this, fix it before continuing.

```bash
cp .env.example .env            # then fill in GEMINI_API_KEY

# Tier 3 (full) — default
docker compose up --build

# Tier 2 (no Neo4j, no MCP, no arq)
docker compose -f docker-compose.tier2.yml up --build

# Tier 1 (Postgres only — minimal)
docker compose -f docker-compose.tier1.yml up --build
```

Expected services after Tier 3 `up`:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | REST, Intent, Evaluate, Gateway, Admin APIs |
| API docs | http://localhost:8000/docs | OpenAPI / Swagger UI |
| Frontend | http://localhost:3000 | Persona portals |
| PostgreSQL | localhost:5432 | `ruledb`; tenant isolation via RLS |
| Elasticsearch | http://localhost:9200 | Search index |
| Neo4j Browser | http://localhost:7474 | Rule relationship graph |
| MCP Server | http://localhost:8001 | Streamable-HTTP MCP for agents |
| Redis | localhost:6379 | arq job queue |
| arq-worker | — | Background task processor |

The frontend talks to the backend over `NEXT_PUBLIC_API_BASE_URL`. The Python clients talk to the backend over `RULEREPO_SERVER_URL`. All API calls require an authenticated principal except `/healthz` and `/readyz`.

---

## 5. Common Commands

### Backend (apps/server)

```bash
cd apps/server
uv sync                                         # install deps
uv run uvicorn rulerepo_server.main:app --reload   # run dev server
uv run pytest                                   # run tests
uv run ruff check .                             # lint
uv run ruff format .                            # format
uv run mypy src                                 # type check
uv run alembic upgrade head                     # apply migrations
uv run alembic revision --autogenerate -m "..." # create migration
```

### Eval harness

```bash
cd apps/server
uv run python -m eval.runner --domain hr --golden-dataset eval/datasets/hr/v1.yaml
uv run python -m eval.runner --all                    # all domains
uv run python -m eval.ab_testing --variant prompt-v2  # A/B test
```

### Frontend (apps/frontend)

```bash
cd apps/frontend
pnpm install
pnpm dev                        # Next.js dev server
pnpm build && pnpm start
pnpm lint
pnpm test
pnpm typecheck
```

### Python SDKs and CLI

```bash
cd packages/rule-client
uv sync && uv run pytest && uv build

cd packages/cli
uv run rulerepo-check --diff "$(git diff origin/main...HEAD)" --format github-actions
uv run rulerepo-hook preflight --file src/api/handler.py
uv run rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python
uv run rulerepo-eval --domain hr           # run eval harness
```

### MCP Server

```bash
uv run rulerepo-mcp                                     # stdio (local, for Claude Code)
MCP_TRANSPORT=streamable-http uv run rulerepo-mcp       # HTTP (remote agents)
```

### Whole repo (from root)

```bash
docker compose up --build
docker compose down -v
docker compose logs -f server
uv run python -m pytest
make eval                       # run eval harness across all domains
make precommit.install
make check                      # format + lint + test (run before committing)
```

---

## 6. Coding Conventions

### Python (server + clients)

- **Python 3.13**. Use modern syntax: built-in generics (`list[str]`, `dict[str, int]`), `match`/`case` where it improves clarity, `type` statement for type aliases.
- **Type hints are mandatory** on all public functions. mypy must pass on `src/`.
- **Formatter and linter**: `ruff` (both linting and formatting). No `black`, no `isort` (ruff covers both).
- **Naming**: snake_case for functions/vars, PascalCase for classes, SCREAMING_SNAKE_CASE for constants. Module names lowercase.
- **Docstrings**: Google style. Required on all public APIs.
- **Errors**: project-specific exception hierarchy under `rulerepo_server.errors` / `rulerepo.errors`. Never raise bare `Exception`.
- **Logging**: `structlog` with JSON output. Never `print()` outside one-off scripts.
- **Pydantic v2** for all data validation at API boundaries.
- **Tests**: `pytest` + `pytest-asyncio`. Unit tests on pure logic, integration tests against the docker-compose stack, eval tests via the harness.

### TypeScript (frontend)

- **Strict TS**: `"strict": true`. No `any` without justification.
- **App Router** (Next.js 15+ idioms). Server Components by default, Client Components only when needed.
- **Tailwind**: utility classes only; design tokens in `tailwind.config.ts`.
- **State**: Server Components and URL state preferred. For client state, `zustand`. For server-state caching, `@tanstack/react-query`.
- **API calls**: generated TypeScript client from the backend's OpenAPI spec.
- **Linting**: ESLint + Prettier.
- **Persona separation**: each portal lives under `app/(persona)/`; never share Client Components across portals (Server Components are okay).

### Commits / branches

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `perf:`, `ci:`.
- Branch from `main`. Open PRs even for solo work.
- PR description must include: domain affected, plugin or core, eval harness impact (none / regression / improvement).

---

## 7. Backend Architecture Notes

The server is a single FastAPI application. Read this before adding any new module.

### 7.1 Layering

The server enforces strict downward dependencies:

```
api/v1/      ──depends on──▶  services/, plugins/  ──depends on──▶  domain/, adapters/
                              core/                ──depends on──▶  domain/
                                                                   ▲
plugins/<name>/ ──depends on──▶  services/, core/, domain/         │
                                                                   │
adapters/                       ──depends on──▶  domain/  ─────────┘
```

**Rules:**
- `domain/` depends on nothing else in the project
- `core/` depends on `domain/` and `adapters/` only
- `services/` depends on `core/`, `domain/`, `adapters/`
- `plugins/<name>/` depends on `core/`, `domain/`, `services/` (read-only); never on other plugins
- `api/v1/` depends on `services/` and `plugins/` (via the registry)

### 7.2 Internal modules

```
src/rulerepo_server/
├── main.py                     # FastAPI app factory; loads plugins via registry
├── api/v1/                     # Routers
│   ├── rules.py                # CRUD, retire, revisions, relationships, /context
│   ├── search.py               # FT/vector/hybrid/category/context/by-source
│   ├── evaluate.py             # POST /evaluate (dispatches by evaluator_type)
│   ├── intent.py               # NL query routing
│   ├── intelligence.py         # Health, analytics, recommendations
│   ├── admin.py                # Tenant management, RBAC, ABAC policies
│   └── plugin_routes.py        # Mounts plugin-contributed routes under /api/v1/plugins/<name>/
├── core/
│   ├── config.py               # Settings (typed)
│   ├── logging.py              # structlog setup
│   ├── errors.py               # Exception hierarchy
│   ├── auth.py                 # OIDC/SAML/SCIM integration; principal extraction
│   ├── middleware.py           # Tenant resolution, request ID, audit context
│   ├── tenant.py               # Tenant model and resolution
│   ├── identity.py             # User, Group, ServiceAccount, Principal
│   ├── rbac.py                 # Role-based access
│   ├── abac.py                 # Attribute-based access (policy engine)
│   ├── sod.py                  # Segregation of duties enforcement
│   ├── pii.py                  # Data classification, PII redaction
│   └── llm.py                  # Gemini client, model selection, prompt versioning
├── domain/
│   ├── rule.py                 # Rule, MaturityLevel, Modality, etc.
│   ├── bundle.py               # RuleBundle
│   ├── snapshot.py             # Snapshot
│   ├── evaluation.py           # EvaluationContext, Verdict, ReasonGraph, Remediation
│   ├── tenant.py               # Tenant, Organization
│   ├── identity.py             # Principal, Role, ABACPolicy
│   ├── proposal.py             # Proposal, ApprovalVote
│   ├── domain_enum.py          # The Domain enum
│   └── plugin.py               # DomainPlugin protocol; registries
├── services/                   # Domain-neutral services
│   ├── evaluation/
│   │   ├── core/               # Orchestrator (domain-neutral)
│   │   │   ├── orchestrator.py
│   │   │   ├── rule_selector.py
│   │   │   ├── verdict_aggregator.py
│   │   │   ├── batch_evaluator.py
│   │   │   └── persistence.py
│   │   └── prompts/            # Shared prompt templates (rare; usually plugin-owned)
│   ├── extraction/             # Document ingestion pipeline (Gemini-powered)
│   ├── intelligence/           # Health scoring, analytics, recommendations
│   ├── context_delivery/       # Smart rule selection + formatting for agents
│   ├── discovery/              # Generic discovery infrastructure
│   ├── feedback/               # Feedback ingestion and clustering
│   ├── federation/             # Cross-project rule federation
│   ├── playground/             # Rule sandbox + test cases
│   ├── snapshots/              # Rule set versioning + deployment
│   ├── proposals/              # Governance proposals
│   ├── fact_store/             # Fact resolution (see §16)
│   │   ├── service.py
│   │   ├── registry.py
│   │   └── providers/          # Built-in providers
│   ├── search.py
│   ├── rule_service.py
│   └── intent.py
├── plugins/                    # See §15
│   ├── _registry.py            # PluginRegistry (loads plugins at startup)
│   ├── engineering/
│   ├── hr/
│   ├── legal/
│   ├── finance/
│   └── ...
├── connectors/                 # Connector implementations
│   ├── _base.py                # EventSource, Sink protocols
│   ├── hris_workday/
│   ├── hris_smarthr/
│   ├── crm_salesforce/
│   └── ...
├── adapters/                   # postgres, elasticsearch, neo4j, gemini, files, vault, cmek
├── mcp/                        # MCP server (core tools + plugin tools)
├── gateway/                    # Enforcement gateway (normalizers, policies)
├── integrations/               # GitHub webhook, CI formatters
├── workers/                    # arq cron jobs and async tasks
└── schemas/                    # Pydantic request/response models
```

### 7.3 Async

The API layer is fully async. DB calls use `asyncpg` (or `sqlalchemy[asyncio]`), Elasticsearch via the async client, Neo4j via the official async driver, Gemini via `google-genai`. Sync I/O outside one-off scripts is a defect.

### 7.4 Tenant resolution

Every request goes through tenant resolution middleware:

1. `core/auth.py` extracts the authenticated `Principal` from the request
2. `core/middleware.py` reads `Principal.tenant_id` and stores it in the request context
3. SQLAlchemy session is opened with `SET LOCAL app.tenant_id = '<tenant_id>'` so that RLS policies activate
4. Service code may not call `request.body.tenant_id` — the body is for data, not routing

If you find code that derives `tenant_id` from a request body, that is a defect — fix it.

---

## 8. Frontend Notes

The frontend is a multi-persona operator console, not a developer dashboard.

### 8.1 Persona portals

- `app/(engineering)/` — existing UX for engineering managers and individual contributors
- `app/(hr)/` — HR business partners and labor relations managers
- `app/(legal)/` — General Counsel, contract reviewers
- `app/(compliance)/` — Chief Compliance Officer, regulatory affairs
- `app/(security)/` — security engineers, DPO
- `app/(admin)/` — tenant admin, identity, billing

The persona portal is selected based on the user's primary role. Users with multiple roles see a portal switcher.

### 8.2 Shared components

Reusable components live under `components/`. Persona-specific components live under `app/(persona)/_components/`. **Never import a component from another persona's `_components/`** — if it's needed in two persona portals, it goes to `components/`.

### 8.3 Data fetching

Use Server Components for initial data fetch where possible. Switch to Client Components only for interactivity. Use `@tanstack/react-query` for client-state caching of server data.

### 8.4 Graph view

The graph view (Neo4j-backed) renders using `react-flow`. Pick one library and stick with it.

### 8.5 Multi-tenant awareness

The frontend never displays a tenant selector — the tenant is inferred from the authenticated session. Cross-tenant features (Marketplace) explicitly show a "tenant of origin" tag on each item.

---

## 9. Gemini API Integration (read carefully)

The LLM layer is the heart of this system. Get this right.

### 9.1 SDK

- **Use `google-genai`** (the new unified SDK). Do **not** use the deprecated `google-generativeai`.
- Install via uv: `uv add google-genai httpx`.

### 9.2 Models

| Use case | Model ID | Why |
|---|---|---|
| High-throughput, routine (search ranking, simple extraction, classification) | `gemini-3-flash-preview` | fast, cheap |
| High-stakes judgment (rule extraction QC, conflict detection, CRITICAL evaluations) | `gemini-3.1-pro-preview` | strongest reasoning |

Centralize model selection in `core/llm.py`. Never hardcode model IDs in business logic.

### 9.3 Mandatory rules

- **Do NOT change `temperature`** away from the default (1.0). Lower temperatures degrade Gemini 3 reasoning and can cause loops.
- Use **`thinking_level`** (not the legacy `thinking_budget`). Valid: `minimal`, `low`, `medium`, `high`. Default `low` for routine, `high` for judgment.
- For function calling, **thought signatures must be cycled through** every turn. The SDK and standard chat history handle this — do not strip signatures.
- For PDFs, set `media_resolution: "media_resolution_medium"` (560 tokens/page).
- Use **structured output** (`response_mime_type="application/json"` + `response_json_schema`) for any call whose result is parsed. Never regex out fields from free-form LLM text.
- **Consensus voting** for `legal_force=statutory` + `severity=CRITICAL`: send three requests with three prompt variants; require agreement.

### 9.4 Document ingestion (PDF, text, markdown)

- **PDFs**: upload via the **Files API** for documents > a few pages. Files API is free, persists 48 hours, max 50 MB / 1000 pages.
- For small / one-shot PDFs, inline `Part.from_bytes(...)` is fine.
- **Text and markdown**: pass as plain text. Gemini "document understanding" only meaningfully renders PDFs.
- Each PDF page is roughly 258 image tokens; extracted native text is included free.
- **Domain-specific extractors** wrap these calls — do not bypass them. The HR extractor knows the structure of HR handbooks; the Legal extractor knows clause boundaries.

### 9.5 Cost and latency discipline

- Cache LLM responses by `hash(inputs + model + prompt_version + tenant_settings)` in Postgres.
- Invalidate on rule revision; tag cache entries with `tenant_id` for per-tenant invalidation.
- Long-context calls use **context caching**.
- Tier-down models when a tenant approaches budget; queue non-urgent evaluations.

### 9.6 Determinism, audit, and prompt versioning

- Every LLM call that produces a verdict, candidate rule, or relationship suggestion **must** log: tenant_id, principal_id, model ID, prompt version (a content hash), inputs, outputs, latency, timestamp, audit row hash chain.
- Prompts live in `services/<area>/prompts/` (core) or `plugins/<name>/prompts/` (plugin-owned), versioned in git. **No inline prompt strings.**
- Prompt changes go through the eval harness before merging.

### 9.7 Regional routing

Tenant settings determine which Vertex AI region serves the LLM call:

```python
client = get_gemini_client(tenant=current_tenant)  # selects region from tenant.llm_region
```

Never hardcode a region in business logic. The adapter handles regional routing transparently.

---

## 10. Data Layer

### 10.1 PostgreSQL (system of record)

- Stores rules, revisions, source documents, evaluations, audit log, tenants, identities, proposals.
- Migrations: `alembic`. One head per branch; rebase before merging.
- **Row-Level Security is mandatory** on every business table. Policies enforce `tenant_id = current_setting('app.tenant_id')`.
- The audit log table is **append-only**. A trigger rejects updates and deletes. A hash chain column links each row to the previous row.
- **Right-to-erasure** (Phase 7d): logical erasure replaces identifiable fields with placeholder values while preserving the hash chain. Encrypted shadow store holds the original for legally required retention.

### 10.2 Elasticsearch (search)

- Index `rules` with: `statement` (analyzed), `tags`, `scope`, `modality`, `severity`, `legal_force`, `jurisdiction`, `domain`, `effective_period`, `embedding` (dense_vector for hybrid).
- Use BM25 + kNN hybrid scoring. LLM rerank only on user request.
- Re-index on rule revision.
- **Tenant filter is mandatory** on every search query. Helper: `index_with_tenant_filter(es_client, tenant_id, query)`.

### 10.3 Neo4j (relationship graph)

- One node label: `Rule`. Node `id` matches the Postgres rule ID. Node carries `tenant_id` as a property.
- Relationships: `REFINES`, `OVERRIDES`, `CONFLICTS_WITH`, `DEPENDS_ON`, `DERIVES_FROM`, `SUCCEEDS`, `INTERPRETS`, `CITES`, `SUPERSEDES_IN_JURISDICTION`, `APPLIES_WHEN`, `CROSS_REFERENCES`. Direction matters and is documented in PROJECT.md §5.2.
- Postgres is the source of truth; Neo4j is a derived projection. If they disagree, Postgres wins and Neo4j is rebuilt.
- Reconciler script: `scripts/reconcile_graph.py`.
- **All Cypher queries must include a `WHERE node.tenant_id = $tenant_id` clause** — this is enforced by a query wrapper.

### 10.4 Redis (cache and queue)

- Used for arq job queue, evaluation result cache, session cache.
- Cache keys are namespaced by `tenant_id`.
- arq workers use Postgres advisory locks to elect a leader; only the leader runs cron jobs.

---

## 11. Multi-tenancy and Identity

This section is new for Phase 7. Implement carefully.

### 11.1 Tenant model

Every business table carries a non-null `tenant_id` column with a foreign key to `tenants.id`. RLS policy applies on every read and write:

```sql
CREATE POLICY tenant_isolation ON rules
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

The session sets `app.tenant_id` in middleware before any query runs. Code that bypasses this middleware (e.g., admin scripts) must explicitly set the variable.

### 11.2 Authentication

- `core/auth.py` integrates with OIDC and SAML providers
- The `Principal` extracted from a request is either a `User` or `ServiceAccount`
- All principals carry a `tenant_id` derived from the identity provider (claim mapping)
- Multi-tenant users (rare) authenticate to one tenant per session

### 11.3 SCIM provisioning

- `/scim/v2/Users` and `/scim/v2/Groups` endpoints
- Group membership maps to internal `Role` assignments
- Deprovisioning removes user access immediately and creates an audit entry

### 11.4 Authorization

- **RBAC**: `Owner / Approver / Reader` roles per rule category — existing model
- **ABAC**: declarative policies that gate on principal attributes (department, classification level) and resource attributes (rule classification, jurisdiction, domain)
- **SoD**: enforced at the proposal lifecycle level — author ≠ approver ≠ enactor

### 11.5 Service accounts and API keys

- Service accounts are tenant-scoped
- API keys have explicit capabilities (e.g., `rules:read`, `evaluate:submit`)
- Keys rotate every 90 days; CI integrations are notified before expiration

### 11.6 Tenant settings

Each tenant has settings for:
- Data residency (which Postgres region)
- LLM region (which Vertex AI region for Gemini)
- Encryption key (CMEK reference, if used)
- LLM budget (monthly soft and hard limits)
- Active plugins (which domain plugins are enabled)
- Connector configuration (which connectors are active, with credentials)

### 11.7 Migration to multi-tenant

For existing single-tenant deployments:

1. Create a default tenant (`00000000-0000-0000-0000-000000000001`)
2. Backfill `tenant_id` on all existing rows
3. Apply RLS policies
4. Wire authentication; set `AUTH_REQUIRED=true` in production
5. Migrate existing API keys to service accounts under the default tenant

---

## 12. Pluggable Evaluator Architecture

This section is new for Phase 7. The single most important refactor in this phase.

### 12.1 The Evaluator protocol

```python
from typing import Protocol
from rulerepo_server.domain.evaluation import EvaluationContext, Verdict
from rulerepo_server.domain.rule import Rule

class Evaluator(Protocol):
    name: str
    domain: Domain
    supported_input_types: list[str]

    async def evaluate(
        self,
        context: EvaluationContext,
        rules: list[Rule],
        facts: dict[str, Any],
        config: EvaluatorConfig,
    ) -> EvaluationResult: ...

    async def golden_dataset(self) -> GoldenDataset: ...

    def prompt_version(self) -> str: ...
```

### 12.2 Existing code-aware evaluator

The current `services/evaluation/evaluation_core.py` becomes `plugins/engineering/evaluators/code_change_evaluator.py`. The orchestrator loses its code-specific knowledge.

**Steps:**

1. Create `plugins/engineering/` package and register it via `_registry.py`
2. Move `diff_parser.py`, `context_assembler.py` (code-specific parts), `evaluation_core.py` to `plugins/engineering/evaluators/code_change_evaluator.py`
3. Keep `rule_selector.py` and `verdict_aggregator.py` in `services/evaluation/core/`
4. Generalize `EvaluationContext` to accept any payload, not just `FileChange`
5. Add `evaluator_type` parameter to `POST /api/v1/evaluate`; default to `code_change` for backwards compatibility
6. Update the API to dispatch to the registered evaluator by `evaluator_type`

### 12.3 New evaluator implementations (Phase 7 scope)

| Evaluator | Plugin | Module |
|---|---|---|
| `code_change` | engineering | `plugins/engineering/evaluators/code_change_evaluator.py` |
| `document` | legal, hr | `plugins/legal/evaluators/document_evaluator.py`, `plugins/hr/evaluators/handbook_evaluator.py` |
| `form` | hr, finance | `plugins/hr/evaluators/form_evaluator.py` |
| `factual_query` | core | `services/evaluation/evaluators/factual_query_evaluator.py` |

`content`, `transaction`, and `conversation` evaluators are Phase 8.

### 12.4 Backwards compatibility

API endpoints without an explicit `evaluator_type` default to `code_change`. CLI tools default to `code_change` unless overridden. This preserves all existing CI integrations during the migration.

### 12.5 Evaluator registration

Plugins register evaluators in their `register_evaluators` method:

```python
# plugins/hr/__init__.py
def register_evaluators(self, registry: EvaluatorRegistry) -> None:
    registry.register("form", FormEvaluator())
    registry.register("handbook_document", HandbookDocumentEvaluator())
```

The registry rejects duplicate `evaluator_type` registrations across plugins.

---

## 13. Important Rules for Claude Code

These are non-negotiable. Violating them breaks the system or wastes review time.

1. **Read PROJECT.md before designing anything new.** Domain decisions belong there, not here.
2. **Run linters, formatters, type checkers, and the eval harness before claiming a task is done.** `ruff`, `mypy`, `pnpm lint`, `pnpm typecheck`, plus `make eval` if you touched any prompt or evaluator. CI rejects otherwise.
3. **Never commit secrets.** No API keys, no DB passwords, nothing in code. Use `.env` (dev) and the configured secrets manager (production).
4. **Never tweak Gemini `temperature`.** Default 1.0 stays.
5. **Never use deprecated Gemini params.** Use `thinking_level`, not `thinking_budget`. Use `google-genai`, not `google-generativeai`.
6. **Never call Gemini outside the core.** Plugins request prompts and models through `core/llm.py`; never instantiate a Gemini client directly.
7. **Never write to the audit log table from application code.** Only the evaluation/extraction services write, and only through the audit-log adapter that enforces hash chaining.
8. **Never make Postgres, Neo4j, and Elasticsearch disagree silently.** If you write to one, write to all relevant ones through the same service. If you can only write to one, queue the others.
9. **Never delete rules.** Use `effective_period.valid_until` to retire them. Past evaluations must remain re-explainable.
10. **Keep `docker compose up --build` working at every tier.** If your change breaks any tier, fix it before merging.
11. **Update both `PROJECT.md` and `CLAUDE.md`** when introducing a new dependency, service, plugin, or architectural decision. Code without doc updates does not ship.
12. **Prefer fewer dependencies.** Every added library is a long-term cost. Justify additions in the PR description.
13. **Write structured logs, not `print`.** Logs are operational data.
14. **Tests for LLM-driven features must mock the LLM** unless the test is explicitly an eval test. Eval tests gate on the harness.
15. **When unsure, ask.** Open an issue or a draft PR. Do not guess on domain semantics — wrong rules are worse than no rules.
16. **The core never imports from plugins.** This is non-negotiable. If you find yourself wanting to, the abstraction is wrong; fix the abstraction.
17. **All business tables carry `tenant_id`.** A migration that adds a business table without `tenant_id` is a defect. RLS policy is mandatory.
18. **Tenant ID comes from the authenticated principal, never from the request body.** Code that derives `tenant_id` from request data is a security defect.
19. **No new domain plugin ships without a golden dataset.** A new plugin without an `eval/datasets/<domain>/v1.yaml` and baseline metrics is not approved for merge.
20. **No prompt change merges without an eval harness regression run.** The PR description must show the eval delta. Regression of >2 percentage points blocks the merge.
21. **PII redaction happens before LLM transmission.** Code that sends a `Principal` or `Employee` object into a prompt without going through `core/pii.redact()` is a security defect.
22. **Plugin-contributed routes mount under `/api/v1/plugins/<name>/`.** Core routes are stable; plugin routes are versioned independently.
23. **Connector credentials are stored in the configured secrets manager, never in `tenant_settings`.** The settings table holds references, not secrets.

---

## 14. Phase 7 Implementation Guidance

This section is the working playbook for Phase 7 — Enterprise Ground. Each subsection corresponds to a workstream in PROJECT.md §10.

### 14.1 7e: Eval Harness scaffolding (do first)

**Goal:** every prompt and model change has measurable impact before merging.

**Steps:**

1. Create `apps/server/eval/` with subdirectories: `datasets/`, `runner.py`, `reporters/`, `ab_testing/`
2. Define golden dataset format (YAML or JSONL) with fields: `id`, `domain`, `evaluator_type`, `input`, `applicable_rule_ids`, `expected_verdict`, `expected_violations`, `notes`
3. Build `runner.py` that:
   - Loads a golden dataset
   - Runs the current evaluator against each case (with a real LLM, gated by `RULEREPO_LIVE_LLM=1`)
   - Compares actual vs expected
   - Reports precision, recall, F1, per-case verdicts
4. Build `reporters/` for stdout, JSON, and Markdown formats
5. Build `ab_testing/` for routing a configured percentage of traffic to a candidate prompt
6. Add `make eval` and `uv run rulerepo-eval` entry points
7. Wire CI to run a smoke subset of the harness on every PR; full harness nightly

**Deliverable:** baseline scores for engineering golden dataset (50 cases, hand-labeled).

### 14.2 7b1: Evaluator Plugin Architecture

**Goal:** the evaluation core knows nothing about code, contracts, or HR.

**Steps:**

1. Create `domain/plugin.py` with `DomainPlugin` protocol, `Evaluator` protocol, `EvaluatorRegistry`
2. Create `plugins/_registry.py` with `PluginRegistry` that loads plugins at startup
3. Create `plugins/engineering/` and move existing code-aware logic there
4. Refactor `services/evaluation/` into `core/` (orchestrator, selector, aggregator) and remove code-specific imports
5. Update `POST /api/v1/evaluate` to dispatch by `evaluator_type` (default: `code_change`)
6. Verify all existing tests pass; existing CI integrations continue to work

**Deliverable:** core evaluation orchestrator has zero references to `diff`, `file_path`, or any other code-specific concept.

### 14.3 7a: Multi-Tenancy and Identity

**Goal:** tenant isolation by construction, not by convention.

**Steps:**

1. Create `Tenant`, `Organization`, `User`, `Group`, `ServiceAccount`, `Principal` domain models
2. Add `tenant_id` column to every business table; backfill with default tenant
3. Apply RLS policies on every business table
4. Wire OIDC (Google, Microsoft Entra, generic) and SAML in `core/auth.py`
5. Implement SCIM endpoints under `/scim/v2/`
6. Build ABAC policy engine in `core/abac.py`; load policies from a versioned table
7. Enforce SoD in `services/proposals/`
8. Add per-tenant settings: data residency, LLM region, encryption key, LLM budget, active plugins, connectors
9. Update `core/middleware.py` to set `app.tenant_id` per request
10. Test cross-tenant access (must return 404 or 403, never leak data)

**Deliverable:** a multi-tenant test suite that verifies isolation at every layer.

### 14.4 7c: Fact Store

**Goal:** rules can declare facts they need; the system resolves them at evaluation time.

**Steps:**

1. Create `services/fact_store/` with `service.py`, `registry.py`, `providers/`
2. Define `FactProvider` protocol and `Fact` domain model
3. Add `external_facts_required` column to `Rule` (migration)
4. Wire the orchestrator to call `fact_store.resolve(rule.external_facts_required, context)` between Rule Selection and Evaluator Dispatch
5. Implement initial providers:
   - `EmployeeAttributesProvider` (reads from a local table populated by HRIS sync)
   - `OFACSanctionsProvider` (HTTP-fetched JSON, daily refresh)
   - `InternalMasterDataProvider` (generic key-value tenant master data)
6. Add per-tenant provider configuration in tenant settings
7. Cache facts with TTL declared by the provider; tag cache by `tenant_id`

**Deliverable:** an HR rule that depends on `36_agreement_status(employee_id, month)` evaluates correctly end-to-end.

### 14.5 7b2: HR/Labor Vertical Deep-Dive

**Goal:** HR is a fully supported domain end-to-end.

**Steps:**

1. Add `domain` enum to `Rule` (migration); backfill all existing rules to `domain="engineering"`
2. Create `plugins/hr/` package with:
   - `evaluators/form_evaluator.py` (employee form input → verdict)
   - `evaluators/handbook_document_evaluator.py` (document evaluation)
   - `extractors/handbook_extractor.py` (HR handbook PDF → candidate rules)
   - `prompts/` (HR-specific prompt templates)
   - `golden_dataset/v1.yaml` (100 hand-labeled cases)
3. Build `EmployeeAttributesProvider` (Fact Store, §14.4)
4. Build the first HRIS connector under `connectors/hris_<vendor>/` (start with SmartHR or freee 人事労務 for JP focus, or Workday for international)
5. Build the HR persona portal under `app/(hr)/`:
   - Attendance compliance dashboard
   - Employee fact viewer (with PII gating)
   - Policy clarification queue
   - HRIS connection status
6. Add HR-specific MCP tools: `evaluate_attendance`, `lookup_hr_rule`
7. Run the eval harness; require ≥0.80 F1 before considering HR plugin "stable"

**Deliverable:** a working HR demo that ingests a handbook PDF, registers attendance for an employee, and produces a compliant or non-compliant verdict.

### 14.6 7g: Persona-Driven UX

**Goal:** Legal, HR, Compliance, and Security teams see a system designed for them.

**Steps:**

1. Define persona-to-portal routing in `app/layout.tsx` based on the user's primary role
2. Build portal scaffolds: `(legal)`, `(hr)`, `(compliance)`, `(security)`, plus `(admin)` for tenant administration
3. For Phase 7, build out the HR portal end-to-end (other portals can be scaffolded with stubs)
4. Add a portal switcher for users with multiple roles
5. Ensure each portal has its own navigation, and never imports Client Components from other portals' `_components/`

**Deliverable:** a user with role `hr_business_partner` lands on the HR portal by default; never sees engineering-specific UI.

### 14.7 7f: Connector Hub

**Goal:** rules are evaluated where work happens.

**Steps:**

1. Create `services/connectors/_base.py` with `EventSource` and `Sink` protocols
2. Build the first three connectors:
   - HRIS: SmartHR or Workday
   - CRM: Salesforce
   - ERP: SAP S/4 or freee 会計
3. Each connector lives in `packages/connectors/<vendor>/` as a separately versioned package
4. Implement per-tenant connector configuration with credential management (via secrets manager)
5. Build connector health dashboard in the admin portal
6. Wire connectors to the evaluation pipeline as `EventSource`s and to the notification pipeline as `Sink`s

**Deliverable:** an HRIS event (overtime registration) automatically triggers a preflight evaluation, with the verdict written back as a sink action.

### 14.8 7d: Compliance and Privacy Layer

**Goal:** regulated industries can deploy confidently.

**Steps:**

1. Build `core/pii.py` with `Classification` enum (`public`, `internal`, `confidential`, `pii`, `pii_special`) and `redact()` function
2. Add classification tags to every Pydantic schema field; mypy enforces presence on PII-bearing models
3. Wire `redact()` into the LLM call path (between context assembly and prompt formatting)
4. Build a separate encrypted store for original PII values, indexed by `redaction_id`
5. Build the right-to-erasure API: `DELETE /api/v1/data-subjects/{id}` performs logical deletion preserving the hash chain
6. Add per-tenant regional routing: `core/llm.py` selects Vertex AI region based on `tenant.llm_region`
7. Integrate CMEK with the configured cloud provider
8. Build the Approval Policy DSL for category-aware approval requirements
9. Add Mandatory Consultation roles (e.g., DPO for PII rules)

**Deliverable:** EU tenants can configure EU-only data processing; right-to-erasure works end-to-end without breaking the audit hash chain.

### 14.9 7h: Operability

**Goal:** production-grade operations.

**Steps:**

1. Wire OpenTelemetry instrumentation into all service-to-service calls, DB queries, and LLM calls
2. Export metrics to OTLP and a Prometheus-compatible `/metrics` endpoint
3. Tag every LLM call with model, tokens, latency, cost
4. Build per-tenant cost dashboard
5. Implement worker leader election (Postgres advisory lock claimed at arq startup)
6. Define LLM fallback strategy: cached + `stale=true` for non-CRITICAL outages; queued + `NEEDS_CONFIRMATION` for CRITICAL
7. Document and automate backup: Postgres WAL archiving, audit log mirroring to WORM storage, ES snapshots, Neo4j dumps
8. Quarterly DR drill runbook

**Deliverable:** SLO dashboard shows p95 latency, availability, and cost per tenant.

### 14.10 Sequencing

Do not pursue all eight in parallel. Follow this order:

- **Quarter 1**: 7e (Eval Harness), 7b1 (Evaluator Plugin)
- **Quarter 2**: 7a (Multi-Tenancy), 7c (Fact Store)
- **Quarter 3**: 7b2 (HR Vertical), 7g (Persona UX for HR)
- **Quarter 4**: 7f (Connectors, 3 reference), 7d (Privacy Layer), 7h (Operability)

If reality forces a re-prioritization, document it in `docs/09_changelog/` with rationale.

---

## 15. Plugin Authoring Guide

This is reference material for adding a new domain plugin.

### 15.1 Directory layout

```
plugins/<name>/
├── __init__.py             # exports the DomainPlugin instance
├── plugin.py               # implements DomainPlugin protocol
├── evaluators/
│   ├── __init__.py
│   └── <type>_evaluator.py
├── extractors/
│   └── __init__.py
├── feedback_sources/
│   └── __init__.py
├── fact_providers/
│   └── __init__.py
├── prompts/
│   └── *.txt
├── routes.py               # plugin-contributed API routes (mounted under /api/v1/plugins/<name>/)
├── mcp_tools.py            # plugin-contributed MCP tools
├── persona_views/          # frontend integration descriptors
├── golden_dataset/
│   └── v1.yaml
└── README.md               # plugin-specific notes
```

### 15.2 Required components

A plugin is approved for production deployment only when it has:

- At least one Evaluator with prompts and structured output schema
- At least one Extractor (or explicit declaration that none is needed)
- A golden dataset (`golden_dataset/v1.yaml`) with ≥50 cases
- Eval harness baseline scores (precision, recall, F1) ≥ targets in PROJECT.md §11.2
- A persona view (or shared view if the plugin doesn't warrant its own portal)
- Tests: unit tests for pure logic, integration tests against the docker-compose stack
- Documentation in `docs/04_use_cases/<name>/`

### 15.3 Plugin contract versioning

The `DomainPlugin` protocol is versioned. Plugins declare the protocol version they target:

```python
class HRPlugin(DomainPlugin):
    plugin_protocol_version = "1.0"
```

The core rejects plugins that target an incompatible protocol version. Protocol changes follow semantic versioning; minor version bumps are backwards-compatible.

---

## 16. Fact Store Authoring Guide

### 16.1 Implementing a Fact Provider

```python
from rulerepo_server.services.fact_store import FactProvider, Fact, FactSchema
from rulerepo_server.domain.tenant import Tenant

class EmployeeAttributesProvider:
    name = "employee_attributes"
    domain = Domain.HR

    async def supported_facts(self) -> list[FactSchema]:
        return [
            FactSchema("employee_grade", "(employee_id: str, date: str) -> str"),
            FactSchema("employment_type", "(employee_id: str) -> str"),
            FactSchema("36_agreement_status", "(employee_id: str, month: str) -> bool"),
        ]

    async def fetch(self, key: str, context: dict) -> Fact | None:
        tenant: Tenant = context["tenant"]
        # ... query the HRIS sync table for this tenant ...
        return Fact(value=..., source="hris_sync", fetched_at=...)

    async def health_check(self) -> bool:
        # ... ping the underlying source ...
        return True
```

### 16.2 Caching

Providers may declare TTL:

```python
async def fetch(self, key: str, context: dict) -> Fact | None:
    fact = ...
    fact.ttl_seconds = 3600  # cache for 1 hour
    return fact
```

The Fact Store handles caching transparently.

### 16.3 Tenant scoping

Every `fetch()` call receives the active `Tenant` in context. Providers must respect tenant boundaries — a provider that returns data from the wrong tenant is a security defect.

---

## 17. Eval Harness Authoring Guide

### 17.1 Golden dataset format

```yaml
version: 1
domain: hr
evaluator_type: form
description: "HR overtime registration verdicts"
cases:
  - id: hr-001
    input:
      employee_id: "E001"
      month: "2025-04"
      overtime_hours: 50
    facts:
      36_agreement_status: false
      employee_grade: "junior"
    applicable_rule_ids:
      - "rule_hr_overtime_45_limit"
    expected_verdict: DENY
    expected_violations:
      - rule_id: "rule_hr_overtime_45_limit"
        reason_substring: "exceeds 45-hour limit"
    notes: "Standard junior employee without 36-agreement"
  - id: hr-002
    input: ...
```

### 17.2 Running the harness

```bash
uv run python -m eval.runner --domain hr --dataset eval/datasets/hr/v1.yaml
```

Output:

```
HR golden dataset (50 cases)
  Precision: 0.86
  Recall:    0.82
  F1:        0.84

  Per-case results: 43 passed, 7 failed
  Failed cases: hr-007, hr-013, hr-022, hr-031, hr-035, hr-041, hr-049

  Latency: p50 1.2s, p95 2.8s, p99 4.1s
  Cost:    $0.18 total, $0.0036 per case
```

### 17.3 CI integration

- **Per-PR**: run a smoke subset (10 cases per affected domain) to verify no regression
- **Nightly**: run the full harness; alert on F1 drop >2pp
- **A/B tests**: separate runs comparing variants side-by-side

### 17.4 Quality gates

| Gate | Threshold |
|---|---|
| New plugin merged | F1 ≥ 0.80 on its golden dataset |
| Prompt change merged | No regression of >2pp on any domain |
| Model upgrade merged | No regression of >5pp on any domain |
| New domain plugin "stable" status | F1 ≥ 0.85 sustained for 60 days |

---

## 18. Testing

- **Unit tests**: pure logic in `domain/`. No external services. Fast.
- **Integration tests**: spin up docker-compose services in CI. Use `testcontainers-python` if running in CI without compose.
- **LLM tests**: never call the real Gemini API in unit tests. Use a mock client. For integration, gate behind an env flag (`RULEREPO_LIVE_LLM=1`).
- **Eval tests**: run via the eval harness, gated on golden datasets. Block merges on regression.
- **Frontend tests**: Vitest + React Testing Library for components; Playwright for end-to-end if added.
- **Multi-tenant tests**: explicit tests verifying that one tenant cannot read or modify another tenant's data via any API path. These are mandatory for any change touching data access.
- **PII redaction tests**: explicit tests verifying that PII fields are redacted before LLM transmission and audit log persistence.

---

## 19. Environment Variables

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

# Identity
AUTH_REQUIRED=true                    # production: true; local dev: false acceptable
OIDC_ISSUER=...
OIDC_CLIENT_ID=...
OIDC_CLIENT_SECRET=...
SAML_METADATA_URL=...
SCIM_BEARER_TOKEN=...

# Multi-tenancy
DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000001  # for migration only
TENANT_ISOLATION_MODE=rls             # rls | schema | strict

# Secrets management
SECRETS_PROVIDER=env                  # env | vault | aws_sm | gcp_sm
VAULT_ADDR=...                        # if SECRETS_PROVIDER=vault

# Fact Store
FACT_STORE_PROVIDERS=employee_attributes,ofac_sanctions,internal_master

# MCP Server
MCP_TRANSPORT=stdio
MCP_PORT=8001

# Redis / Background Workers
REDIS_URL=redis://redis:6379/0
WORKER_LEADER_LOCK_KEY=rulerepo_worker_leader

# GitHub Integration
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=

# Discovery
GITHUB_TOKEN=                         # for PR comment analysis

# Alerts and notifications
ALERT_WEBHOOK_URL=
DIGEST_WEBHOOK_URL=
NOTIFICATION_WEBHOOK_URL=

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=
PROMETHEUS_METRICS_ENABLED=true

# Eval harness
RULEREPO_LIVE_LLM=0                   # 1 to enable real Gemini in integration tests
EVAL_HARNESS_NIGHTLY_ENABLED=true

# CMEK (production)
CMEK_PROVIDER=                        # gcp_kms | aws_kms | none
CMEK_KEY_REF=

# Rate limits and budgets
PER_TENANT_LLM_BUDGET_DEFAULT_USD=1000
```

When you add a new env var, update `.env.example` in the same change.

---

## 20. Documentation Structure

The repository's documentation is split into focused sections:

```
docs/
├── 01_vision/              # Stable vision (PROJECT.md §1–3)
├── 02_concepts/            # Domain model, terminology, design principles
├── 03_personas/            # Per-persona getting-started guides
│   ├── legal.md
│   ├── hr.md
│   ├── compliance.md
│   ├── security.md
│   └── engineering.md
├── 04_use_cases/           # Per-domain deep dives
│   ├── hr_attendance.md
│   ├── contract_review.md
│   ├── regulatory_compliance.md
│   └── coding_standards.md
├── 05_architecture/        # Technical architecture, data flow, ADRs
├── 06_operations/          # Deployment, backup, monitoring, DR
├── 07_api/                 # OpenAPI reference, MCP reference, SDK guides
├── 08_governance/          # Approval policies, SoD, RBAC/ABAC design
└── 09_changelog/           # Phase implementation history
```

`PROJECT.md` and `CLAUDE.md` are the entry points. Both should remain focused and stable.

---

## 21. References

- Gemini 3 developer guide: https://ai.google.dev/gemini-api/docs/gemini-3
- Gemini document processing: https://ai.google.dev/gemini-api/docs/document-processing
- Gemini Files API: https://ai.google.dev/gemini-api/docs/files
- Semantic Governance (conceptual inspiration): https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/policies/configure-semantic-governance
- uv: https://docs.astral.sh/uv/
- pnpm: https://pnpm.io/
- FastAPI: https://fastapi.tiangolo.com/
- Next.js App Router: https://nextjs.org/docs/app
- Neo4j Python driver: https://neo4j.com/docs/api/python-driver/current/
- Elasticsearch Python client: https://elasticsearch-py.readthedocs.io/
- PostgreSQL Row-Level Security: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- SCIM 2.0: https://datatracker.ietf.org/doc/html/rfc7643
- OpenTelemetry: https://opentelemetry.io/

---

*This file is a contract. If you (Claude Code) find a conflict between this file and the user's request, surface the conflict and ask. Do not silently override.*

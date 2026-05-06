# CLAUDE.md

> Operational guide for Claude Code when working on the **Rule Repository** project.
> For the project vision, domain model, and roadmap, see **PROJECT.md**.
> For the analysis that motivated the current improvement work, see **IMPROVEMENT.md**.

This file is the working contract between you (Claude Code) and the project. Read it before making changes. When in doubt, follow the rules in this file over your prior conventions.

---

## 1. Project at a Glance

The Rule Repository stores natural-language rules across multiple domains (laws, contracts, internal policies, engineering rules, communication standards, documentation conventions) and makes them searchable, evaluable, and enforceable through LLM-assisted services and SDKs.

**This repository is a monorepo** containing the backend server, frontend, Python client SDKs, the unified CLI, and local dev infrastructure. The first-class deliverable is a fully working local stack via **Docker Compose**.

**Active development phase**: the project recently completed an aggressive expansion (Phases 1 through 6). The current 90-day priority is **stabilization and domain expansion**, organized in five tiers (see §15). Significant new feature work is on hold during Tier 0 (Stabilization). Read §15 before opening any PR.

---

## 2. Tech Stack (authoritative)

| Layer | Technology | Notes |
|---|---|---|
| Backend | **Python 3.13** + FastAPI | Library management with **uv** |
| Frontend | **TypeScript**, **React 19**, **Next.js 15**, **Tailwind CSS** | Library management with **pnpm** |
| Python clients | **Python 3.13** (Rule Client, Agentic Rule Client) | Library management with **uv** |
| LLM (default) | **Gemini 3 Flash** (`gemini-3-flash-preview`) and **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`) | via `google-genai` SDK |
| LLM (planned) | **Anthropic Claude**, **OpenAI GPT**, **vLLM/Ollama** (self-hosted) | Behind `LLMProvider` Protocol |
| Document parsing / OCR | **Gemini Files API** + document understanding | PDF, text, markdown |
| Relational DB | **PostgreSQL 17** with **Row-Level Security** | Rules, revisions, audit log, evaluations, governance |
| Search | **Elasticsearch 8.17** | Full-text + dense_vector hybrid search; `routing` for tenant isolation |
| Graph DB | **Neo4j 5** with **multi-database** | Rule relationships and federation; one database per tenant |
| Job Queue | **arq** + **Redis 7** | Background tasks |
| Object storage | **S3-compatible** (MinIO local, S3/GCS prod) | Source documents, archived evaluations, audit-log WORM |
| Tracing/metrics | **OpenTelemetry** → OTLP → **Jaeger** + **Prometheus** | [PARTIAL] (OTel instrumentation IMPLEMENTED; Jaeger/Prometheus services PLANNED) |
| MCP | **FastMCP** (mcp >= 1.9) | 12 tools |
| Local orchestration | **Docker Compose** | Dev + integration tests |

Do **not** introduce additional frameworks or services without updating this file and PROJECT.md first.

---

## 3. Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                              # FastAPI backend (Python 3.13, uv)
│   │   ├── pyproject.toml
│   │   ├── src/rulerepo_server/
│   │   │   ├── main.py                      # FastAPI app factory
│   │   │   ├── api/v1/                      # 18+ routers
│   │   │   ├── core/                        # config, logging, errors, auth, middleware
│   │   │   │   ├── pii/                     # PII tokenizer (IMPLEMENTED)
│   │   │   │   ├── tenancy/                 # tenant context (PLANNED)
│   │   │   │   ├── telemetry.py             # OpenTelemetry setup (IMPLEMENTED)
│   │   │   │   └── llm.py                   # provider routing
│   │   │   ├── domain/                      # pure domain objects
│   │   │   │   ├── rule.py
│   │   │   │   ├── evaluation.py
│   │   │   │   ├── verdict.py
│   │   │   │   ├── subject.py               # Subject, SubjectFilter (IMPLEMENTED)
│   │   │   │   ├── contract.py              # ContractScope, ContractType (IMPLEMENTED)
│   │   │   │   └── proposal.py
│   │   │   ├── services/
│   │   │   │   ├── evaluation/
│   │   │   │   │   ├── service.py           # Domain-agnostic orchestrator
│   │   │   │   │   ├── adapters/            # NEW: domain adapters (Tier 1)
│   │   │   │   │   │   ├── base.py          # EvaluationDomainAdapter Protocol
│   │   │   │   │   │   ├── code/            # Existing logic relocated here
│   │   │   │   │   │   ├── business_event/  # IMPLEMENTED
│   │   │   │   │   │   ├── document_diff/   # IMPLEMENTED
│   │   │   │   │   │   ├── communication/   # IMPLEMENTED
│   │   │   │   │   │   └── documentation/   # IMPLEMENTED
│   │   │   │   │   ├── consensus.py         # IMPLEMENTED
│   │   │   │   │   ├── batch_evaluator.py
│   │   │   │   │   ├── evaluation_core.py
│   │   │   │   │   ├── rule_selector.py
│   │   │   │   │   ├── graph_resolver.py
│   │   │   │   │   ├── conflict_aggregator.py
│   │   │   │   │   ├── verdict_aggregator.py
│   │   │   │   │   ├── impact_preview.py
│   │   │   │   │   └── idempotency.py       # IMPLEMENTED
│   │   │   │   ├── extraction/
│   │   │   │   │   ├── pipeline.py
│   │   │   │   │   ├── pdf_sanitizer.py     # PLANNED
│   │   │   │   │   └── contract/            # IMPLEMENTED (segmenter, classifier, resolver)
│   │   │   │   ├── intelligence/
│   │   │   │   ├── context_delivery/
│   │   │   │   ├── discovery/
│   │   │   │   │   ├── service.py
│   │   │   │   │   ├── github_importer.py
│   │   │   │   │   ├── analyzers/
│   │   │   │   │   └── connectors/          # PARTIAL (Confluence, Notion, e-Gov, EUR-Lex IMPLEMENTED)
│   │   │   │   │       ├── confluence.py
│   │   │   │   │       ├── notion.py
│   │   │   │   │       ├── egov.py
│   │   │   │   │       └── eurlex.py
│   │   │   │   ├── feedback/
│   │   │   │   ├── federation/
│   │   │   │   ├── playground/
│   │   │   │   │   ├── service.py
│   │   │   │   │   ├── test_runner.py
│   │   │   │   │   ├── test_generator.py
│   │   │   │   │   └── counterexample_generator.py  # IMPLEMENTED
│   │   │   │   ├── snapshots/
│   │   │   │   ├── proposals/
│   │   │   │   ├── agent_governance/
│   │   │   │   ├── provenance/              # IMPLEMENTED (lineage_resolver, why_api, basis_type edge)
│   │   │   │   │   ├── lineage_resolver.py
│   │   │   │   │   └── why_api.py
│   │   │   │   ├── polyglot/                # PLANNED Tier 4
│   │   │   │   ├── search.py
│   │   │   │   ├── rule_service.py
│   │   │   │   └── intent.py
│   │   │   ├── adapters/                    # External system adapters
│   │   │   │   ├── postgres/
│   │   │   │   ├── elasticsearch/
│   │   │   │   ├── neo4j/
│   │   │   │   ├── redis/
│   │   │   │   ├── s3/                      # PLANNED Tier 3
│   │   │   │   └── llm/
│   │   │   │       ├── base.py              # LLMProvider Protocol
│   │   │   │       ├── gemini.py
│   │   │   │       ├── anthropic.py         # IMPLEMENTED
│   │   │   │       ├── openai.py            # IMPLEMENTED
│   │   │   │       └── local.py             # IMPLEMENTED
│   │   │   ├── mcp/                         # MCP server
│   │   │   ├── gateway/
│   │   │   ├── integrations/
│   │   │   ├── workers/                     # arq cron jobs
│   │   │   │   ├── settings.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── conflict_scanner.py      # IMPLEMENTED
│   │   │   │   ├── archival.py              # IMPLEMENTED
│   │   │   │   ├── policy_review_cycle.py   # PLANNED Tier 2
│   │   │   │   ├── verdict_drift.py         # IMPLEMENTED
│   │   │   │   └── polyglot_validator.py    # IMPLEMENTED
│   │   │   └── schemas/
│   │   ├── alembic/                         # 22+ migrations
│   │   └── tests/
│   │       ├── unit/
│   │       ├── integration/
│   │       │   └── feature_matrix/          # NEW Tier 0
│   │       ├── e2e/                         # PLANNED Tier 3 (Playwright)
│   │       └── eval_harness/                # PLANNED Tier 3
│   │           ├── golden/
│   │           ├── runner.py
│   │           └── README.md
│   └── frontend/                            # Next.js + TS + Tailwind
│       ├── package.json
│       ├── app/
│       │   └── (dashboard)/                 # 23+ pages
│       └── components/
├── packages/
│   ├── rule-client/                         # Python SDK
│   ├── agentic-client/                      # Python SDK (wraps rule-client)
│   └── cli/                                 # UNIFIED rulerepo CLI
│       └── src/rulerepo_cli/
│           ├── main.py                      # Typer/Click root
│           ├── commands/
│           │   ├── check.py                 # was rulerepo-check
│           │   ├── hook.py                  # was rulerepo-hook
│           │   ├── ingest.py                # was rulerepo-ingest
│           │   ├── export.py                # was rulerepo-export
│           │   ├── context.py               # was rulerepo-context
│           │   ├── mcp.py                   # was rulerepo-mcp
│           │   ├── init.py                  # IMPLEMENTED
│           │   ├── doctor.py                # IMPLEMENTED
│           │   └── audit.py                 # IMPLEMENTED (chain verify)
│           └── pyproject.toml
├── infra/
│   ├── docker/
│   ├── postgres/
│   │   ├── init.sql
│   │   └── rls_policies.sql                 # IMPLEMENTED
│   ├── elasticsearch/
│   └── neo4j/
├── scripts/
│   ├── seed_data.py
│   ├── reconcile_graph.py
│   ├── reindex_elasticsearch.py
│   ├── generate_claude_md.py
│   ├── verify_audit_chain.py                # IMPLEMENTED
│   └── spec_audit.py                        # IMPLEMENTED
├── sample_rules/
│   ├── coding_rules/
│   ├── company_rules/
│   ├── sales_team_rules/
│   ├── legal_rules/                         # PLANNED Tier 2
│   ├── communication_rules/                 # PLANNED Tier 4
│   └── templates/
│       ├── python-fastapi.yaml
│       ├── typescript-react.yaml
│       ├── security-owasp.yaml
│       ├── api-design.yaml
│       ├── testing-standards.yaml
│       ├── documentation-standards.yaml     # PLANNED Tier 2
│       ├── nda-template.yaml                # PLANNED Tier 2
│       └── japan-labor-law.yaml             # PLANNED Tier 4
├── development/                             # Technical docs
│   ├── architecture.md
│   ├── api_reference.md
│   ├── database_schema.md
│   ├── feature_interactions.md              # NEW Tier 0
│   ├── spec_implementation_audit.md         # NEW Tier 0
│   ├── multi_tenancy.md                     # NEW Tier 3
│   ├── domain_adapter_guide.md              # NEW Tier 1
│   └── operations/
│       ├── backup_restore.md                # NEW Tier 3
│       ├── llm_failover.md                  # NEW Tier 3
│       └── observability.md                 # NEW Tier 3
├── docs/                                    # mkdocs site
├── docker-compose.yml                       # 8+ services
├── Makefile                                 # 63+ targets
├── pyproject.toml                           # uv workspace root
├── pnpm-workspace.yaml
├── .pre-commit-config.yaml
├── .env.example
├── PROJECT.md                               # Project vision and specification
├── CLAUDE.md                                # This file
└── IMPROVEMENT.md                           # Improvement analysis (input to current work)
```

When adding a new package, place it under `apps/` (deployable apps) or `packages/` (libraries). Update `pyproject.toml` (uv workspace) or `pnpm-workspace.yaml` accordingly.

---

## 4. Quick Start (local dev)

The whole stack must come up with one command. If your changes break this, fix it before continuing.

```bash
cp .env.example .env            # then fill in GEMINI_API_KEY
make up                         # or: docker compose up --build -d
make seed                       # load 23 sample documents and 5 rule templates
```

Expected services after `make up`:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | REST + Intent + Evaluate + Why API |
| API docs (OpenAPI) | http://localhost:8000/docs | FastAPI Swagger UI |
| Frontend | http://localhost:3000 | Next.js dev server |
| MCP Server | http://localhost:8001 | Streamable-HTTP MCP for agents |
| PostgreSQL | localhost:5432 | `ruledb` |
| Elasticsearch | http://localhost:9200 | Search index |
| Neo4j Browser | http://localhost:7474 | Rule graph |
| Redis | localhost:6379 | Job queue (arq) + idempotency cache |
| arq-worker | — | Background task processor |
| Jaeger UI | http://localhost:16686 | Distributed tracing (PLANNED) |
| Prometheus | http://localhost:9090 | Metrics (PLANNED) |

The frontend talks to the backend over `NEXT_PUBLIC_API_BASE_URL`. The Python clients talk to the backend over `RULEREPO_SERVER_URL`. The unified CLI defaults to `RULEREPO_SERVER_URL` or `--server URL`.

---

## 5. Common Commands

### Backend (apps/server)

```bash
cd apps/server
uv sync                                                      # install deps
uv run uvicorn rulerepo_server.main:app --reload             # dev server
uv run pytest                                                # run all tests
uv run pytest tests/unit                                     # unit only
uv run pytest tests/integration/feature_matrix               # feature interactions
uv run pytest tests/eval_harness --live-llm                  # eval harness (requires API key)
uv run ruff check .                                          # lint
uv run ruff format .                                          # format
uv run mypy src                                              # type check
uv run alembic upgrade head                                  # apply migrations
uv run alembic revision --autogenerate -m "..."              # new migration
```

### Frontend (apps/frontend)

```bash
cd apps/frontend
pnpm install
pnpm dev                                                     # dev server
pnpm build && pnpm start                                     # production build
pnpm lint                                                    # ESLint
pnpm test                                                    # Vitest / RTL
pnpm test:e2e                                                # Playwright (PLANNED)
pnpm typecheck                                               # tsc --noEmit
pnpm gen:api                                                 # regenerate OpenAPI client
```

### Unified CLI (replaces 6 separate binaries)

```bash
# Compliance check (was rulerepo-check)
rulerepo check --diff "$(git diff origin/main...HEAD)" --format github-actions

# Agent hooks (was rulerepo-hook)
rulerepo hook preflight --file src/api/handler.py --agent-id claude-code
rulerepo hook posthoc --file src/api/handler.py --agent-id claude-code

# Document/rule ingestion (was rulerepo-ingest)
rulerepo ingest --source claude-md --file ./CLAUDE.md --scope engineering/python
rulerepo ingest --source pdf --file ./contract.pdf --scope legal/procurement

# Rule export (was rulerepo-export)
rulerepo export --project backend-api --output rules.yaml

# CLAUDE.md context generator (was rulerepo-context)
rulerepo context generate --project backend-api
rulerepo context update --file CLAUDE.md
rulerepo context watch --file CLAUDE.md --interval 60

# MCP server (was rulerepo-mcp)
rulerepo mcp                                                 # stdio
MCP_TRANSPORT=streamable-http rulerepo mcp                   # HTTP

# NEW Tier 1
rulerepo init                                                # zero-config bootstrap
rulerepo doctor                                              # environment validation
rulerepo audit verify --since 7d                             # chain verification
```

### Whole repo (from root)

```bash
make help                                                    # show all targets
make up                                                      # start full stack
make down                                                    # stop
make reset                                                   # wipe volumes and rebuild
make dev.server                                              # FastAPI hot-reload
make dev.frontend                                            # Next.js hot-reload
make precommit.install                                       # install git hooks
make test                                                    # all tests
make check                                                   # format + lint + test (run before commit)
make eval-harness                                            # nightly eval (manual trigger)
make spec-audit                                              # NEW Tier 0
```

---

## 6. Coding Conventions

### Python (server + clients + CLI)

- **Python 3.13**. Use modern syntax: built-in generics (`list[str]`, `dict[str, int]`), `match` where it improves clarity, `type` aliases.
- **Type hints are mandatory** on all public functions. mypy must pass on `src/`.
- **Formatter and linter**: `ruff` (both linting and formatting). Configure via `pyproject.toml`. No `black`, no `isort`.
- **Naming**: snake_case for functions/vars, PascalCase for classes, SCREAMING_SNAKE_CASE for constants. Module names lowercase.
- **Docstrings**: Google style. Required on all public APIs.
- **Errors**: project-specific exception hierarchy under `rulerepo_server.errors` / `rulerepo.errors`. Never raise bare `Exception`.
- **Logging**: `structlog` with JSON output. Never `print()` outside one-off scripts. Include `tenant_id`, `agent_id`, and `trace_id` in log context where available.
- **Pydantic**: v2 idioms for all data validation at API boundaries.
- **Tests**: `pytest` + `pytest-asyncio`. Unit tests on pure logic, integration tests against the docker-compose stack, eval-harness tests for LLM-driven features.
- **Property-based tests**: use `hypothesis` for invariants (e.g., verdict aggregator monotonicity).

### TypeScript (frontend)

- **Strict TS**: `"strict": true` in `tsconfig.json`. No `any` without justification.
- **App Router** (Next.js 15). Server Components by default, Client Components only when needed.
- **Tailwind**: prefer utility classes. Centralize design tokens in `tailwind.config.ts`.
- **State**: Server Components and URL state preferred. For client state, `zustand`. For server-state caching, `@tanstack/react-query`.
- **Components**: PascalCase files, one component per file unless tightly coupled.
- **API calls**: generated TypeScript client from the backend's OpenAPI spec (`openapi-typescript` + `openapi-fetch`). Do not hand-write types that already exist in the API contract.
- **Linting**: ESLint + Prettier. `pnpm lint` must pass.

### Commits / branches

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `perf:`.
- Branch from `main`. Open PRs even for solo work — keeps history reviewable.
- PR title must reference the relevant Tier (e.g., `feat(adapter): add business_event adapter [Tier 2]`).

---

## 7. Backend Architecture Notes

The server is a single FastAPI application that exposes:

- **REST API** at `/api/v1/...` for CRUD on rules, documents, evaluations.
- **Evaluate API** at `/api/v1/evaluate` — domain-aware compliance checking. The request includes a `domain` discriminator dispatching to the matching adapter.
- **Intent API** at `/api/v1/intent` — natural-language query routing.
- **Why API** at `/api/v1/rules/{id}/why` [IMPLEMENTED] — multi-level rationale.
- **Audit API** at `/api/v1/audit/...` [IMPLEMENTED] — audit log inspection.
- **Gateway API** at `/api/v1/gateway/...` — webhook-driven enforcement.
- **Intelligence API** at `/api/v1/intelligence/...` — health, analytics, recommendations.
- **Discovery API** at `/api/v1/discover/...` — automatic rule discovery.
- **Feedback API** at `/api/v1/feedback/...` — correction feedback loop.
- **Federation API** at `/api/v1/federations/...` — hierarchical rule composition.
- **Integrations** at `/api/v1/integrations/...` — GitHub webhook receiver.
- **Playground API** at `/api/v1/playground/...` — sandbox evaluation.
- **Alerts API** at `/api/v1/alerts/...` — alert management.
- **Snapshots API** at `/api/v1/snapshots/...` — versioned rule sets.
- **Proposals API** at `/api/v1/proposals/...` — change proposals with voting.
- **Agent Governance API** at `/api/v1/agent-governance/...` — agent profiles, trust, exceptions.
- **Marketplace API** at `/api/v1/marketplace/...` — rule packages. **[DEPRECATED — Removed]**
- **MCP Server** on a separate port (8001).

### Layering Rule (strictly enforced)

```
api → services → domain
api → services → adapters
services → domain
adapters → domain (read-only; adapters never depend on services)
domain → nothing else in the project
```

Do not import upward. Mypy + custom CI lint enforces this.

### Async

The API layer is fully async. DB calls use `asyncpg` (or `sqlalchemy[asyncio]`). Elasticsearch via the async client. Neo4j via the official async driver. Gemini via `google-genai`.

### Tenant Context [PLANNED Tier 3]

Every request carries a `TenantContext` resolved from the API key. Helpers in `core/tenancy/` ensure SQLAlchemy sessions, Elasticsearch routing, and Neo4j database selection are tenant-scoped automatically. Bypassing tenant context is a CI failure.

---

## 8. Frontend Notes

The frontend is the operator console. After Tier 3 reorganization, navigation is grouped by activity, with persona-aware filtering:

```
Compose
  Rules · Documents · Discovery · Playground · Templates
Govern
  Proposals · Federation · Snapshots · Approvals · Audit
Observe
  Dashboard · Intelligence · Effectiveness · Notifications
Share
  Marketplace · Packages
Agents
  Profiles · Sessions · Trust Levels
```

A persona switcher in the user profile collapses irrelevant groups by default for the three personas (Compliance Officer, Engineering Lead, AI Operator).

Use Server Components for data fetching. Use Client Components only for interactivity. The graph view (Neo4j-backed) renders via `react-flow` or `cytoscape`; one of these has been chosen — do not introduce a third.

---

## 9. Gemini API Integration (read carefully)

The LLM layer is the heart of this system. Get this right.

### 9.1 SDK

- **Use `google-genai`** (the new unified SDK). Do **not** use the deprecated `google-generativeai`.
- Install via uv: `uv add google-genai httpx`.

### 9.2 Models

Two models are in use:

| Use case | Model ID | Why |
|---|---|---|
| High-throughput, routine tasks | `gemini-3-flash-preview` | Fast, cheap |
| High-stakes judgment (extraction QC, conflict detection, CRITICAL evaluation) | `gemini-3.1-pro-preview` | Strongest reasoning |

Centralize model selection in `core/llm.py`. Never hardcode model IDs in business logic. The `LLMProvider` Protocol (Tier 3) abstracts the provider entirely; until then, the routing module decides which Gemini model to use based on rule severity.

### 9.3 Mandatory rules when calling Gemini

- **Do NOT change `temperature`** away from the default (1.0). Lower temperatures degrade Gemini 3 reasoning quality and can cause loops. If a caller insists on determinism, document the override and review carefully.
- Use **`thinking_level`** (not the legacy `thinking_budget`). Valid values: `minimal`, `low`, `medium`, `high`. Default to `low` for high-throughput tasks, `high` for judgment tasks.
- For function calling, **thought signatures must be cycled through** every turn. The `google-genai` SDK and standard chat history handle this automatically — do not strip signatures from history.
- For PDFs, set `media_resolution: "media_resolution_medium"` (560 tokens/page). Going higher rarely helps OCR and increases cost.
- Use **structured output** (`response_mime_type="application/json"` + `response_json_schema`) for any call that must return data the system parses. Do not regex out fields from free-form LLM text.

### 9.4 Document ingestion (PDF, text, markdown)

- **PDFs > a few pages**: upload via the **Files API**. Files API is free, files persist 48 hours, max 50 MB / 1000 pages. **Always** sanitize via `services/extraction/pdf_sanitizer.py` (`pikepdf`-based; strips JavaScript, embedded files, XFA forms) before upload.
- For small / one-shot PDFs, inline `Part.from_bytes(data=..., mime_type='application/pdf')` is fine.
- **Text and markdown**: pass as plain text. Gemini "document understanding" only meaningfully renders PDFs.
- Each PDF page is roughly 258 tokens for image content; extracted native text is included free.
- The extraction pipeline wraps these calls; do not bypass it.

### 9.5 Cost and latency discipline

- Cache LLM responses by `hash(inputs + model + prompt_version + tenant_id)` in Postgres. Invalidate on rule revision.
- Default model: `gemini-3-flash-preview`. Use `gemini-3.1-flash-lite-preview` only with explicit approval. Use `gemini-3.1-pro-preview` only for high-severity judgment or extraction QC.
- Long-context calls should use **context caching** for repeated reuse.
- Persist `gemini_input_tokens`, `gemini_output_tokens`, `estimated_cost_usd` on every evaluation record [PLANNED Tier 3].

### 9.6 Determinism, audit, and consensus

- Every LLM call that produces a verdict, candidate rule, or relationship suggestion **must** log: model ID, prompt version (content hash), inputs, outputs, latency, timestamp. Goes to the audit log.
- Prompts live in `services/<area>/prompts/` as standalone files, versioned in git. No inline strings scattered across the codebase.
- For `severity=CRITICAL` rules with `DENY` verdict, `consensus.py` runs a second independent call. Mismatch → `NEEDS_CONFIRMATION`. [IMPLEMENTED]

### 9.7 Failure handling

- Gemini calls are wrapped in a circuit breaker (`aiobreaker`).
- When the breaker is open: `evaluate` returns `Verdict.UNKNOWN_LLM_DOWN`; CI hooks exit code 3; frontend shows degraded banner.
- Multi-provider fallback (when configured): the next-priority `LLMProvider` takes over; verdict carries `provider_fallback: true` and is sampled for review.

### 9.8 PII handling

Inputs to Gemini pass through `core/pii/tokenizer.py` [IMPLEMENTED] which replaces detected PII with stable placeholders (`[PERSON_1]`, `[EMAIL_1]`, `[ID_1]`). The reverse-mapping dict is encrypted and persisted with the evaluation record. De-tokenization happens locally on the LLM response before persistence.

For `rule.sensitivity == RESTRICTED`, the call is routed to a self-hosted LLM (Ollama / vLLM) rather than Gemini.

---

## 10. Data Layer

### 10.1 PostgreSQL (system of record)

- Stores rules, revisions, source documents, evaluations, audit log, governance, agent profiles, snapshots, proposals, packages.
- Migrations: `alembic`. One head per branch; rebase migrations before merging.
- The audit log table is **append-only**. A Postgres trigger rejects updates/deletes. A `previous_hash` column links each row to the previous, forming the integrity chain.
- **Tenant isolation** [PLANNED Tier 3]: every major model has `tenant_id`. Postgres Row-Level Security policies enforce isolation at the database layer. The application sets `rulerepo.current_tenant_id` per session via SQLAlchemy event listener.

### 10.2 Elasticsearch (search)

- Index `rules` with: `statement` (analyzed), `tags`, `scope`, `modality`, `effective_period`, `embedding` (dense_vector for hybrid).
- Hybrid scoring: BM25 + kNN. Rerank top-k with the LLM only when the user requests "smart" search.
- Re-index on rule revision; do not run partial updates that risk drift.
- **Tenant isolation** [PLANNED Tier 3]: use `routing=tenant_{id}` on all index and search operations.

### 10.3 Neo4j (relationship graph)

- One node label: `Rule`. Node `id` matches the Postgres rule ID.
- Relationships: `REFINES`, `OVERRIDES`, `CONFLICTS_WITH`, `DEPENDS_ON`, `DERIVES_FROM`, `SUCCEEDS`. Direction matters and is documented in PROJECT.md §5.4.
- `DERIVES_FROM` carries `basis_type` edge property (`law` / `regulation` / `internal_policy` / `department_rule` / `contract_template`). The provenance graph is queried by filtering on `basis_type`; this is **distinct** from the federation graph.
- Federation: `(:Federation)-[:CONTAINS]->(:Rule)`. Do not mix federation and provenance edges.
- Postgres is the source of truth for rule existence; Neo4j is a derived projection. If they disagree, Postgres wins and Neo4j is rebuilt by `scripts/reconcile_graph.py`.
- **Tenant isolation** [PLANNED Tier 3]: one Neo4j database per tenant (Neo4j 5 multi-database). Driver pool keys on `tenant_id`.

### 10.4 Redis

- arq job queue for background workers.
- Idempotency cache: `(tenant_id, idempotency_key, request_hash) → evaluation_id` with 24-hour TTL [IMPLEMENTED].
- Evaluation cache: `hash(inputs + model + prompt_version + tenant_id) → response` with TTL keyed on rule revision.

### 10.5 Object Storage [PLANNED Tier 3]

- Source documents (PDFs > 5 MB, large markdown bundles).
- Archived evaluations (Parquet, partitioned by date and tenant).
- Audit log WORM tier (S3 Object Lock with compliance mode for legal retention).

---

## 11. Testing

### 11.1 Test categories

- **Unit tests**: pure logic in `domain/`. No external services. Fast.
- **Integration tests**: spin up docker-compose services in CI. Use `testcontainers-python` if running CI without compose.
- **Feature interaction tests** [Tier 0]: in `tests/integration/feature_matrix/`. One test per documented interaction in `development/feature_interactions.md`.
- **LLM tests**: never call the real Gemini API in unit tests. Use a mock client. For integration, gate behind `RULEREPO_LIVE_LLM=1`.
- **Eval harness** [Tier 3]: golden test sets in `tests/eval_harness/golden/` for rule extraction and verdict accuracy. `tests/eval_harness/runner.py` runs nightly with `RULEREPO_LIVE_LLM=1`. CI fails if metrics regress > 5pp from baseline.
- **Frontend tests**: Vitest + RTL for components.
- **E2E tests** [Tier 3]: Playwright in `tests/e2e/`. One happy path per persona.
- **Mutation tests**: weekly run of `mutmut` on `domain/`. Target > 80% kill rate.
- **Property-based tests**: Hypothesis for invariants; required for verdict aggregation, conflict resolution, federation walk.

### 11.2 What to test for each new feature

When adding any new feature:

1. Unit tests on the pure logic.
2. At least one integration test exercising the full path through services and adapters.
3. If the feature interacts with another feature (Federation × Snapshot, etc.), a feature-matrix test.
4. If the feature involves LLM, at least one mocked unit test plus one eval-harness golden case.
5. If the feature has a frontend, at least one Vitest component test.

PRs that add code without proportionate test coverage are rejected.

### 11.3 Eval harness contract

```
tests/eval_harness/golden/
├── rule_extraction/
│   ├── japanese_labor_regulation.input.txt
│   ├── japanese_labor_regulation.expected.json
│   └── ...
└── verdict/
    ├── overtime_violation_50_hours.input.json
    ├── overtime_violation_50_hours.expected.json
    └── ...
```

Each `.input.*` is paired with an `.expected.*`. The runner compares actual outputs against expected and reports per-class precision/recall. Adding a golden case is part of the PR adding the feature.

---

## 12. Environment Variables

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
AUTH_REQUIRED=false                          # Set true for any non-local-dev deployment

# MCP Server
MCP_TRANSPORT=stdio
MCP_PORT=8001

# Redis / Background Workers
REDIS_URL=redis://redis:6379/0

# GitHub Integration
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=
GITHUB_TOKEN=

# Alerts and notifications
ALERT_WEBHOOK_URL=
DIGEST_WEBHOOK_URL=
NOTIFICATION_WEBHOOK_URL=
NOTIFICATION_WEBHOOK_TYPE=

# Marketplace
REGISTRY_URL=
REGISTRY_API_KEY=
PACKAGE_AUTO_UPDATE_ENABLED=false

# Agent Governance
AGENT_TRUST_PROMOTION_ENABLED=false          # Default off; require human approval
AGENT_MASTERY_THRESHOLD=0.95
AGENT_PATTERN_MIN_EVIDENCE=10

# PLANNED — Tier 1
IDEMPOTENCY_TTL_HOURS=24
CONSENSUS_FOR_CRITICAL=true
PII_TOKENIZER_ENABLED=true
PII_TOKENIZER_LOCALES=ja,en

# PLANNED — Tier 3 (multi-tenancy)
TENANT_ISOLATION_MODE=rls                    # rls | schema | database
DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000000

# PLANNED — Tier 3 (observability)
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
PROMETHEUS_METRICS_ENABLED=true

# PLANNED — Tier 3 (LLM provider abstraction)
LLM_PROVIDER_DEFAULT=gemini                  # gemini | anthropic | openai | local
LLM_PROVIDER_RESTRICTED=local                # for sensitivity=RESTRICTED
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
LOCAL_LLM_ENDPOINT=http://localhost:11434

# PLANNED — Tier 3 (object storage)
OBJECT_STORAGE_ENDPOINT=
OBJECT_STORAGE_BUCKET=rulerepo
OBJECT_STORAGE_ACCESS_KEY=
OBJECT_STORAGE_SECRET_KEY=

# PLANNED — Tier 3 (data retention)
EVALUATION_RETENTION_DAYS=365
AUDIT_LOG_RETENTION_DAYS=2555
CORRECTION_RETENTION_DAYS=730

# PLANNED — Tier 4 (regulatory feeds)
EGOV_API_KEY=
EURLEX_API_KEY=
FEDERAL_REGISTER_API_KEY=
```

When you add a new env var, update `.env.example` in the same change.

---

## 13. Important Rules for Claude Code

These are non-negotiable. Violating them breaks the system or wastes review time.

1. **Read PROJECT.md and IMPROVEMENT.md before designing anything new.** Domain decisions belong in PROJECT.md; analysis context lives in IMPROVEMENT.md.
2. **Respect the active Tier.** During Tier 0 (Stabilization), new feature work is frozen. Bug fixes, integration tests, and the spec audit only.
3. **Run linters, formatters, and type checkers before claiming a task is done.** `ruff`, `mypy`, `pnpm lint`, `pnpm typecheck`. CI will reject otherwise.
4. **Never commit secrets.** No API keys, no DB passwords. Use `.env` and `.env.example`.
5. **Never tweak Gemini `temperature`.** Default 1.0 stays.
6. **Never use deprecated Gemini params.** Use `thinking_level`, not `thinking_budget`. Use `google-genai`, not `google-generativeai`.
7. **Never bypass the extraction pipeline** to call Gemini directly from random services. There is one place that talks to Gemini for ingestion.
8. **Never bypass a domain adapter** to read raw input directly. The orchestrator dispatches through `services/evaluation/adapters/{domain}/`.
9. **Never write to the audit log table from application code.** Only the evaluation/extraction services write, and only through the audit-log adapter that enforces hash chaining.
10. **Never make Postgres and Neo4j disagree silently.** If you write to one, write to the other through the same service. If you can only write to one, queue the other change.
11. **Never delete rules.** Use `effective_period.valid_until` to retire them. Past evaluations must remain re-explainable.
12. **Never bypass tenant context.** All SQL, ES, and Neo4j calls go through tenant-aware helpers. Bypassing is a CI failure.
13. **Never log raw PII.** All log statements containing potentially-PII fields use `core.pii.mask()`. Tests verify masking on a fixture set.
14. **Keep `make up` working.** If your change breaks the local stack, fix it before merging.
15. **Update PROJECT.md, CLAUDE.md, and IMPROVEMENT.md** when introducing a new dependency, service, or architectural decision. Code without doc updates does not ship.
16. **Update status markers.** Every section in PROJECT.md uses `[IMPLEMENTED]`, `[PARTIAL]`, `[PLANNED]`, or `[DEPRECATED]`. CLAUDE.md sections use the same. Keep them honest.
17. **Prefer fewer dependencies.** Every added library is a long-term cost. Justify additions in the PR description.
18. **Write structured logs, not `print`.** Logs are operational data.
19. **Tests for LLM-driven features must mock the LLM** unless the test is explicitly an eval-harness test.
20. **Mix federation and provenance edges, and CI fails.** They are separate graphs in Neo4j.
21. **Idempotency-Key required for production** — when integrating evaluation into an external system, always send the header.
22. **No new feature without a feature-interaction test** if it touches Federation, Snapshots, Proposals, Marketplace, or Agent Governance.
23. **No new domain adapter without a golden-test case** in the eval harness.
24. **No new schema field without a migration and a backfill plan.** Document the backfill in the migration's docstring.
25. **When unsure, ask.** Open a draft PR with the question. Do not guess on domain semantics — wrong rules are worse than no rules.

---

## 14. Domain Adapter Implementation Pattern [Tier 1+]

When implementing a new evaluation domain adapter, follow this pattern.

### 14.1 Interface

```python
# services/evaluation/adapters/base.py
from typing import Protocol
from rulerepo_server.domain.evaluation import EvaluationContext

class EvaluationDomainAdapter(Protocol):
    """Parses domain-specific input into a uniform EvaluationContext."""

    domain: str  # discriminator: "code", "business_event", etc.

    async def parse(self, payload: dict) -> EvaluationContext:
        """Parse the request payload into an EvaluationContext.

        The EvaluationContext is the uniform input to RuleSelector.
        """
        ...

    def resolve_scopes(self, payload: dict) -> list[str]:
        """Resolve the applicable rule scopes from the payload.

        For 'code': from file paths via DEFAULT_SCOPE_MAP.
        For 'business_event': from event_type and Subject fields.
        For 'document_diff': from contract_type and ContractScope.
        For 'communication': from channel sensitivity and audience.
        For 'documentation': from doc paths and document type.
        """
        ...

    def get_prompt_fragments(self) -> dict[str, str]:
        """Return adapter-specific prompt fragments to be merged into
        the evaluation prompt. Keys are placeholders (e.g., 'domain_intro',
        'context_format') used in the shared prompt template.
        """
        ...
```

### 14.2 Wire-up

The orchestrator (`services/evaluation/service.py`) maintains a registry:

```python
ADAPTERS: dict[str, EvaluationDomainAdapter] = {
    "code": CodeAdapter(),
    "business_event": BusinessEventAdapter(),
    "document_diff": DocumentDiffAdapter(),
    "communication": CommunicationAdapter(),
    "documentation": DocumentationAdapter(),
}

async def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    adapter = ADAPTERS[request.domain]
    context = await adapter.parse(request.payload)
    scopes = adapter.resolve_scopes(request.payload)
    rules = await rule_selector.select(scopes=scopes, context=context, ...)
    verdicts = await batch_evaluator.evaluate(rules, context, adapter)
    ...
```

### 14.3 Per-domain conventions

- Prompts live in `services/evaluation/adapters/{domain}/prompts/`.
- Domain-specific value objects live in `domain/{domain_concept}.py` (e.g., `domain/subject.py`, `domain/contract.py`).
- Each adapter has its own scope resolver implementation.
- Each adapter ships with at least one `sample_rules/` template demonstrating its rules.

### 14.4 Required artifacts when adding a domain

When PR adds a new adapter:

1. The adapter implementation under `services/evaluation/adapters/{domain}/`.
2. Domain value objects under `domain/`.
3. At least one prompt under `services/evaluation/adapters/{domain}/prompts/`.
4. At least one sample-rules template under `sample_rules/templates/`.
5. At least 3 golden test cases in `tests/eval_harness/golden/verdict/{domain}/`.
6. Frontend handling: the rule detail page renders the new scope correctly; the discovery page recognizes new connectors if applicable.
7. Documentation in `development/domain_adapter_guide.md`.

---

## 15. Active Development: Tier-by-Tier Implementation Guidance

The current 90-day plan organizes work into five tiers. Read the tier you are working on **before** opening a PR.

### 15.1 Tier 0 — Stabilization [WEEKS 1–2]

**Goal**: stop the bleeding before adding more code.

**Allowed changes**: bug fixes, test additions, documentation, the spec-audit tool, the feature-matrix tests.
**Not allowed**: new features, new endpoints, new pages, new dependencies.

**Specific work items**:

1. **`scripts/spec_audit.py`**: **[DONE]**
   - Parses `PROJECT.md` and `CLAUDE.md` into sections.
   - Classifies features as `IMPLEMENTED`, `PARTIAL`, `PLANNED`, or `MISSING` via code-only heuristics (with optional `--live-llm` for Gemini-based classification).
   - Writes results to `development/spec_implementation_audit.md`.
   - `make spec-audit` Makefile target added.

2. **`development/feature_interactions.md`**: **[DONE]**
   - All 7 pairs documented with intended behavior, current behavior, gap, and remediation.
   - Maturity × Snapshot bug identified and fixed (serializer now includes `maturity_level`).
   - Marketplace interactions marked N/A (marketplace removed).

   | Pair | Question |
   |---|---|
   | Federation × Snapshot | Does a snapshot freeze federation resolution? |
   | Snapshot × Marketplace | Does a snapshot include subscribed package updates? |
   | Proposal × Federation | Who approves a child override of a parent rule? |
   | Agent Governance × Federation | Does personalization walk the federation chain? |
   | Maturity × Snapshot | Does an experimental rule keep shadow behavior in deployed snapshots? |
   | Marketplace × Maturity | Are imported rules subject to local maturity lifecycle? |
   | Proposal × Snapshot | What happens to live snapshots when a referenced rule is retired by proposal? |

3. **`tests/integration/feature_matrix/`**: **[DONE]**
   - Tests for all 7 pairs in `apps/server/tests/integration/feature_matrix/test_feature_interactions.py`.
   - Tests document current behavior and known gaps.

4. **CLAUDE.md and PROJECT.md cleanup**: **[DONE]**
   - Section numbering resolved (§14 collision fixed in earlier work).
   - Status markers (`[IMPLEMENTED]` / `[PARTIAL]` / `[PLANNED]` / `[DEPRECATED]`) applied consistently across both documents based on spec audit findings.

### 15.2 Tier 1 — Reliability and Foundation [WEEKS 3–6]

**Goal**: make the existing surface area trustworthy and prepare for domain expansion.

**Specific work items**:

1. **EvaluationDomainAdapter introduction**: **[DONE]**
   - `services/evaluation/adapters/base.py` defines `EvaluationDomainAdapter` Protocol.
   - `services/evaluation/adapters/code/` contains relocated existing logic.
   - All existing tests pass unchanged.

2. **Continuous Conflict Detector**: **[DONE]**
   - `workers/conflict_scanner.py` implemented.
   - Pre-filter pairs by embedding similarity > 0.7 OR scope overlap.
   - Bound at 200 LLM calls per run.
   - Auto-create `Proposal(type=resolve_conflict)` on detection.

3. **Idempotency-Key middleware**: **[DONE]**
   - `services/evaluation/idempotency.py` implemented.
   - Redis-backed `(tenant_id, idempotency_key, request_hash) → evaluation_id`, 24h TTL.
   - Same key + same payload → cached response. Same key + different payload → 409.

4. **Consensus voting for CRITICAL**: **[DONE]**
   - `services/evaluation/consensus.py` implemented.
   - Triggered for `severity=CRITICAL` rules with `DENY` verdict.
   - Two independent calls with `pro` model + `thinking_level=high`.
   - Mismatch → `NEEDS_CONFIRMATION` with `consensus_disagreement: true` flag.

5. **Audit Log inspection**: **[DONE]**
   - `GET /api/v1/audit?...` endpoint with filters — **[DONE]** (`api/v1/audit.py`).
   - `/audit` frontend page with pagination, filtering, CSV export — **[DONE]**.
   - `scripts/verify_audit_chain.py` walking the chain and asserting integrity — **[DONE]**.
   - CI runs verification nightly against last 7 days.

6. **PII Tokenizer + Sensitivity tag**: **[DONE]**
   - `core/pii/tokenizer.py` with regex detectors and named-entity recognition — **[DONE]**.
   - `Rule.sensitivity` field added (migration 023) — **[DONE]**.
   - LLM router consults `sensitivity` for provider selection — **[DONE]** (`core/llm.py:get_config_for_sensitivity`).
   - `evaluations.context_encrypted` column with AES-GCM at rest — **[DONE]** (migration 023).

7. **CLI consolidation**: **[DONE]**
   - `packages/cli/src/rulerepo_cli/main.py` with Typer/Click groups — **[DONE]**.
   - Existing entry points kept with deprecation warnings for one release cycle.
   - `rulerepo init`, `rulerepo doctor`, `rulerepo audit verify` — **[DONE]**.

### 15.3 Tier 2 — Domain Expansion [WEEKS 7–10]

**Goal**: make non-code domains first-class.

**Specific work items**:

1. **`business_event` adapter**: **[DONE]**
   - `services/evaluation/adapters/business_event/` implemented.
   - `domain/subject.py` with `Subject` and `SubjectFilter` implemented.
   - `Rule.applicable_to: list[SubjectFilter]` field implemented.
   - Golden cases and sample rules template — verify coverage.

2. **`document_diff` adapter**: **[DONE]**
   - `services/evaluation/adapters/document_diff/` implemented.
   - `domain/contract.py` with `ContractType`, `ContractScope`, `PartyRole`, `Clause` implemented.
   - `services/extraction/contract/` — **[DONE]** (clause segmenter, classifier, reference resolver with 15 unit tests).
   - Golden cases and sample rules template — verify coverage.

3. **`documentation` adapter**: **[DONE]**
   - `services/evaluation/adapters/documentation/` implemented.
   - Markdown AST parser, glossary checker, link validator.
   - Sample rules template — verify coverage.

4. **Counterexample Generator**: **[DONE]**
   - `services/playground/counterexample_generator.py` implemented.
   - On rule create / update, Gemini generates one minimal compliant + one minimal violating example.
   - Persisted as test cases.

5. **Why API and Provenance Lineage**: **[DONE]**
   - `services/provenance/lineage_resolver.py` — **[DONE]** (includes `basis_type` in output).
   - `GET /api/v1/rules/{id}/why?depth=N` — **[DONE]**.
   - `derives_from` edge property `basis_type` added to Neo4j — **[DONE]** (`graph_repo.create_relationship`).
   - Reconciler script updated to emit edge property — **[DONE]**.

6. **Source Connectors (initial)**: **[DONE]**
   - `services/discovery/connectors/confluence.py` implemented.
   - `services/discovery/connectors/notion.py` implemented.
   - `services/discovery/connectors/egov.py` and `eurlex.py` also implemented (ahead of Tier 4 schedule).

### 15.4 Tier 3 — Operations and Differentiation [WEEKS 11–14]

**Goal**: production-ready operations and unique value.

**Specific work items**:

1. **Multi-tenancy**: **[DONE]**
   - `TenantModel` and `tenant_id` foreign keys on rules — **[DONE]** (migration 024).
   - Postgres RLS policies in `infra/postgres/rls_policies.sql` — **[DONE]**.
   - `core/tenancy/` with `TenantContext`, `tenant_scope()`, get/set functions — **[DONE]**.
   - Elasticsearch `routing=tenant_{id}` — wiring pending per-query.
   - Neo4j multi-database — wiring pending per-driver-pool.
   - API key → tenant mapping in `core/auth.py` — wiring pending.

2. **Observability**: **[DONE]**
   - `core/telemetry.py` setting up OpenTelemetry — **[DONE]**.
   - `/metrics` Prometheus endpoint — **[DONE]** (in `main.py`).
   - docker-compose adds Jaeger and Prometheus — **[DONE]**.

3. **LLM Provider abstraction**: **[DONE]**
   - `adapters/llm/base.py` defining `LLMProvider` Protocol — **[DONE]**.
   - `adapters/llm/anthropic.py`, `adapters/llm/openai.py`, `adapters/llm/local.py` — **[DONE]**.
   - Routing in `core/llm.py` based on `(rule.sensitivity, rule.severity, tenant.allowed_providers)`.
   - Multi-provider fallback on Gemini circuit-breaker open.

4. **Cost Ledger**: **[DONE]**
   - `input_tokens`, `output_tokens`, `estimated_cost_usd` on `EvaluationRecordModel` — **[DONE]** (migration 024).
   - `cost_tracker.py` with pricing table and tracking — **[DONE]**.
   - Intelligence dashboard "Cost" panel — wiring pending.

5. **Eval Harness**: **[DONE]**
   - `tests/eval_harness/runner.py` with golden case loading and accuracy computation — **[DONE]**.
   - `tests/eval_harness/golden/` directory structure — **[DONE]**.
   - CI regression check (>5pp) — **[DONE]** in runner.py.

6. **Frontend persona reorganization**: **[DONE]**
   - Sidebar grouped by manage / observe / enforce / settings — **[DONE]**.
   - `PersonaSwitcher` component in sidebar — **[DONE]**.
   - Onboarding wizard for zero-state — deferred.

7. **Data retention**: **[DONE]**
   - `workers/archival.py` moving evaluations > 30 days to S3 Parquet — **[DONE]**.
   - `evaluations_daily_agg` table — **[DONE]** (migration 024 + model).
   - Audit log archival to S3 Object Lock — wiring pending.

8. **E2E test suite**: **[DONE]**
   - `tests/e2e/` with evaluation, extraction, and full workflow tests — **[DONE]**.

### 15.5 Tier 4 — Cross-Domain and Regulatory [WEEKS 15+]

**Goal**: complete the user-stated domain matrix.

**Specific work items**:

1. **`communication` adapter**: **[DONE]** (adapter + Slack/Teams/Email gateway normalizers all implemented).
2. **Regulatory feed connectors**: **[DONE]** (e-Gov and EUR-Lex connectors implemented; Federal Register — **[PLANNED]**).
3. **Polyglot Rules**: **[DONE]** (`workers/polyglot_validator.py` + `equivalence_id` field on RuleModel (migration 024) — **[DONE]**).
4. **Rule Tutor frontend**: **[DONE]** (`/tutor` page backed by Intent API — **[DONE]**).
5. **Verdict Drift monitor**: **[DONE]** (`workers/verdict_drift.py` implemented).
6. **Bulk Impact Preview**: **[DONE]** (`POST /api/v1/snapshots/{id}/simulate-bulk` — **[DONE]**).
7. **Self-governance meta-rules**: **[PLANNED]** (register the rules from PROJECT.md §7.4 in the system itself; track effectiveness).

---

## 16. Migration Path Documentation

When introducing a refactor with breaking implications (e.g., the Domain Adapter introduction, multi-tenancy), follow this template:

1. **Add the new structure alongside the old.** No deletion in the same PR.
2. **Provide compatibility shims** for the old import paths.
3. **Migrate one consumer at a time** in subsequent PRs.
4. **Deprecation warnings** with a removal-target version.
5. **Removal PR** only after all consumers are migrated and one full release cycle has passed.

Each refactor PR includes a "Migration Path" section in the description. The squashed merge commit message preserves this section.

---

## 17. Common Pitfalls (Hard-Won Lessons)

### 17.1 Mixing federation and provenance edges in Neo4j

A previous design used `(:Rule)-[:DERIVES_FROM]->(:Rule)` for both regulatory derivation and federation hierarchy. This conflated organizational ownership with regulatory grounding, breaking both the Why API and the federation resolver.

**Rule**: `DERIVES_FROM` is regulatory provenance only. Federation uses `(:Federation)-[:CONTAINS]->(:Rule)`. CI lint catches violations.

### 17.2 Calling Gemini with `temperature` other than 1.0

Gemini 3 reasoning is calibrated for `temperature=1.0`. Lower temperatures produce loops and degraded reasoning. We have an integration test that explicitly catches this.

**Rule**: leave temperature alone.

### 17.3 Stripping thought signatures during chat replay

If a function-calling history is replayed without the original `thoughtSignature` blocks, Gemini returns an error or produces noticeably worse follow-ups.

**Rule**: pass through whatever the SDK gives you. Don't filter.

### 17.4 Forgetting to set tenant context in background workers

Workers don't have an HTTP request, so `core/tenancy/middleware.py` doesn't fire. Workers must set tenant context explicitly via `with tenant_scope(tenant_id):`. Test fixtures include a worker-tenant integration test.

### 17.5 Forgetting to encrypt context columns

When adding a new evaluation-context-related column, default to encrypted unless content is explicitly non-sensitive. Migration generators include a check.

---

## 18. References

- Gemini 3 developer guide: <https://ai.google.dev/gemini-api/docs/gemini-3>
- Gemini document processing: <https://ai.google.dev/gemini-api/docs/document-processing>
- Gemini Files API: <https://ai.google.dev/gemini-api/docs/files>
- Semantic Governance (conceptual inspiration): <https://docs.cloud.google.com/gemini-enterprise-agent-platform/govern/policies/configure-semantic-governance>
- uv: <https://docs.astral.sh/uv/>
- pnpm: <https://pnpm.io/>
- FastAPI: <https://fastapi.tiangolo.com/>
- Next.js App Router: <https://nextjs.org/docs/app>
- Neo4j Python driver: <https://neo4j.com/docs/api/python-driver/current/>
- Neo4j multi-database: <https://neo4j.com/docs/operations-manual/current/manage-databases/>
- Elasticsearch Python client: <https://elasticsearch-py.readthedocs.io/>
- OpenTelemetry Python: <https://opentelemetry.io/docs/instrumentation/python/>
- Postgres Row-Level Security: <https://www.postgresql.org/docs/current/ddl-rowsecurity.html>
- arq: <https://arq-docs.helpmanual.io/>
- FastMCP: <https://github.com/jlowin/fastmcp>

---

*This file is a contract. If you (Claude Code) find a conflict between this file and the user's request, surface the conflict and ask. Do not silently override.*

*If a section of this file conflicts with PROJECT.md, PROJECT.md wins for vision and CLAUDE.md wins for operational guidance. If both are silent, follow IMPROVEMENT.md until both are updated.*

# CLAUDE.md

> Operational guide for Claude Code when working on the **Rule Repository** project.
> For the project vision, domain model, and roadmap, see **PROJECT.md**.

This file is the working contract between you (Claude Code) and the project. Read it before making changes. When in doubt, follow the rules in this file over your prior conventions.

---

## 1. Project at a Glance

The Rule Repository stores natural-language rules (laws, contracts, policies, engineering rules, doc standards) and makes them searchable, evaluable, and enforceable through LLM-assisted services and SDKs. See `PROJECT.md` for the full design.

**This repository is a monorepo** containing the backend server, frontend, Python client SDKs, and local dev infrastructure. The first deliverable is a fully working local stack via **Docker Compose**.

---

## 2. Tech Stack (authoritative)

| Layer | Technology | Notes |
|---|---|---|
| Backend | **Python 3.13** + FastAPI | Library management with **uv** |
| Frontend | **TypeScript**, **React**, **Next.js**, **Tailwind CSS** | Library management with **pnpm** |
| Python clients | **Python 3.13** (Rule Client, Agentic Rule Client) | Library management with **uv** |
| LLM | **Gemini 3 Flash** (`gemini-3-flash-preview`) and **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`) | via `google-genai` SDK |
| Document parsing / OCR | **Gemini Files API** + document understanding | PDF, text, markdown |
| Relational DB | **PostgreSQL** | rules, revisions, audit log |
| Search | **Elasticsearch** | full-text + hybrid search |
| Graph DB | **Neo4j** | rule relationships (`refines`, `overrides`, `conflicts_with`, `derives_from`, `succeeds`, `depends_on`) |
| Job Queue | **arq** + **Redis** | Background tasks (health scoring, recommendations, correction analysis) |
| Local orchestration | **Docker Compose** | dev + integration tests |

Do **not** introduce additional frameworks or services without updating this file and PROJECT.md first.

---

## 3. Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                 # FastAPI backend (Python 3.13, uv)
│   │   ├── pyproject.toml
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/         # REST API routers (rules, search, evaluate, intent, etc.)
│   │   │   ├── core/           # config, logging, errors, auth, middleware, PII
│   │   │   ├── domain/         # Rule, Evaluation, Verdict (pure domain objects)
│   │   │   ├── services/       # evaluation/, extraction/, search, intent, intelligence/, context_delivery/, discovery/, feedback/, federation/
│   │   │   ├── adapters/       # postgres, elasticsearch, neo4j, gemini, files
│   │   │   ├── mcp/            # MCP server (tools, resources, prompts)
│   │   │   ├── gateway/        # Enforcement gateway (normalizers, policies, SSE)
│   │   │   ├── integrations/   # GitHub App, CI formatters
│   │   │   ├── schemas/        # Pydantic request/response models
│   │   │   └── workers/        # background jobs (arq): settings.py, tasks.py
│   │   ├── alembic/            # database migrations
│   │   └── tests/
│   └── frontend/               # Next.js + TS + Tailwind (pnpm)
│       ├── package.json
│       ├── app/                # App Router (rules, search, documents, intelligence, gateway, integrations)
│       └── components/         # Badge, RuleCard, RuleGraph, Pagination, etc.
├── packages/
│   ├── rule-client/            # Python SDK (thin wrapper over server APIs)
│   ├── agentic-client/         # Python SDK (wraps rule-client + evaluation)
│   └── cli/                    # CLI tools: rulerepo-check, rulerepo-hook, rulerepo-ingest
├── infra/
│   ├── docker/                 # Dockerfiles (server, frontend)
│   ├── postgres/               # init SQL
│   ├── elasticsearch/          # index templates + setup script
│   └── neo4j/                  # constraints
├── scripts/                    # seed_data, reconcile_graph, generate_claude_md
├── development/                # technical development docs
├── docs/                       # mkdocs documentation site
├── docker-compose.yml          # local dev stack
├── pyproject.toml              # uv workspace root
├── pnpm-workspace.yaml
├── .env.example
├── PROJECT.md                  # project vision and specification
└── CLAUDE.md                   # this file — operational guide
```

When adding a new package, place it under `apps/` (deployable apps) or `packages/` (libraries). Update `pyproject.toml` (uv workspace) or `pnpm-workspace.yaml` accordingly.

---

## 4. Quick Start (local dev)

The whole stack must come up with one command. If your changes break this, fix it before continuing.

```bash
cp .env.example .env            # then fill in GEMINI_API_KEY
docker compose up --build       # brings up: server, frontend, postgres, elasticsearch, neo4j
```

Expected services after `up`:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | REST + Intent API |
| API docs (OpenAPI) | http://localhost:8000/docs | FastAPI Swagger UI |
| Frontend | http://localhost:3000 | Next.js dev server |
| PostgreSQL | localhost:5432 | `ruledb` |
| Elasticsearch | http://localhost:9200 | search index |
| Neo4j Browser | http://localhost:7474 | rule graph |
| MCP Server | http://localhost:8001 | Streamable-HTTP MCP for agents |
| Redis | localhost:6379 | Job queue (arq) |
| arq-worker | — | Background task processor |

The frontend talks to the backend over `NEXT_PUBLIC_API_BASE_URL`. The Python clients talk to the backend over `RULEREPO_SERVER_URL`.

---

## 5. Common Commands

### Backend (apps/server)

```bash
cd apps/server
uv sync                         # install deps
uv run uvicorn rulerepo_server.main:app --reload   # run dev server
uv run pytest                   # run tests
uv run ruff check .             # lint
uv run ruff format .            # format
uv run mypy src                 # type check
```

### Frontend (apps/frontend)

```bash
cd apps/frontend
pnpm install
pnpm dev                        # Next.js dev server
pnpm build && pnpm start        # production build
pnpm lint                       # ESLint
pnpm test                       # Vitest / React Testing Library
pnpm typecheck                  # tsc --noEmit
```

### Python SDKs (packages/rule-client, packages/agentic-client)

```bash
cd packages/rule-client
uv sync
uv run pytest
uv build                        # build wheel
```

### CLI Tools (packages/cli)

```bash
rulerepo-check --diff "$(git diff origin/main...HEAD)" --format github-actions   # CI
rulerepo-hook preflight --file src/api/handler.py     # agent hook: before edit
rulerepo-hook posthoc --file src/api/handler.py       # agent hook: after edit
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python  # import rules
```

### MCP Server

```bash
uv run rulerepo-mcp                    # stdio (local, for Claude Code)
MCP_TRANSPORT=streamable-http uv run rulerepo-mcp   # HTTP (remote agents)
```

### Whole repo (from root)

```bash
docker compose up --build
docker compose down -v          # tear down + wipe volumes
docker compose logs -f server   # tail server logs
uv run python -m pytest         # run all tests (142+)
```

---

## 6. Coding Conventions

### Python (server + clients)
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
- **API calls**: generated TypeScript client from the backend's OpenAPI spec (`openapi-typescript` or `orval`). Do not hand-write types that already exist in the API contract.
- **Linting**: ESLint + Prettier. `pnpm lint` must pass.

### Commits / branches
- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- Branch from `main`. Open PRs even for solo work — keeps history reviewable.

---

## 7. Backend Architecture Notes

The server is a single FastAPI application that exposes:

- **REST API** at `/api/v1/...` for CRUD on rules, documents, evaluations.
- **Evaluate API** at `/api/v1/evaluate` for code-aware compliance checking (diffs, files, or facts).
- **Intent API** at `/api/v1/intent` that classifies natural-language queries and routes to handlers.
- **Gateway API** at `/api/v1/gateway/...` for webhook-driven enforcement.
- **Intelligence API** at `/api/v1/intelligence/...` for health scoring, analytics, recommendations.
- **Discovery API** at `/api/v1/discover/...` for automatic rule discovery from code, configs, and PR comments.
- **Feedback API** at `/api/v1/feedback/...` for agent correction feedback loop.
- **Federation API** at `/api/v1/federations/...` for cross-project rule federation.
- **Integrations** at `/api/v1/integrations/...` for GitHub webhook receiver.
- **Playground API** at `/api/v1/playground/...` for sandbox evaluation and test cases.
- **Alerts API** at `/api/v1/alerts/...` for proactive alert management.
- **Snapshots API** at `/api/v1/snapshots/...` for versioned rule set deployment.
- **MCP Server** on a separate port (8001) for AI agent tool integration.

Internal modules:

```
src/rulerepo_server/
├── main.py                     # FastAPI app factory
├── api/v1/                     # routers (rules, search, evaluate, intent, intelligence, extraction)
├── core/                       # config, logging, errors, auth, middleware, PII, deps
├── domain/                     # Rule, Evaluation, Verdict, AuditEntry (pure)
├── services/
│   ├── evaluation/             # Code-Aware Evaluation Engine
│   │   ├── service.py          #   Orchestrator (context→select→evaluate→aggregate)
│   │   ├── batch_evaluator.py  #   Batched multi-rule evaluation (single LLM call, fallback to per-rule)
│   │   ├── evaluation_core.py  #   LLM-as-Judge per rule (with cache)
│   │   ├── diff_parser.py      #   Unified diff parser
│   │   ├── context_assembler.py#   Normalize inputs into EvaluationContext
│   │   ├── rule_selector.py    #   Narrow corpus (scope+severity+effective_period)
│   │   ├── graph_resolver.py   #   Neo4j relationship resolution (OVERRIDES/DEPENDS_ON)
│   │   ├── conflict_aggregator.py # Conflict-aware verdict aggregation
│   │   ├── verdict_aggregator.py  # Simple verdict aggregation (fallback)
│   │   └── impact_preview.py   #   Rule change impact analysis (replay evaluations)
│   ├── extraction/             # Document ingestion pipeline (Gemini-powered)
│   ├── intelligence/           # Health scoring, analytics (cache stats, top violations), recommendations
│   ├── context_delivery/       # Smart rule selection + formatting for agents
│   ├── discovery/              # Automatic rule discovery
│   │   ├── service.py          #   Scan orchestrator
│   │   ├── github_importer.py  #   GitHub repo import (fetch CLAUDE.md, configs via API)
│   │   ├── analyzers/          #   claude_md.py, linter_config.py, code_patterns.py
│   │   └── pattern_detector.py #   Deduplication + confidence scoring
│   ├── feedback/               # Correction feedback loop
│   │   ├── service.py          #   FeedbackService (submit, analyze, approve)
│   │   ├── pr_capture.py       #   Auto-capture corrections from merged PRs
│   │   ├── correction_analyzer.py # Semantic delta analysis
│   │   └── auto_drafter.py     #   [PLANNED] Auto-draft rules from correction patterns
│   ├── federation/             # Cross-project rule federation (hierarchy + resolution)
│   ├── playground/             # Rule sandbox + test cases
│   │   ├── service.py          #   PlaygroundService (sandbox eval, test CRUD)
│   │   ├── test_runner.py      #   Execute test suite per rule
│   │   └── test_generator.py   #   Gemini-powered test case generation
│   ├── snapshots/              # Rule set versioning + deployment
│   │   ├── service.py          #   SnapshotService (create, deploy, rollback)
│   │   ├── simulator.py        #   Impact simulation (compare snapshots)
│   │   └── serializer.py       #   Rule snapshot serialization
│   ├── search.py               # Multi-modal search service
│   ├── rule_service.py         # Rule CRUD orchestration (PG+ES+Neo4j)
│   └── intent.py               # Intent classification and routing
├── adapters/                   # postgres, elasticsearch, neo4j, gemini, files
├── mcp/                        # MCP server (tools, resources, prompts)
├── gateway/                    # Enforcement gateway (normalizers, policies)
├── integrations/               # GitHub webhook, CI formatters
├── workers/                    # background jobs (arq): settings.py, tasks.py
└── schemas/                    # Pydantic request/response models
```

**Layering rule**: `api` depends on `services`, `services` depends on `domain` and `adapters`. `domain` depends on nothing else in the project. Do not import upward.

**Async**: the API layer is fully async. DB calls use `asyncpg` (or `sqlalchemy[asyncio]`), Elasticsearch via the async client, Neo4j via the official async driver, Gemini via `google-genai`.

---

## 8. Frontend Notes

The frontend is the operator console for the Rule Repository:

- Browse and search rules
- Upload documents → run extraction → review/approve candidate rules
- View rule details, source provenance, and the relationship graph
- Inspect evaluations and audit logs
- Manage governance (owners, approvers, revision proposals)

Use the Next.js App Router. Co-locate route segments under `app/(area)/...`. Use Server Components for data fetching where possible; switch to Client Components only for interactivity.

The graph view (Neo4j-backed) renders using something like `react-flow` or `cytoscape`. Pick one early and stick with it.

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
| High-throughput, routine tasks (search ranking, simple extraction, classification) | `gemini-3-flash-preview` | fast, cheap |
| High-stakes judgment (rule extraction QC, conflict detection, evaluation of CRITICAL rules) | `gemini-3.1-pro-preview` | strongest reasoning |

Centralize model selection in one config module (`core/llm.py`). Never hardcode model IDs in business logic — always read from config.

### 9.3 Mandatory rules when calling Gemini
- **Do NOT change `temperature`** away from the default (1.0). Lower temperatures degrade Gemini 3 reasoning quality and can cause loops. If a caller insists on determinism, document the override and review carefully.
- Use **`thinking_level`** (not the legacy `thinking_budget`). Valid values: `minimal`, `low`, `medium`, `high`. Default to `low` for high-throughput tasks, `high` for judgment tasks.
- For function calling, **thought signatures must be cycled through** every turn. The `google-genai` SDK and standard chat history handle this automatically — do not strip signatures from history.
- For PDFs in document processing, set `media_resolution: "media_resolution_medium"` (560 tokens/page). Going higher rarely helps OCR and increases token cost.
- Use **structured output** (`response_mime_type="application/json"` + `response_json_schema`) for any call that must return data the system parses. Do not regex out fields from free-form LLM text.

### 9.4 Document ingestion (PDF, text, markdown)
- **PDFs**: upload via the **Files API** (`client.files.upload(...)`) for documents > a few pages. Files API is free, files persist 48 hours, max 50 MB / 1000 pages.
- For small / one-shot PDFs, inline `Part.from_bytes(data=..., mime_type='application/pdf')` is fine.
- **Text and markdown**: pass as plain text. Note that Gemini "document understanding" only meaningfully renders PDFs; for `.md`/`.txt`, treat them as text-only inputs (no charts, no formatting interpretation).
- Each PDF page is roughly 258 tokens for image content; extracted native text is included free.
- The extraction pipeline (see PROJECT.md §6.1) wraps these calls; do not bypass it from random parts of the codebase.

### 9.5 Cost and latency discipline
- Cache LLM responses by `hash(inputs + model + prompt_version)` in Postgres. Invalidate on rule revision.
- Use `gemini-3.1-flash-lite-preview` only if explicitly approved for a use case where Flash is overkill. Default is `gemini-3-flash-preview`.
- Long-context calls (rule corpus + large doc) should use **context caching** for repeated reuse.

### 9.6 Determinism and audit
- Every LLM call that produces a verdict, a candidate rule, or a relationship suggestion **must** log: model ID, prompt version (a content hash), inputs, outputs, latency, timestamp. This goes to the audit log.
- Prompts live in `services/<area>/prompts/` as standalone files (or constants), versioned in git. No inline strings scattered across the codebase.

---

## 10. Data Layer

### 10.1 PostgreSQL (system of record)
- Stores rules, revisions, source documents, evaluations, audit log.
- Migrations: `alembic`. One head per branch; rebase migrations before merging.
- The audit log table is **append-only**. Enforce with a Postgres trigger that rejects updates/deletes. Add a hash chain column linking each row to the previous row.

### 10.2 Elasticsearch (search)
- Index `rules` with: `statement` (analyzed), `tags`, `scope`, `modality`, `effective_period`, `embedding` (dense_vector for hybrid search).
- Use BM25 + kNN hybrid scoring. Rerank top-k with the LLM only when the user requests "smart" search.
- Re-index on rule revision; do not run partial updates that risk drift.

### 10.3 Neo4j (relationship graph)
- One node label: `Rule`. Node `id` matches the Postgres rule ID.
- Relationships: `REFINES`, `OVERRIDES`, `CONFLICTS_WITH`, `DEPENDS_ON`, `DERIVES_FROM`, `SUCCEEDS`. Direction matters and is documented in PROJECT.md §5.2.
- Postgres is the source of truth for rule existence; Neo4j is a derived projection of relationships. If they disagree, Postgres wins and Neo4j is rebuilt.
- Provide a reconciler script (`scripts/reconcile_graph.py`) that rebuilds Neo4j from Postgres.

---

## 11. Testing

- **Unit tests**: pure logic in `domain/`. No external services. Fast.
- **Integration tests**: spin up docker-compose services in CI. Use `testcontainers-python` if running in CI without compose.
- **LLM tests**: never call the real Gemini API in unit tests. Use a mock client. For integration, gate behind an env flag (`RULEREPO_LIVE_LLM=1`).
- **Frontend tests**: Vitest + React Testing Library for components; Playwright for end-to-end if added later.
- **Eval harness**: a separate test suite that validates LLM-driven features (rule extraction quality, conflict detection precision/recall) against curated fixtures. This runs nightly, not on every PR.

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
GITHUB_TOKEN=                        # for PR comment analysis

# Alerts
ALERT_WEBHOOK_URL=                   # URL to receive critical alert webhooks
```

When you add a new env var, update `.env.example` in the same change.

---

## 13. Important Rules for Claude Code

These are non-negotiable. Violating them breaks the system or wastes review time.

1. **Read PROJECT.md before designing anything new.** Domain decisions belong there, not here.
2. **Run linters, formatters, and type checkers before claiming a task is done.** `ruff`, `mypy`, `pnpm lint`, `pnpm typecheck`. CI will reject otherwise.
3. **Never commit secrets.** No API keys, no DB passwords, nothing in code. Use `.env` and `.env.example`.
4. **Never tweak Gemini `temperature`.** Default 1.0 stays.
5. **Never use deprecated Gemini params.** Use `thinking_level`, not `thinking_budget`. Use `google-genai`, not `google-generativeai`.
6. **Never bypass the extraction pipeline** to call Gemini directly from random services. There is one place that talks to Gemini for ingestion.
7. **Never write to the audit log table from application code.** Only the evaluation/extraction services write, and only through the audit-log adapter that enforces hash chaining.
8. **Never make Postgres and Neo4j disagree silently.** If you write to one, write to the other through the same service. If you can only write to one, queue the other change.
9. **Never delete rules.** Use `effective_period.valid_until` to retire them. Past evaluations must remain re-explainable.
10. **Keep `docker compose up --build` working.** If your change breaks the local stack, fix it before merging. The local stack is the developer onboarding path.
11. **Update both `PROJECT.md` and `CLAUDE.md`** when introducing a new dependency, service, or architectural decision. Code without doc updates does not ship.
12. **Prefer fewer dependencies.** Every added library is a long-term cost. Justify additions in the PR description.
13. **Write structured logs, not `print`.** Logs are operational data.
14. **Tests for LLM-driven features must mock the LLM** unless the test is explicitly an eval test.
15. **When unsure, ask.** Open an issue or a draft PR with the question. Do not guess on domain semantics — wrong rules are worse than no rules.

---

## 14. Phase 5 Implementation Guidance

These are architecture decisions and patterns for ongoing Phase 5 work. Read before implementing any improvement.

### 14.1 Batched Evaluation Architecture
- `batch_evaluator.py` sends all selected rules in a single Gemini call. The service.py orchestrator calls `evaluate_batch()` instead of `asyncio.gather()` on individual rules.
- **Fallback**: If the batch call fails for any reason, `evaluate_batch()` transparently falls back to per-rule `evaluate_rule()` via `asyncio.gather()`. No caller code changes.
- **Tiered**: Flash for the batch, Pro confirmation only for DENY + CRITICAL rules. Never send all rules to Pro.
- **Token budget**: If the combined prompt exceeds 30K chars, the batch raises ValueError and the fallback kicks in.
- Prompts: `evaluate_batch.txt` (code diffs) and `evaluate_batch_facts.txt` (scenarios) in `services/evaluation/prompts/`.

### 14.2 Evaluation Persistence
- The `evaluations` table stores one row per rule per evaluation (not per overall evaluation). This enables per-rule analytics.
- The intelligence analytics module has dual-path queries: `evaluations` table when it has data, `audit_log` JSON parsing as fallback. Remove the fallback once all historical data is backfilled.
- `get_compliance_trend(session, days)` returns daily compliance rates for sparkline charts.

### 14.3 Dashboard Summary API
- `GET /api/v1/intelligence/summary` returns all home dashboard data in one call. Queries run sequentially (SQLAlchemy async sessions do not support concurrent queries on the same connection).
- The frontend home page (`app/page.tsx`) is a Server Component that SSR-fetches from this endpoint. Graceful degradation: if API is unreachable, renders the minimal health-check page.

### 14.4 Rule Maturity Model (Implemented)
- `domain/rule.py` has `MaturityLevel` enum: EXPERIMENTAL, STABLE, PROVEN.
- `models.py` has `maturity_level`, `false_positive_count`, `true_positive_count` columns on RuleModel (migration 015).
- `evaluation_core.py` implements shadow mode: experimental rules with DENY verdict are downgraded to NEEDS_CONFIRMATION with `[SHADOW]` prefix.
- `rule_selector.py` includes `maturity_level` in the dict passed to evaluation core.
- `workers/settings.py` has `auto_promote_rules` cron job (4am daily): experimental→stable (30d, <5% FP), stable→proven (60d, <1% FP), demotion if FP >10%.
- New rules default to `experimental`. Existing rules backfilled as `proven` by migration.
- `RuleResponse` schema includes `maturity_level`.

### 14.5 Structured Auto-Remediation (Implemented)
- `domain/evaluation.py` has `Remediation` frozen dataclass: type, file_path, start_line, end_line, original, replacement, description, auto_applicable.
- `RuleVerdict` has `remediations: list[Remediation]` field.
- `evaluate_code_change.txt` prompt requests structured remediations in JSON schema.
- `_VERDICT_SCHEMA` in `evaluation_core.py` includes `remediations` array.
- `evaluation_core.py` parses `remediations` from LLM response and constructs `Remediation` objects.
- `schemas/evaluation.py` has `RemediationResponse` model; `EvaluateResponse` includes `remediations` and `auto_fixable_count`.
- `auto_applicable=true` only for SHOULD-level rules where fix is unambiguous.

### 14.6 Correction-to-Rule Flywheel (Implemented)
- `services/feedback/auto_drafter.py` implements `cluster_and_draft()`: cosine similarity clustering of corrections, Gemini-powered rule drafting.
- `models.py` has `DraftRuleProposalModel` (migration 016): statement, modality, severity, scope, evidence_correction_ids, confidence, status.
- `workers/settings.py` has `cluster_corrections` cron job (5am daily).
- `api/v1/feedback.py` has proposal endpoints: `GET /proposals`, `POST /proposals/{id}/approve` (creates rule with experimental maturity), `POST /proposals/{id}/dismiss`.
- Configuration: CLUSTER_WINDOW_DAYS=14, MIN_CLUSTER_SIZE=3, MIN_CONFIDENCE=0.8, SIMILARITY_THRESHOLD=0.8.

### 14.7 Agent Performance Tracking (Implemented)
- `EvaluateRequest` schema has `agent_id: str | None` field. CLI hook has `--agent-id` option with `RULEREPO_AGENT_ID` env var.
- `EvaluationRecordModel` has `agent_id` column (migration 017). Each evaluation record persists the agent identity.
- `services/intelligence/agent_analytics.py` provides: `get_agent_list()`, `get_agent_detail()`, `get_agent_top_violations()`.
- API: `GET /intelligence/agents` (list agents with compliance rates), `GET /intelligence/agents/{agent_id}` (trend + violations).
- `rule_selector.py` boosts rules the agent historically violates by +20 relevance points when `agent_id` is provided.
- Flow: CLI `--agent-id` → request → service → select_rules (boost) → persist record → analytics queries.

### 14.8 Rules-as-Code SDK (Partially Implemented)
- `packages/cli/src/rulerepo_cli/rules_yaml.py` defines `RulesYaml` and `RuleEntry` dataclasses with `load_rules_yaml()` and `save_rules_yaml()`.
- `packages/cli/src/rulerepo_cli/export.py` implements `rulerepo-export`: fetches rules from server, writes `rules.yaml`.
- `pyyaml>=6.0` added as CLI dependency.
- Entry point: `rulerepo-export` registered in `packages/cli/pyproject.toml`.

### 14.9 Seamless Agent Integration (Implemented)
- **File-aware scope resolution**: `resolve_scopes(file_path, custom_map)` in `context_delivery/scope_registry.py` with `DEFAULT_SCOPE_MAP` (20 glob patterns). Returns deduplicated scope list.
- **Session context API**: `GET /api/v1/rules/context?files=...&format=instructions`. Resolves scopes → loads rules → matches by language/path → formats with `format_rules(format_type=...)`. Must be registered before `/{rule_id}` route to avoid path conflict.
- **Rules import endpoint**: `POST /api/v1/rules/import` accepts `RulesImportRequest` with version + rules array. Creates rules with `["imported"]` tag. Schema in `schemas/rule.py`.

### 14.10 Rule Impact Analytics (Implemented)
- **Effectiveness score**: `services/intelligence/effectiveness.py` — `compute_effectiveness(session, rule_id)`. Three metrics: precision (40%, from FP/TP counts), prevention rate (35%, corrections before vs after), agent adoption (25%, ALLOW rate). API at `GET /intelligence/effectiveness/{rule_id}`.
- **Weekly digest**: `services/intelligence/digest.py` — `generate_weekly_digest(session, project_id)`. Sections: compliance trend, rule changes, top violations, attention needed, corrections, pending actions. API at `GET /intelligence/digest`. Cron: `send_weekly_digest` (Monday 9am) sends to `DIGEST_WEBHOOK_URL`.
- **Team comparison**: `GET /intelligence/comparison` — per-project rule count + compliance rate, sorted by performance.

### 14.11 Rule Templates (Implemented)
- 5 YAML templates in `sample_rules/templates/`: python-fastapi (15 rules), typescript-react (12), security-owasp (10), api-design (10), testing-standards (10).
- Format: `version: 1`, `template: {name, description, tags}`, `rules: [{statement, modality, severity, scope, tags, rationale}]`.
- Import via `POST /api/v1/rules/import` with the rules array from any template.

### 14.12 Future Implementation Notes
- **CLAUDE.md generator**: `rulerepo-context update --file ./CLAUDE.md` — maintains a `## Rules` section in CLAUDE.md, auto-updated when rules change.
- **Task-start hook**: Add `task-start` mode to `rulerepo-hook` with `--prompt` option for task-aware rule injection.
- **Zero-config init**: Create `packages/cli/src/rulerepo_cli/init.py` that wraps the existing discovery analyzers for local execution without the server.
- **CLI auto-fix**: Add `--auto-fix` flag to `rulerepo-check` that applies `auto_applicable` remediations and re-evaluates.
- **Agent dashboard frontend**: Create `/agents` page showing compliance leaderboard, per-agent trends, top violations.
- **Frontend onboarding wizard**: When zero rules exist, show 3-step wizard (scan → review → activate in shadow mode).
- **Infrastructure tiers**: Add `ELASTICSEARCH_ENABLED`, `NEO4J_ENABLED`, `REDIS_ENABLED` flags to Settings. Implement Postgres FTS fallback in search service.
- **Generated TypeScript client**: Export OpenAPI spec and use `openapi-typescript` + `openapi-fetch` to replace hand-written `lib/api.ts`.

---

## 15. References

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

---

*This file is a contract. If you (Claude Code) find a conflict between this file and the user's request, surface the conflict and ask. Do not silently override.*

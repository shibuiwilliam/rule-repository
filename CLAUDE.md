# CLAUDE.md

> Operational guide for Claude Code when working on the **Rule Repository** project.
> For the project vision, domain model, and roadmap, see **PROJECT.md**.
> For the analytical rationale behind the current refocus, see **IMPROVEMENT.md**.

This file is the working contract between you (Claude Code) and the project. Read it before making changes. When in doubt, follow the rules in this file over your prior conventions.

The project is in a **refocused** state. Existing engineering-centric code paths remain working but are being generalized into a Cross-Organizational Rule Platform. Many sections below describe the **target architecture**; current code may not yet match. Where this file describes a target state, follow that target state when adding new code, and migrate existing code only via the migration discipline described in §15.

---

## 1. Project at a Glance

The Rule Repository stores natural-language rules (laws, contracts, policies, HR regulations, finance controls, sales policies, communication standards, engineering rules, doc standards) and makes them searchable, evaluable, and enforceable through LLM-assisted services and SDKs across **all** business domains and personas. See `PROJECT.md` for the full design.

**This repository is a monorepo** containing the backend server, frontend, Python client SDKs, Domain Packs, and local dev infrastructure. The first deliverable is a fully working local stack via **Docker Compose**.

Two strategic facts to internalize:

1. **Code change is one `EvaluationSubject` kind among many**, not the default. Business events, document artifacts, transactions, and communications are equal first-class subjects.
2. **The system is structured around Domain Packs.** The core engine is domain-agnostic; domain-specific knowledge (prompts, analyzers, templates, metadata extensions) lives in `packages/domain-packs/{legal,hr,finance,sales,communication,engineering}/`. Do not put domain-specific behavior in the core.

---

## 2. Tech Stack (authoritative)

| Layer | Technology | Notes |
|---|---|---|
| Backend | **Python 3.13** + FastAPI | Library management with **uv** |
| Frontend | **TypeScript**, **React 19**, **Next.js 15**, **Tailwind CSS** | Library management with **pnpm** |
| Python clients | **Python 3.13** (Rule Client, Agentic Rule Client) | Library management with **uv** |
| LLM | **Gemini 3 Flash** (`gemini-3-flash-preview`) and **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`) | via `google-genai` SDK |
| Deterministic eval | **`asteval`** (sandboxed expressions), Pydantic (schema), in-memory state machine | no shell-out, no I/O |
| Document parsing / OCR | **Gemini Files API** + domain-adaptive structural parsers | PDF, text, markdown |
| Relational DB | **PostgreSQL 17** | rules, revisions, audit log; `scope` is JSONB |
| Search | **Elasticsearch 8** | full-text + dense_vector hybrid; `scope` indexed as a structured object |
| Graph DB | **Neo4j 5** | rule relationships (`refines`, `overrides`, `conflicts_with`, `derives_from`, `succeeds`, `depends_on`, `translates`) |
| Job Queue | **arq** + **Redis** | health scoring, recommendations, correction analysis, translation verification |
| MCP | **FastMCP** (`mcp >= 1.9`) | stdio + streamable-http |
| Local orchestration | **Docker Compose** | dev + integration tests |

Do **not** introduce additional frameworks or services without updating this file and PROJECT.md first.

---

## 3. Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                       # FastAPI backend (Python 3.13, uv)
│   │   ├── pyproject.toml
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/               # REST API routers
│   │   │   ├── core/                 # config, logging, errors, auth, middleware, PII, deps, feature flags
│   │   │   ├── domain/               # Rule, Evaluation, Verdict, Scope, EvaluationSubject, RuleKind, etc. (pure)
│   │   │   ├── services/
│   │   │   │   ├── evaluation/       # subject-dispatched evaluation engine
│   │   │   │   │   ├── service.py    #   orchestrator
│   │   │   │   │   ├── subjects/     #   per-subject context assemblers
│   │   │   │   │   ├── deterministic/#   deterministic-layer evaluators (numeric/schema/state/lookup)
│   │   │   │   │   ├── llm_judge/    #   LLM-layer evaluators
│   │   │   │   │   ├── rule_selector.py
│   │   │   │   │   ├── graph_resolver.py
│   │   │   │   │   └── verdict_aggregator.py
│   │   │   │   ├── extraction/       # domain-adaptive extraction pipeline
│   │   │   │   ├── intelligence/     # health, analytics, recommendations (essentials only)
│   │   │   │   ├── context_delivery/ # rule selection + formatting for agents and persona views
│   │   │   │   ├── discovery/        # cross-domain discovery (analyzers dispatched by Domain Pack)
│   │   │   │   ├── feedback/         # correction feedback loop (code + non-code)
│   │   │   │   ├── federation/       # hierarchical rule composition
│   │   │   │   ├── playground/       # sandbox + test cases for all subject kinds
│   │   │   │   ├── snapshots/        # versioning + deployment
│   │   │   │   ├── proposals/        # collaborative governance workflow
│   │   │   │   ├── governance/       # ABAC policy resolution
│   │   │   │   ├── multilingual/     # translation links + equivalence verification
│   │   │   │   ├── domain_packs/     # Domain Pack loader & registry
│   │   │   │   ├── search.py
│   │   │   │   ├── rule_service.py
│   │   │   │   └── intent.py
│   │   │   ├── adapters/             # postgres, elasticsearch, neo4j, gemini, files
│   │   │   ├── mcp/                  # MCP server (tools, resources, prompts)
│   │   │   ├── integrations/         # GitHub webhook (optional), CI formatters
│   │   │   ├── schemas/              # Pydantic request/response models
│   │   │   └── workers/              # background jobs (arq): settings.py, tasks.py
│   │   ├── alembic/                  # database migrations
│   │   └── tests/
│   └── frontend/                     # Next.js + TS + Tailwind (pnpm)
│       ├── package.json
│       ├── app/
│       │   ├── (personas)/
│       │   │   ├── engineering/      # current engineering pages migrated here
│       │   │   ├── legal/
│       │   │   ├── hr/
│       │   │   ├── finance/
│       │   │   ├── sales/
│       │   │   └── compliance/
│       │   └── (shared)/             # rule detail, search, proposals, settings, notifications
│       └── components/               # Badge, RuleCard, RuleGraph, Pagination, etc.
├── packages/
│   ├── rule-client/                  # Python SDK (thin wrapper over server APIs)
│   ├── agentic-client/               # Python SDK (wraps rule-client + evaluation)
│   ├── cli/                          # CLI tools: rulerepo-check, rulerepo-hook, rulerepo-ingest, rulerepo-export, rulerepo-context, rulerepo-policy
│   └── domain-packs/                 # NEW: business-domain extensions
│       ├── _core/                    # shared utilities (manifest schema, base prompts)
│       ├── engineering/              # existing engineering analyzers/prompts/templates migrated here
│       ├── legal/
│       ├── hr/
│       ├── finance/
│       ├── sales/
│       └── communication/
├── infra/
│   ├── docker/                       # Dockerfiles (server, frontend)
│   ├── postgres/                     # init SQL
│   ├── elasticsearch/                # index templates + setup script
│   └── neo4j/                        # constraints
├── scripts/                          # seed_data, reconcile_graph, generate_claude_md, reindex_elasticsearch
├── development/                      # technical development docs
├── docs/                             # mkdocs documentation site (per-persona sections)
├── docker-compose.yml                # local dev stack
├── pyproject.toml                    # uv workspace root
├── pnpm-workspace.yaml
├── .env.example
├── PROJECT.md                        # project vision and specification (target state)
├── CLAUDE.md                         # this file — operational guide
└── IMPROVEMENT.md                    # rationale for the refocus
```

When adding a new package, place it under `apps/` (deployable apps), `packages/` (libraries), or `packages/domain-packs/` (business-domain extensions). Update `pyproject.toml` (uv workspace) or `pnpm-workspace.yaml` accordingly.

---

## 4. Quick Start (local dev)

The whole stack must come up with one command. If your changes break this, fix it before continuing.

```bash
cp .env.example .env            # then fill in GEMINI_API_KEY
docker compose up --build       # brings up: server, frontend, postgres, elasticsearch, neo4j, redis, arq-worker, MCP server
```

Expected services after `up`:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | REST + Intent + Submissions APIs |
| API docs (OpenAPI) | http://localhost:8000/docs | FastAPI Swagger UI |
| Frontend | http://localhost:3000 | Next.js dev server (persona-aware) |
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
uv sync                                                   # install deps
uv run uvicorn rulerepo_server.main:app --reload          # run dev server
uv run pytest                                              # run tests
uv run pytest -m "not live_llm"                            # exclude live-LLM tests
uv run ruff check .                                        # lint
uv run ruff format .                                       # format
uv run mypy src                                            # type check
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

### Python SDKs and CLI

```bash
cd packages/rule-client
uv sync
uv run pytest
uv build                        # build wheel
```

### CLI Tools (packages/cli)

```bash
rulerepo-check --diff "$(git diff origin/main...HEAD)" --format github-actions       # CI
rulerepo-hook preflight --file src/api/handler.py                                     # agent hook: before edit
rulerepo-hook posthoc  --file src/api/handler.py                                      # agent hook: after edit
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope domain=engineering,subject_type=python  # import rules
rulerepo-export --project backend-api --output rules.yaml                              # export rules
rulerepo-context update --file CLAUDE.md                                              # refresh CLAUDE.md rules section
rulerepo-policy list                                                                  # list ABAC policies
rulerepo-policy grant --principal group:legal-team --action rule.edit --domain legal  # grant policy
```

### MCP Server

```bash
uv run rulerepo-mcp                                              # stdio (local, for Claude Code)
MCP_TRANSPORT=streamable-http uv run rulerepo-mcp                # HTTP (remote agents)
```

### Whole repo (from root)

```bash
docker compose up --build
docker compose down -v          # tear down + wipe volumes
docker compose logs -f server   # tail server logs
uv run python -m pytest         # run all tests
make check                      # format + lint + test
```

---

## 6. Coding Conventions

### 6.1 Python (server + clients)

- **Python 3.13**. Use modern syntax: built-in generics (`list[str]`, `dict[str, int]`), `match` where it improves clarity.
- **Type hints are mandatory** on all public functions. mypy must pass on `src/`.
- **Formatter and linter**: `ruff` (both linting and formatting). Configure via `pyproject.toml`. No `black`, no `isort` (ruff covers both).
- **Naming**: snake_case for functions/vars, PascalCase for classes, SCREAMING_SNAKE_CASE for constants. Module names lowercase.
- **Docstrings**: Google style. Required on all public APIs.
- **Errors**: define a project-specific exception hierarchy under `rulerepo_server.errors` / `rulerepo.errors`. Never raise bare `Exception`.
- **Logging**: `structlog` with JSON output. Never `print()` outside of one-off scripts.
- **Pydantic v2** for all data validation at API boundaries.
- **Tests**: `pytest` + `pytest-asyncio`. Aim for unit tests on pure logic, integration tests against the docker-compose stack.

### 6.2 TypeScript (frontend)

- **Strict TS**: `"strict": true` in `tsconfig.json`. No `any` without justification.
- **App Router** (Next.js 15 idioms). Server Components by default, Client Components only when needed.
- **Tailwind**: prefer utility classes over custom CSS. Centralize design tokens in `tailwind.config.ts`.
- **State**: prefer Server Components and URL state. For client state, `zustand`. For server-state caching, `@tanstack/react-query`.
- **Components**: PascalCase files, one component per file unless tightly coupled.
- **API calls**: generated TypeScript client from the backend's OpenAPI spec. Do not hand-write types that exist in the API contract.
- **Persona awareness**: every page lives under `app/(personas)/{persona}/` or `app/(shared)/`. Persona is derived from the URL prefix. Components imported from `(shared)` must not depend on persona; persona-specific logic lives in the persona directory.
- **Vocabulary**: per-persona vocabulary maps live in `app/(personas)/{persona}/vocabulary.ts`. Use them via a `usePersonaTerm()` hook in shared components.
- **Linting**: ESLint + Prettier. `pnpm lint` must pass.

### 6.3 Commits / branches

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- Branch from `main`. Open PRs even for solo work — keeps history reviewable.

---

## 7. Backend Architecture Notes

The server is a single FastAPI application that exposes:

- **REST API** at `/api/v1/...` for CRUD on rules, documents, evaluations.
- **Universal Submissions API** at `/api/v1/submissions` — the canonical intake for any `EvaluationSubject` kind. Prefer this over `POST /api/v1/evaluate` for new integrations.
- **Evaluate API** at `/api/v1/evaluate` — legacy entry point for code-aware compliance checking. Internally constructs a `CodeChangeSubject` and forwards to the Submissions pipeline.
- **Intent API** at `/api/v1/intent` — classifies natural-language queries and routes to handlers.
- **Intelligence API** at `/api/v1/intelligence/...` — health scoring, analytics, recommendations.
- **Discovery API** at `/api/v1/discover/...` — automatic rule discovery from code, configs, PR comments, documents.
- **Feedback API** at `/api/v1/feedback/...` — correction feedback loop.
- **Federation API** at `/api/v1/federations/...` — cross-project rule federation.
- **Playground API** at `/api/v1/playground/...` — sandbox evaluation and test cases.
- **Alerts API** at `/api/v1/alerts/...` — proactive alert management.
- **Snapshots API** at `/api/v1/snapshots/...` — versioned rule set deployment.
- **Proposals API** at `/api/v1/proposals/...` — collaborative governance workflow.
- **Governance API** at `/api/v1/governance/...` — ABAC policy management.
- **Translations API** at `/api/v1/rules/{id}/translations` — multilingual equivalence.
- **MCP Server** on a separate port (8001) for AI agent tool integration.
- **Deferred routers** (feature-flagged off by default): gateway external intake, marketplace, advanced autonomous agent governance.

### 7.1 Internal Module Layout

```
src/rulerepo_server/
├── main.py                           # FastAPI app factory; loads Domain Packs at startup
├── api/v1/                           # routers
├── core/
│   ├── config.py                     # Settings (feature flags, model IDs, secrets)
│   ├── feature_flags.py              # central flag registry
│   ├── logging.py
│   ├── errors.py
│   ├── auth.py                       # principal resolution
│   └── deps.py                       # FastAPI dependencies
├── domain/
│   ├── rule.py                       # Rule, RuleKind, RuleBody variants
│   ├── scope.py                      # Scope (multi-axis)
│   ├── evaluation_subject.py         # EvaluationSubject base + variants
│   ├── verdict.py                    # Verdict, ReasonGraph
│   ├── translation.py                # TranslationLink
│   └── governance.py                 # GovernancePolicy
├── services/
│   ├── evaluation/
│   │   ├── service.py                # orchestrator — dispatches on subject.kind
│   │   ├── subjects/
│   │   │   ├── code_change.py        # context assembler + selector for code
│   │   │   ├── business_event.py
│   │   │   ├── document_artifact.py
│   │   │   ├── transaction.py
│   │   │   ├── communication.py
│   │   │   └── decision_request.py
│   │   ├── deterministic/
│   │   │   ├── runner.py             # entry point — dispatches on rule.kind
│   │   │   ├── numeric_evaluator.py  # asteval-based expressions
│   │   │   ├── schema_evaluator.py   # Pydantic-based predicate
│   │   │   ├── state_machine_evaluator.py
│   │   │   └── lookup_evaluator.py   # table-driven lookups
│   │   ├── llm_judge/
│   │   │   ├── runner.py             # entry point — handles normative / exception / principle
│   │   │   ├── batch_evaluator.py
│   │   │   └── single_evaluator.py
│   │   ├── rule_selector.py          # scope-based + embedding-based selection
│   │   ├── graph_resolver.py         # Neo4j relationship resolution
│   │   └── verdict_aggregator.py
│   ├── extraction/
│   │   ├── pipeline.py               # orchestrator
│   │   ├── structural/               # PDF/MD/text structure parsers
│   │   ├── normative_detection.py
│   │   ├── coref_resolution.py
│   │   ├── metadata_inference.py
│   │   └── (analyzers live in Domain Packs; loaded via registry)
│   ├── intelligence/                 # essentials only — health, top violations, basic dashboard
│   ├── context_delivery/             # smart rule selection + formatting; persona-aware
│   ├── discovery/                    # cross-domain orchestrator; analyzers from Domain Packs
│   ├── feedback/                     # correction capture + flywheel for any subject kind
│   ├── federation/
│   ├── playground/                   # sandbox + test cases for all subject kinds
│   ├── snapshots/
│   ├── proposals/
│   ├── governance/                   # ABAC policy resolution
│   ├── multilingual/                 # translation link CRUD + equivalence verification
│   ├── domain_packs/
│   │   ├── loader.py                 # scans packages/domain-packs at startup
│   │   ├── registry.py               # registries: prompts, analyzers, templates, metadata schemas, UI hints
│   │   └── manifest.py               # pack.yaml schema
│   ├── search.py
│   ├── rule_service.py
│   └── intent.py
├── adapters/                         # postgres, elasticsearch, neo4j, gemini, files
├── mcp/                              # MCP server (tools, resources, prompts)
├── integrations/                     # GitHub webhook (optional), CI formatters
├── workers/                          # background jobs (arq): settings.py, tasks.py
└── schemas/                          # Pydantic request/response models
```

**Layering rule**: `api` depends on `services`, `services` depends on `domain` and `adapters`. `domain` depends on nothing else in the project. Do not import upward. Domain Packs depend only on a stable `packages/domain-packs/_core/` interface — they must not import from the server's internal modules directly.

**Async**: the API layer is fully async. DB calls use `asyncpg` (or `sqlalchemy[asyncio]`), Elasticsearch via the async client, Neo4j via the official async driver, Gemini via `google-genai`.

---

## 8. Frontend Notes (Persona-Aware)

The frontend is the operator console for the Rule Repository. **Personas drive everything visible.** Engineering, Legal, HR, Finance, Sales, and Compliance personas each have their own landing dashboard, sidebar, vocabulary, and default filters.

```
apps/frontend/app/
├── (personas)/
│   ├── engineering/
│   │   ├── layout.tsx                # engineer-style sidebar, code-themed
│   │   ├── page.tsx                  # code compliance dashboard
│   │   ├── playground/               # code editor playground
│   │   ├── rules/                    # engineering-domain rules listing
│   │   ├── discovery/                # engineering discovery (CLAUDE.md, linters)
│   │   └── ...
│   ├── legal/
│   │   ├── layout.tsx                # legal-style sidebar
│   │   ├── page.tsx                  # contract review queue
│   │   ├── contracts/                # contract review workflow
│   │   ├── clauses/                  # clause library
│   │   ├── jurisdictions/
│   │   └── ...
│   ├── hr/
│   │   ├── page.tsx                  # employee event compliance dashboard
│   │   ├── events/                   # event review queue
│   │   └── employees/
│   ├── finance/
│   │   ├── page.tsx                  # transaction approval queue
│   │   ├── transactions/
│   │   └── policies/
│   ├── sales/
│   │   ├── page.tsx                  # deal & discount review
│   │   └── deals/
│   └── compliance/
│       ├── page.tsx                  # cross-domain compliance summary
│       └── audit/
└── (shared)/
    ├── rules/[id]/                   # rule detail (persona-tinted)
    ├── search/
    ├── proposals/
    ├── notifications/
    ├── settings/
    └── login/
```

**Persona switching**: the top-of-page persona switcher updates a `persona` cookie and rewrites the URL prefix. Deep links work across personas.

**Rule detail page**: shared (`(shared)/rules/[id]/`) but the rule's `scope.domain` and the active persona together drive which sections are highlighted (e.g., legal rules show "jurisdiction" prominently; HR rules show "applicable employee class").

**Playground**: `(shared)/playground/` provides an input-mode switcher: code editor, business event form, document section, transaction, communication. The mode is set by the active persona's default but can be overridden.

**Graph view**: Neo4j-backed; uses `react-flow` or `cytoscape`. Pick one and stick with it.

---

## 9. Gemini API Integration (read carefully)

The LLM layer is the heart of this system. Get this right.

### 9.1 SDK
- **Use `google-genai`** (the new unified SDK). Do **not** use the deprecated `google-generativeai`.
- Install via uv: `uv add google-genai httpx`.

### 9.2 Models

| Use case | Model ID | Why |
|---|---|---|
| High-throughput, routine tasks (search ranking, simple extraction, classification) | `gemini-3-flash-preview` | fast, cheap |
| High-stakes judgment (rule extraction QC, conflict detection, evaluation of CRITICAL rules, principle-level evaluation) | `gemini-3.1-pro-preview` | strongest reasoning |

Centralize model selection in one config module (`core/llm.py`). Never hardcode model IDs in business logic — always read from config.

### 9.3 Mandatory rules when calling Gemini

- **Do NOT change `temperature`** away from the default (1.0). Lower temperatures degrade Gemini 3 reasoning quality and can cause loops. If a caller insists on determinism, push them to the deterministic evaluation layer (§14.9) instead.
- Use **`thinking_level`** (not the legacy `thinking_budget`). Valid values: `minimal`, `low`, `medium`, `high`. Default to `low` for high-throughput tasks, `high` for judgment tasks.
- For function calling, **thought signatures must be cycled through** every turn. The `google-genai` SDK and standard chat history handle this automatically — do not strip signatures from history.
- For PDFs in document processing, set `media_resolution: "media_resolution_medium"` (560 tokens/page). Going higher rarely helps OCR and increases token cost.
- Use **structured output** (`response_mime_type="application/json"` + `response_json_schema`) for any call that must return data the system parses. Do not regex out fields from free-form LLM text.

### 9.4 Document ingestion (PDF, text, markdown)

- **PDFs**: upload via the **Files API** (`client.files.upload(...)`) for documents > a few pages. Files API is free, files persist 48 hours, max 50 MB / 1000 pages.
- For small / one-shot PDFs, inline `Part.from_bytes(data=..., mime_type='application/pdf')` is fine.
- **Text and markdown**: pass as plain text. Note that Gemini "document understanding" only meaningfully renders PDFs; for `.md`/`.txt`, treat them as text-only inputs (no charts, no formatting interpretation).
- Each PDF page is roughly 258 tokens for image content; extracted native text is included free.
- The extraction pipeline is **domain-adaptive**: structural extraction first, then domain-specific metadata inference via Domain Pack prompts. Do not bypass the pipeline from random parts of the codebase.

### 9.5 Cost and latency discipline

- Cache LLM responses by `hash(inputs + model + prompt_version)` in Postgres. Invalidate on rule revision.
- Use `gemini-3.1-flash-lite-preview` only if explicitly approved for a use case where Flash is overkill. Default is `gemini-3-flash-preview`.
- Long-context calls (rule corpus + large doc) should use **context caching** for repeated reuse.
- **Prefer the deterministic layer for arithmetic, schema, and lookup checks.** Do not send a numeric comparison to the LLM; send it to the `numeric_evaluator`.

### 9.6 Determinism and audit

- Every LLM call that produces a verdict, a candidate rule, or a relationship suggestion **must** log: model ID, prompt version (a content hash), inputs, outputs, latency, timestamp. This goes to the audit log.
- Prompts live in `packages/domain-packs/{domain}/prompts/` (domain-specific) or `services/{area}/prompts/` (cross-cutting). All prompts are versioned in git. No inline strings scattered across the codebase.

---

## 10. Data Layer

### 10.1 PostgreSQL (system of record)

- Stores rules, revisions, source documents, evaluations, audit log, proposals, governance policies, translation links.
- Migrations: `alembic`. One head per branch; rebase migrations before merging.
- The audit log table is **append-only**. Enforce with a Postgres trigger that rejects updates/deletes. Add a hash chain column linking each row to the previous row.
- **`Rule.scope` is JSONB**. Use:
  ```sql
  CREATE INDEX ix_rules_scope_domain        ON rules ((scope->>'domain'));
  CREATE INDEX ix_rules_scope_subject_type  ON rules ((scope->>'subject_type'));
  CREATE INDEX ix_rules_scope_org_unit      ON rules ((scope->>'org_unit'));
  CREATE INDEX ix_rules_scope_attributes    ON rules USING GIN ((scope->'attributes'));
  ```

### 10.2 Elasticsearch (search)

- Index `rules` with: `statement` (analyzed by language), `tags`, `scope.domain`, `scope.subject_type`, `scope.org_unit`, `scope.attributes` (flattened), `modality`, `kind`, `effective_period`, `language`, `embedding` (dense_vector).
- Use BM25 + kNN hybrid scoring. Rerank top-k with the LLM only when the user requests "smart" search.
- Re-index on rule revision; do not run partial updates that risk drift.
- Multi-language analyzers: configure `language`-specific analyzers (`japanese`, `english`, etc.) and route based on `Rule.language`.

### 10.3 Neo4j (relationship graph)

- One node label: `Rule`. Node `id` matches the Postgres rule ID.
- Relationships: `REFINES`, `OVERRIDES`, `CONFLICTS_WITH`, `DEPENDS_ON`, `DERIVES_FROM`, `SUCCEEDS`, `TRANSLATES`. Direction matters and is documented in PROJECT.md §6.4.
- Postgres is the source of truth for rule existence; Neo4j is a derived projection of relationships. If they disagree, Postgres wins and Neo4j is rebuilt.
- Provide a reconciler script (`scripts/reconcile_graph.py`) that rebuilds Neo4j from Postgres.

---

## 11. Testing

- **Unit tests**: pure logic in `domain/`. No external services. Fast.
- **Integration tests**: spin up docker-compose services in CI. Use `testcontainers-python` if running in CI without compose.
- **LLM tests**: never call the real Gemini API in unit tests. Use a mock client. For integration, gate behind an env flag (`RULEREPO_LIVE_LLM=1`) and a pytest marker (`@pytest.mark.live_llm`).
- **Frontend tests**: Vitest + React Testing Library for components; Playwright for end-to-end if added later.
- **Eval harness**: a separate test suite that validates LLM-driven features (rule extraction quality, conflict detection precision/recall, evaluation accuracy) against curated fixtures per Domain Pack. Runs nightly, not on every PR.
- **Parity tests**: for any pipeline being generalized (e.g., during migration of `CodeChangeSubject` into the subject-dispatched engine), write tests that run the old and new code paths on the same input and assert identical output. Keep parity tests in CI until the old path is removed.
- **Cross-domain coverage**: at least one integration test per `EvaluationSubject` kind. At least one extraction test per Domain Pack.

---

## 12. Environment Variables

All env vars live in `.env.example`. Never commit `.env`. Required for local dev:

```bash
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

# Optional GitHub Integration (off by default in local mode)
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=
GITHUB_TOKEN=

# Multilingual
TRANSLATION_VERIFICATION_ENABLED=true
TRANSLATION_EQUIVALENCE_THRESHOLD=0.85

# Domain Packs
DOMAIN_PACKS_DIR=/app/packages/domain-packs
DOMAIN_PACKS_ENABLED=engineering,legal,hr,finance,sales,communication

# Feature Flags — Phase 6 features deferred per refocus
FEATURE_MARKETPLACE_ENABLED=false
FEATURE_GATEWAY_EXTERNAL_INTAKE_ENABLED=false
FEATURE_OBSERVABILITY_DIGEST_DELIVERY_ENABLED=false
FEATURE_GITHUB_APP_ENABLED=false
FEATURE_AGENT_TRUST_AUTO_PROMOTION_ENABLED=false
FEATURE_AGENT_NEGOTIATION_ENABLED=false
FEATURE_MULTI_AGENT_SESSIONS_ENABLED=false

# Feature Flags — Refocus migration toggles
FEATURE_EVALUATION_SUBJECT_V2_ENABLED=true
FEATURE_STRUCTURED_SCOPE_ENABLED=true
FEATURE_RULE_KIND_POLYMORPHISM_ENABLED=true
FEATURE_DOMAIN_PACKS_ENABLED=true
FEATURE_HYBRID_EVALUATION_ENABLED=true
FEATURE_PERSONA_ROUTING_ENABLED=true
FEATURE_ABAC_GOVERNANCE_ENABLED=false   # off until Step 4

# Alerts (compute internally; do not deliver externally in local mode)
ALERT_WEBHOOK_URL=
```

When you add a new env var, update `.env.example` in the same change.

---

## 13. Important Rules for Claude Code

These are non-negotiable. Violating them breaks the system, the refocus, or wastes review time.

1. **Read PROJECT.md before designing anything new.** Domain decisions belong there, not here.
2. **Treat code change as one subject kind among many.** Do not assume code in new code. Use `EvaluationSubject` and dispatch on `kind`.
3. **Put domain-specific behavior in Domain Packs.** If you find yourself writing legal/HR/finance logic in `services/` or the frontend `(shared)/`, stop and move it to the appropriate Domain Pack.
4. **Run linters, formatters, and type checkers before claiming a task is done.** `ruff`, `mypy`, `pnpm lint`, `pnpm typecheck`. CI will reject otherwise.
5. **Never commit secrets.** No API keys, no DB passwords, nothing in code. Use `.env` and `.env.example`.
6. **Never tweak Gemini `temperature`.** Default 1.0 stays. For deterministic answers, use the deterministic evaluation layer, not lower temperature.
7. **Never use deprecated Gemini params.** Use `thinking_level`, not `thinking_budget`. Use `google-genai`, not `google-generativeai`.
8. **Never bypass the extraction or evaluation pipelines.** There is one place that talks to Gemini for ingestion, and one orchestrator per pipeline. Random services should not invent their own.
9. **Never write to the audit log table from application code.** Only the evaluation/extraction services write, and only through the audit-log adapter that enforces hash chaining.
10. **Never make Postgres and Neo4j (and Elasticsearch) disagree silently.** If you write to one, write to the others through the same service. If you can only write to one, queue the other change.
11. **Never delete rules.** Use `effective_period.valid_until` to retire them. Past evaluations must remain re-explainable.
12. **Never re-enable feature-flagged-off subsystems casually.** Marketplace, gateway external intake, observability digest delivery, GitHub App centrality, and advanced agent governance are off by default for a reason. Re-enabling requires a discussion and a PROJECT.md update.
13. **Keep `docker compose up --build` working.** If your change breaks the local stack, fix it before merging. The local stack is the developer onboarding path.
14. **Update PROJECT.md, CLAUDE.md, and IMPROVEMENT.md** when introducing a new dependency, service, or architectural decision. Code without doc updates does not ship.
15. **Prefer fewer dependencies.** Every added library is a long-term cost. Justify additions in the PR description.
16. **Write structured logs, not `print`.** Logs are operational data.
17. **Tests for LLM-driven features must mock the LLM** unless the test is explicitly an eval test (`@pytest.mark.live_llm`).
18. **Follow migration discipline (§15).** Schema changes are additive-first; refactors are guarded by parity tests; rollouts are feature-flagged.
19. **When unsure, ask.** Open an issue or a draft PR with the question. Do not guess on domain semantics — wrong rules are worse than no rules.

---

## 14. Refocus Implementation Guidance

These are architecture decisions and patterns for the ongoing refocus. Read before implementing any work that touches the relevant areas.

### 14.1 `EvaluationSubject` Abstraction

- `domain/evaluation_subject.py` defines `EvaluationSubject` (abstract) and concrete variants: `CodeChangeSubject`, `BusinessEventSubject`, `DocumentArtifactSubject`, `TransactionSubject`, `CommunicationSubject`, `DecisionRequestSubject`.
- Each variant has a corresponding context assembler under `services/evaluation/subjects/{kind}.py`.
- `services/evaluation/service.py` dispatches on `subject.kind`. Do not branch on subject shape inside the orchestrator.
- API: `POST /api/v1/submissions` accepts any subject kind via a Pydantic discriminated union on `kind`. `POST /api/v1/evaluate` (legacy) constructs `CodeChangeSubject` internally.
- For new integrations, prefer the Submissions API. Legacy `/evaluate` remains for backward compatibility.

### 14.2 Structured `Scope` Migration

- `domain/scope.py` defines `Scope` with `domain`, `org_unit`, `subject_type`, `attributes`.
- Database: `scope` is JSONB. Migration adds the column, backfills from legacy string, and switches reads to the new column.
- During the migration window, `rule_service.py` reads from `scope_v2` (the new JSONB column) and falls back to the legacy string if absent. Writes go to both.
- Elasticsearch mappings include `scope.domain`, `scope.subject_type`, `scope.org_unit`, `scope.attributes`. Reindex on switch.
- Federation continues to walk `org_unit` ancestry; update the federation resolver to use the structured form.
- Legacy string scopes (`"engineering/python"`) normalize as `{domain: "engineering", subject_type: "python_source"}`.

### 14.3 Rule Kind Polymorphism

- `domain/rule.py` defines `RuleKind` enum: `NORMATIVE`, `COMPUTATIONAL`, `PROCEDURAL`, `DEFINITIONAL`, `PRINCIPLE`.
- `Rule.body` is a discriminated union of `NormativeBody`, `ComputationalBody`, `ProceduralBody`, `DefinitionalBody`, `PrincipleBody`. Migration adds `kind` (default `NORMATIVE`) and `body` (derived from existing fields for backfill).
- Evaluator dispatch: `services/evaluation/deterministic/runner.py` routes by `rule.kind`. `computational` always uses `numeric_evaluator`. `normative` may use the deterministic layer for its embedded predicate, then fall through to the LLM layer. `principle` skips the deterministic layer entirely.
- `ComputationalBody` carries `expression`, `required_inputs`, `unit`, optional `exception_predicate`. Expressions are evaluated by `asteval` (no I/O, no imports, no attribute access).
- New rule kinds added in this order: `computational` first, then `definitional`, then `procedural`, then `principle`. Each goes through a vertical slice with one real rule before stabilization.

### 14.4 Domain Pack Architecture

- Domain Packs live under `packages/domain-packs/{domain}/`.
- Manifest (`pack.yaml`) declares `domain`, `name`, `version`, `subject_types`, `metadata_extensions`, `default_modality`, `preferred_evaluator_subject_kinds`.
- Pack contributions are registered at server startup by `services/domain_packs/loader.py`:
  - **Prompts**: registered into the prompt registry, keyed by `(domain, purpose)` (e.g., `(legal, evaluate)`).
  - **Analyzers**: registered into the discovery analyzer registry.
  - **Templates**: registered into the template catalog (importable via `POST /api/v1/rules/import`).
  - **Metadata schema extensions**: registered into the `domain_attributes` JSON schema validator.
  - **(Optional) UI hints**: registered into a key→component-name map; the frontend looks them up by `(domain, view)`.
- A Domain Pack must depend only on `packages/domain-packs/_core/`. It must not import from `apps/server/`.
- The `engineering` pack is the **second** implementation, not the reference. Test the abstraction against `legal` first; if the manifest cannot express `legal`, fix the abstraction before declaring it stable.

### 14.5 Domain-Adaptive Extraction Pipeline

- `services/extraction/pipeline.py` is the orchestrator. Stages: structural → normative detection → coreference resolution → domain-specific metadata inference → relationship suggestion → human review.
- The structural stage uses Gemini File API. For PDFs, a two-call pattern:
  1. First call: extract section hierarchy as structured JSON.
  2. Second call: for each leaf section, extract normative sentences with cross-references resolved.
- Domain-specific behavior (Japanese legal 条/項/号 anchoring, Subcontracting Act metadata, HR applicable-employee-class extraction) lives in the Domain Pack's analyzers, dispatched by the pipeline based on the detected (or declared) domain.
- For `.md`/`.txt`, skip the structural PDF stages and use markdown/text section parsers in `services/extraction/structural/`.

### 14.6 Persona-Aware Frontend

- App Router structure: `app/(personas)/{persona}/` and `app/(shared)/`.
- Persona switcher updates a `persona` cookie and the URL prefix. Deep links work across personas.
- Each persona's `layout.tsx` defines sidebar, header, and persona-specific theme.
- Vocabulary per persona is in `app/(personas)/{persona}/vocabulary.ts`. Shared components access vocabulary via `usePersonaTerm("compliance_rate")`.
- Default landing page per persona is `app/(personas)/{persona}/page.tsx`. Use Server Components for SSR-fetched dashboard data.
- Rule detail page is shared but adapts: the rule's `scope.domain` together with the active persona drives which sections are emphasized.
- Playground accepts all subject kinds; input mode selector is on the playground page.

### 14.7 Universal Submissions Endpoint

- `POST /api/v1/submissions` is the canonical intake. Request body schema uses Pydantic discriminated unions on `subject.kind`.
- Response: `verdict`, `violations[]`, `reason_graph`, `suggested_fix`, `applied_rules[]`, `deterministic_results[]`, `llm_results[]`.
- Idempotency: accept an optional `submission_id`; return the same verdict for the same id within a configurable window.
- The legacy `POST /api/v1/evaluate` wraps the submissions endpoint by constructing a `CodeChangeSubject`. Do not duplicate logic across the two endpoints.
- `services/evaluation/service.py` exposes a single `evaluate(subject, ...)` method. Routers translate HTTP requests into `EvaluationSubject` and call this method.

### 14.8 Multilingual Rules

- `domain/rule.py`: `Rule.language` (default `en`) and `Rule.translations: list[TranslationLink]`.
- Storage: `rule_translations(rule_id, sibling_rule_id, language, verified_at, score)` join table.
- API: `GET /api/v1/rules?language=ja`, `GET /api/v1/rules/{id}/translations`, `POST /api/v1/rules/{id}/translations`.
- Background worker (`verify_translations`, cron daily): re-runs Gemini equivalence checks; updates scores; flags drops below `TRANSLATION_EQUIVALENCE_THRESHOLD`.
- Evaluation accepts `Accept-Language` and prefers same-language rules; falls back to translation sibling when no native match exists.
- Search analyzer is selected by `Rule.language` (Elasticsearch `japanese`, `english`, etc.).

### 14.9 Hybrid Evaluation Architecture

- Two layers: deterministic and LLM. `services/evaluation/deterministic/` and `services/evaluation/llm_judge/`.
- For each selected rule, the orchestrator first calls the deterministic runner. The runner dispatches on `rule.kind` and the rule body's contents:
  - `kind=computational` → `numeric_evaluator` evaluates `expression` via `asteval`.
  - `kind=normative` with numeric/schema predicate → partial deterministic check, partial LLM follow-up.
  - `kind=definitional` → reference lookup.
  - `kind=procedural` → state machine check.
  - `kind=principle` → skip deterministic, go straight to LLM.
- LLM layer receives the deterministic result as context: "The deterministic check found X. Confirm whether any exception applies and produce the final verdict."
- Both layers contribute to the audit log: which layer ran, what each produced, and the final aggregated verdict.
- `asteval` configuration: no I/O, no imports, no attribute access, no `__builtins__` exposure. Reject anything else.

### 14.10 ABAC Governance Model

- `domain/governance.py`: `GovernancePolicy` with `domain`, `org_unit`, `action`, `principals`, `effect`.
- Resolution order: explicit deny > explicit allow > inherited allow > default deny.
- `services/governance/resolver.py` evaluates policies. Cache by `(principal, action, domain, org_unit)` for the request lifetime.
- Migration: legacy per-rule Owner/Approver/Reader continues to function as a derived view. New writes go to ABAC policies. After a release, deprecate the legacy form.
- CLI: `rulerepo-policy list/grant/revoke`.
- Feature flag: `FEATURE_ABAC_GOVERNANCE_ENABLED=false` until Step 4 of the roadmap.

### 14.11 Phase 6 De-Scoping & Feature Flags

The following subsystems exist in code but are flagged off by default. Do not silently re-enable them.

| Subsystem | Flag | Action if disabled |
|---|---|---|
| Marketplace | `FEATURE_MARKETPLACE_ENABLED` | Router returns 404. Sidebar entry hidden. Models persist for re-enablement. |
| Gateway external intake | `FEATURE_GATEWAY_EXTERNAL_INTAKE_ENABLED` | Webhook ingress endpoints return 404. Internal-API gateway flow remains. |
| Observability digest delivery | `FEATURE_OBSERVABILITY_DIGEST_DELIVERY_ENABLED` | Compute metrics; do not deliver. Team comparison page hidden. |
| GitHub App | `FEATURE_GITHUB_APP_ENABLED` | Webhook endpoints return 404. CLI `rulerepo-check` remains. |
| Agent trust auto-promotion | `FEATURE_AGENT_TRUST_AUTO_PROMOTION_ENABLED` | Trust level remains manual. Profile creation still works. |
| Agent negotiation | `FEATURE_AGENT_NEGOTIATION_ENABLED` | Negotiation endpoints return 404. |
| Multi-agent sessions | `FEATURE_MULTI_AGENT_SESSIONS_ENABLED` | Session endpoints return 404. |

When adding code that interacts with these subsystems, gate it behind the flag and ensure the subsystem is not a hard dependency of any default code path.

### 14.12 Domain Template Library

Each Domain Pack ships at least one YAML template under `packages/domain-packs/{domain}/templates/`. Initial targets:

| Template | Pack | Rules | Modality | Notes |
|---|---|---|---|---|
| `legal-contracts-jp` | legal | 10 | MUST/MUST_NOT | NDA, anti-social-forces clause, governing law, etc. |
| `legal-contracts-en-us` | legal | 10 | MUST/MUST_NOT | Limitation of liability, indemnification, etc. |
| `hr-attendance-jp` | hr | 10 | MUST + computational | 45h/month cap, 36-agreement clauses |
| `hr-conduct` | hr | 8 | MUST | Harassment, conflict of interest, social media |
| `finance-expense-jp` | finance | 10 | MUST + computational | Entertainment limits, receipt thresholds |
| `finance-procurement` | finance | 8 | MUST | Subcontracting Act compliance, three-quote rule |
| `sales-pricing` | sales | 8 | MUST + MUST_NOT | Discount limits, resale price maintenance |
| `communication-marketing-jp` | communication | 8 | MUST_NOT | 景品表示法, 薬機法, regulated industries |

All non-engineering templates ship as `maturity_level=experimental` (shadow mode). Each rule includes statement, modality, severity, structured scope, rationale, following example, violation example, and at least one playground test case. Computational rules include a structured `body` with `expression` and `required_inputs`.

---

## 15. Migration Discipline

Several refocus items involve schema or pipeline changes. Follow this discipline to avoid disrupting the working system.

### 15.1 Additive-First Migrations

For every schema change:

1. Add the new column / table without dropping the old one.
2. Backfill data using a one-off migration script.
3. Deploy code that reads from new and writes to both old and new (dual-write).
4. After verification, switch reads to new.
5. Stop writing to old.
6. Drop the old column / table only after a stable period (one release minimum).

This applies particularly to:
- `Rule.scope` (string → JSONB): use `scope_v2 JSONB` alongside `scope` initially.
- `Rule.kind` and `Rule.body`: add as nullable; default to `normative` with body derived from existing fields.
- `Rule.language`: add as nullable; default to `"en"`.
- Translation links: new join table; no overwrite of existing data.

### 15.2 Feature-Flag-Driven Rollouts

Every new subsystem ships behind a flag, default off in production-style envs, default on in development. The flag registry lives in `core/feature_flags.py` and is reflected in `.env.example`.

### 15.3 Parity Tests

For any pipeline being generalized, write a "parity test" that runs the old code path and new code path on the same input and asserts identical output. Keep parity tests in CI until the old path is removed.

Examples:
- During the `EvaluationSubject` migration, parity test: legacy `POST /api/v1/evaluate` with a diff vs. new `POST /api/v1/submissions` with the same diff as `CodeChangeSubject`.
- During the `Scope` migration, parity test: legacy string scope filter vs. new structured `Scope` filter producing the same rule selection.

### 15.4 Documentation Co-Evolution

Update `PROJECT.md` and `CLAUDE.md` with every architectural change (Rule 14 in §13). Specifically:

- `PROJECT.md` §6 (Domain Model) tracks `Scope`, `RuleKind`, `EvaluationSubject`, `Domain Pack` shapes.
- `CLAUDE.md` §14 tracks implementation guidance for the same areas.
- When a Domain Pack is added, both files note it.
- When a feature flag's default flips, both files note it.

### 15.5 Removal of Legacy Paths

After Step 5 (stabilization) in the roadmap, legacy paths that have been parity-tested and superseded should be removed in a dedicated `chore: remove legacy X` PR. Do not bundle removal with new features.

---

## 16. References

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
- asteval (sandboxed expression evaluation): https://lmfit.github.io/asteval/
- arq (Redis-backed job queue): https://arq-docs.helpmanual.io/
- FastMCP: https://github.com/jlowin/fastmcp

---

*This file is a contract. If you (Claude Code) find a conflict between this file and the user's request, surface the conflict and ask. Do not silently override. The contract evolves as the refocus progresses — propose changes through PRs that update this file alongside the code.*

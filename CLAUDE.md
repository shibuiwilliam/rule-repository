# CLAUDE.md

> Operational guide for Claude Code when working on the **Rule Repository** project.
> For the project vision, domain model, and roadmap, see **PROJECT.md**.
> For the analysis that led to the v1 direction, see **IMPROVEMENT.md**.

This file is the working contract between you (Claude Code) and the project. Read it before making changes. When in doubt, follow the rules in this file over your prior conventions. If you find a conflict between this file and the user's request, surface the conflict and ask.

---

## 1. Project at a Glance

The Rule Repository stores natural-language rules and makes them searchable, evaluable, and enforceable across multiple functional domains: legal, HR, finance, sales, engineering, communication, and beyond. See `PROJECT.md` for the full design.

**Current focus**: **v1 — Cross-Organizational Generalization**. The system has solid v0 foundations focused on engineering use cases. v1 generalizes those foundations so every functional team can use the same rule corpus and the same evaluation engine.

**This repository is a monorepo** containing the backend server, frontend, Python client SDKs, CLI tools, domain packs, and local dev infrastructure. The entire stack runs on **Docker Compose**.

---

## 2. Tech Stack (authoritative)

| Layer | Technology | Notes |
|---|---|---|
| Backend | **Python 3.13** + FastAPI | Library management with **uv** |
| Frontend | **TypeScript**, **React 19**, **Next.js 15**, **Tailwind CSS** | Library management with **pnpm** |
| Python clients | **Python 3.13** (Rule Client, Agentic Rule Client) | Library management with **uv** |
| LLM | **Gemini 3 Flash** (`gemini-3-flash-preview`) and **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`) | via `google-genai` SDK; provider is abstracted behind the `Evaluator` interface |
| Document parsing | **Gemini Files API** + document understanding | PDF, text, markdown |
| Relational DB | **PostgreSQL 17** | rules, revisions, audit log; `frozen` schema for disabled features |
| Search | **Elasticsearch 8.17** | full-text + hybrid search; per-domain indexing |
| Graph DB | **Neo4j 5** | rule relationships |
| Job Queue | **arq** + **Redis 7** | Background tasks |
| Sandbox expression | **`asteval`** | Deterministic evaluation for `COMPUTATIONAL` rules |
| Local orchestration | **Docker Compose** | dev + integration tests; 8 services |

Do **not** introduce additional frameworks or services without updating this file and PROJECT.md first.

---

## 3. Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                 # FastAPI backend (Python 3.13, uv)
│   │   ├── pyproject.toml
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/         # REST routers (rules, search, evaluate, submissions, intent, …)
│   │   │   ├── core/           # config, logging, errors, auth, middleware, feature_flags, PII
│   │   │   ├── domain/         # Rule, Scope, RuleKind, EvaluationSubject, Verdict (pure)
│   │   │   ├── services/
│   │   │   │   ├── evaluation/
│   │   │   │   │   ├── dispatcher.py         # routes subjects to handlers
│   │   │   │   │   ├── handlers/
│   │   │   │   │   │   ├── code_change/      # existing engineering logic
│   │   │   │   │   │   ├── business_event/   # HR / CRM / etc.
│   │   │   │   │   │   ├── document_artifact/# legal contracts, marketing copy
│   │   │   │   │   │   ├── transaction/      # finance: expense, procurement
│   │   │   │   │   │   ├── communication/    # email, chat, public posts
│   │   │   │   │   │   └── decision_request/ # "should I do X?"
│   │   │   │   │   ├── deterministic/        # computational/procedural/definitional eval
│   │   │   │   │   ├── rule_selector.py      # multi-axis scope-aware selection
│   │   │   │   │   └── llm_judge.py          # shared LLM-call infrastructure
│   │   │   │   ├── extraction/
│   │   │   │   │   ├── structural/           # PDF → sections (domain-agnostic)
│   │   │   │   │   ├── normative/            # normative-sentence detection
│   │   │   │   │   └── domain/{legal,hr,finance,sales,engineering}/
│   │   │   │   ├── search.py                 # multi-modal search with scope filter
│   │   │   │   ├── intent.py                 # intent classification + routing
│   │   │   │   ├── discovery/                # cold-start rule discovery
│   │   │   │   ├── feedback/                 # correction loop
│   │   │   │   ├── intelligence/             # health, effectiveness, per-domain quality
│   │   │   │   ├── federation/               # org → team → project hierarchy
│   │   │   │   ├── snapshots/                # versioned rule sets
│   │   │   │   ├── playground/               # sandbox + test cases
│   │   │   │   ├── proposals/                # rule change workflow
│   │   │   │   └── domain_packs/             # pack loader, pack registry
│   │   │   ├── adapters/                     # postgres, elasticsearch, neo4j, gemini, files
│   │   │   ├── mcp/                          # MCP server (tools, resources, prompts)
│   │   │   ├── integrations/                 # optional integrations (gated)
│   │   │   ├── schemas/                      # Pydantic request/response models
│   │   │   └── workers/                      # arq workers (cron jobs)
│   │   ├── alembic/                          # database migrations
│   │   └── tests/                            # unit, integration, e2e
│   └── frontend/                             # Next.js + TS + Tailwind (pnpm)
│       ├── package.json
│       ├── app/
│       │   ├── (personas)/
│       │   │   ├── engineering/              # existing 23 pages, repackaged
│       │   │   ├── legal/                    # contract review, clause comparison
│       │   │   ├── hr/                       # policy browser, attendance alerts
│       │   │   ├── finance/                  # expense review, account mapping
│       │   │   ├── sales/                    # quote review, discount approval
│       │   │   └── compliance/               # cross-domain dashboard, audit, risk
│       │   ├── (shared)/                     # rule detail, search, settings
│       │   └── layout.tsx                    # persona switcher in top nav
│       └── components/                       # persona-agnostic UI components
├── packages/
│   ├── rule-client/                          # Python SDK (thin wrapper over server APIs)
│   ├── agentic-client/                       # Python SDK with evaluation, three modes
│   ├── cli/                                  # rulerepo-check, rulerepo-hook, rulerepo-ingest, rulerepo-export, rulerepo-context
│   └── domain-packs/                         # Domain Pack contributions
│       ├── legal/
│       ├── hr/
│       ├── finance/
│       ├── sales/
│       └── engineering/                      # the previous core implementation, repackaged
├── infra/
│   ├── docker/                               # Dockerfiles
│   ├── postgres/                             # init SQL
│   ├── elasticsearch/                        # index templates
│   └── neo4j/                                # constraints
├── sample_rules/
│   ├── coding_rules/                         # 11 engineering documents
│   ├── company_rules/                        # 7 corporate policy documents
│   ├── sales_team_rules/                     # 5 sales team documents
│   └── templates/                            # YAML templates (engineering + cross-domain)
├── scripts/                                  # seed_data, reconcile_graph, reindex, reconcile_scope_structured
├── development/                              # technical development docs
├── docs/
│   ├── domains/                              # per-domain-pack documentation
│   ├── migration/                            # A/B/C migration guide
│   └── …
├── docker-compose.yml                        # local dev stack
├── pyproject.toml                            # uv workspace root
├── pnpm-workspace.yaml
├── .env.example
├── PROJECT.md                                # project vision and specification
├── IMPROVEMENT.md                            # v1 direction analysis and proposals
└── CLAUDE.md                                 # this file
```

When adding a new package, place it under `apps/` (deployable apps) or `packages/` (libraries). Update `pyproject.toml` (uv workspace) or `pnpm-workspace.yaml` accordingly.

---

## 4. Quick Start (local dev)

The whole stack must come up with one command. If your changes break this, fix it before continuing.

```bash
cp .env.example .env            # then fill in GEMINI_API_KEY
make up                         # or: docker compose up --build -d
```

Expected services after `up`:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | REST + Submissions + Intent API |
| API docs (OpenAPI) | http://localhost:8000/docs | FastAPI Swagger UI |
| Frontend | http://localhost:3000 | Next.js dev server (persona switcher in top nav) |
| PostgreSQL | localhost:5432 | `ruledb` |
| Elasticsearch | http://localhost:9200 | search index |
| Neo4j Browser | http://localhost:7474 | rule graph |
| MCP Server | http://localhost:8001 | Streamable-HTTP MCP for agents |
| Redis | localhost:6379 | Job queue (arq) |
| arq-worker | — | Background task processor |

Frozen features (Marketplace, external gateway webhooks, etc.) are disabled by default. To enable any during development, set the corresponding `FEATURE_*_ENABLED=true` in `.env`.

---

## 5. Common Commands

### Backend (apps/server)

```bash
cd apps/server
uv sync                         # install deps
uv run uvicorn rulerepo_server.main:app --reload   # run dev server
uv run pytest                   # run tests
uv run pytest -m "not frozen"   # run all tests EXCEPT frozen-feature tests
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

### Python SDKs / CLI (packages/)

```bash
cd packages/rule-client
uv sync && uv run pytest && uv build

# CLI
rulerepo-check --diff "$(git diff origin/main...HEAD)" --format github-actions
rulerepo-hook preflight --file src/api/handler.py --agent-id claude-code
rulerepo-ingest --source claude-md --file ./CLAUDE.md --domain engineering --subject-type code_file
rulerepo-export --project backend-api --output rules.yaml
rulerepo-context generate --server http://localhost:8000 --project backend-api
```

### MCP Server

```bash
uv run rulerepo-mcp                          # stdio (local, for Claude Code)
MCP_TRANSPORT=streamable-http uv run rulerepo-mcp   # HTTP (remote agents)
```

### Whole repo (from root)

```bash
make up                         # start full stack
make down                       # stop
make reset                      # wipe volumes and rebuild
make seed                       # load sample rules across domains
make check                      # format + lint + test (run before committing)
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
- **Submissions API** at `/api/v1/submissions` for non-code subjects (the canonical cross-org entry point).
- **Evaluate API** at `/api/v1/evaluate` for code-aware compliance (now a code-specialized convenience over the dispatcher).
- **Intent API** at `/api/v1/intent` that classifies natural-language queries and routes to handlers.
- **Intelligence API** at `/api/v1/intelligence/...` for health, effectiveness, per-domain quality.
- **Discovery API** at `/api/v1/discover/...` for automatic rule discovery.
- **Feedback API** at `/api/v1/feedback/...` for the correction loop.
- **Federation API** at `/api/v1/federations/...` for hierarchical rule composition.
- **Playground API** at `/api/v1/playground/...` for sandbox evaluation.
- **Snapshots API** at `/api/v1/snapshots/...` for versioned rule set deployment.
- **Proposals API** at `/api/v1/proposals/...` for rule change workflow.
- **MCP Server** on port 8001 for AI agent tool integration.

### 7.1 Layering Rules (Strict)

```
api  →  services  →  domain
                ↓
              adapters
```

- `api` depends on `services` (and `schemas`).
- `services` depends on `domain` and `adapters`.
- `domain` depends on nothing in the project. Pure data classes, enums, protocols.
- Never import upward. Never have `domain/` import from `services/` or `adapters/`.

### 7.2 The Evaluation Dispatcher

The evaluation engine is a dispatcher over `EvaluationSubject` kinds. **Do not bypass it.** Each subject kind has a handler in `services/evaluation/handlers/{kind}/`.

```python
# services/evaluation/dispatcher.py
class EvaluationDispatcher:
    async def evaluate(self, subject: EvaluationSubject) -> EvaluationResult:
        handler = self._handlers[subject.kind]
        normalized = await handler.normalize(subject)
        rules = await handler.select_rules(normalized)
        prompt = handler.build_prompt(normalized, rules)
        verdicts = await self._llm_judge(prompt, handler.verdict_schema)
        return handler.aggregate(verdicts, rules, normalized)
```

Each handler implements `SubjectHandler`:

```python
class SubjectHandler(Protocol):
    async def normalize(self, subject) -> NormalizedSubject: ...
    async def select_rules(self, normalized) -> list[Rule]: ...
    def build_prompt(self, normalized, rules) -> str: ...
    def aggregate(self, verdicts, rules, normalized) -> EvaluationResult: ...
    @property
    def verdict_schema(self) -> dict: ...
```

**Handlers own only**: prompts (in `handlers/{kind}/prompts/`), rule selection strategy, prompt construction, aggregation.

**Handlers do NOT own**: LLM client creation, model selection, audit logging, caching. These are shared in `services/evaluation/llm_judge.py`.

### 7.3 Hybrid Evaluation

For `COMPUTATIONAL`, `PROCEDURAL`, and `DEFINITIONAL` rule kinds, evaluation begins with `services/evaluation/deterministic/`. The LLM only confirms intent and writes the human-readable reason. If they disagree → `NEEDS_CONFIRMATION`.

### 7.4 Async

The API layer is fully async. DB calls use `asyncpg` (or `sqlalchemy[asyncio]`), Elasticsearch via the async client, Neo4j via the official async driver, Gemini via `google-genai`.

---

## 8. Frontend Notes

The frontend is **persona-aware**. Each persona (Legal, HR, Finance, Sales, Engineering, Compliance) has its own home dashboard, default filters, and navigation under `app/(personas)/{persona}/`.

Shared functionality (rule detail, search, settings) is in `app/(shared)/`. A persona switcher in the top nav (`app/layout.tsx`) selects the persona; pages under `(personas)` automatically inherit persona-specific defaults from the layout context.

When adding a new page:
- If it's persona-specific, put it under `(personas)/{persona}/`.
- If it's persona-agnostic, put it under `(shared)/`.
- If you find yourself duplicating a page across personas, extract the shared parts into `components/` and parametrize.

Use Next.js App Router. Server Components by default. The graph view uses `react-flow` (already chosen; do not introduce `cytoscape` as well).

---

## 9. Gemini API Integration (read carefully)

The LLM layer is the heart of this system. Get this right.

### 9.1 SDK
- **Use `google-genai`** (the new unified SDK). Do **not** use the deprecated `google-generativeai`.
- Install via uv: `uv add google-genai httpx`.

### 9.2 Models

Two primary models:

| Use case | Model ID | Why |
|---|---|---|
| High-throughput routine tasks (search ranking, simple extraction, classification, business-event evaluation) | `gemini-3-flash-preview` | fast, cheap |
| High-stakes judgment (rule extraction QC, conflict detection, evaluation of CRITICAL rules, principle-rule evaluation) | `gemini-3.1-pro-preview` | strongest reasoning |

Centralize model selection in `core/llm.py`. Never hardcode model IDs in business logic — always read from config.

### 9.3 Mandatory Rules When Calling Gemini

- **Do NOT change `temperature`** away from the default (1.0). Lower temperatures degrade Gemini 3 reasoning quality and can cause loops.
- Use **`thinking_level`** (not the legacy `thinking_budget`). Valid values: `minimal`, `low`, `medium`, `high`. Default to `low` for high-throughput tasks, `high` for judgment tasks and principle-rule evaluation.
- For function calling, **thought signatures must be cycled through** every turn. The `google-genai` SDK and standard chat history handle this automatically — do not strip signatures from history.
- For PDFs in document processing, set `media_resolution: "media_resolution_medium"` (560 tokens/page). Going higher rarely helps OCR and increases token cost.
- Use **structured output** (`response_mime_type="application/json"` + `response_json_schema`) for any call that must return data the system parses. Do not regex out fields from free-form LLM text.

### 9.4 Document Ingestion (PDF, text, markdown)

- **PDFs**: upload via the **Files API** (`client.files.upload(...)`) for documents > a few pages. Files API is free, files persist 48 hours, max 50 MB / 1000 pages.
- For small / one-shot PDFs, inline `Part.from_bytes(data=..., mime_type='application/pdf')` is fine.
- **Text and markdown**: pass as plain text. Note that Gemini "document understanding" only meaningfully renders PDFs; for `.md`/`.txt`, treat them as text-only inputs.
- Each PDF page is roughly 258 tokens for image content; extracted native text is included free.
- The extraction pipeline (`services/extraction/`) wraps these calls; do not bypass it.

### 9.5 Cost and Latency Discipline

- Cache LLM responses by `hash(inputs + model + prompt_version)` in Postgres. Invalidate on rule revision.
- For `COMPUTATIONAL` rules, the deterministic layer runs first; the LLM call is only for intent confirmation (cheap, low-thinking).
- Default to `gemini-3-flash-preview`. Escalate to `gemini-3.1-pro-preview` only for CRITICAL or principle-rule evaluation.
- Long-context calls (rule corpus + large doc) should use **context caching** for repeated reuse.

### 9.6 Determinism and Audit

- Every LLM call that produces a verdict, a candidate rule, or a relationship suggestion **must** log: model ID, prompt version (content hash), inputs, outputs, latency, timestamp, **subject kind**, **domain**. This goes to the audit log.
- Prompts live in `services/<area>/prompts/` or `services/evaluation/handlers/{kind}/prompts/` or `packages/domain-packs/{domain}/prompts/`. No inline strings scattered across the codebase.

### 9.7 Pluggable Evaluator

The `Evaluator` interface (`services/evaluation/llm_judge.py`) abstracts the LLM provider. Default implementation uses Gemini. Tests use a mock. Adding a new provider (Anthropic, OpenAI, self-hosted) means implementing the interface — no business-logic changes elsewhere.

---

## 10. Data Layer

### 10.1 PostgreSQL (system of record)

- Stores rules, revisions, source documents, evaluations, audit log, proposals, federation hierarchy.
- Migrations: `alembic`. One head per branch; rebase migrations before merging.
- The audit log is **append-only**. Enforce with a Postgres trigger that rejects updates/deletes. Hash chain links each row to the previous.
- Frozen feature tables are in the `frozen` schema (e.g., `frozen.marketplace_packages`). Do not query them in production code paths.

### 10.2 Multi-Axis Scope in PostgreSQL

- `rules.scope_structured` is a JSONB column with the shape `{domain, org_unit, subject_type, attributes}`.
- GIN indexes on `(scope_structured -> 'domain')` and `(scope_structured -> 'subject_type')`.
- The legacy `rules.scope: str` column is retained during the migration period for backward compatibility, populated by the migration script from `scope_structured`.

### 10.3 Elasticsearch (search)

- Index `rules` with: `statement` (analyzed), `tags`, `scope.domain`, `scope.org_unit`, `scope.subject_type`, `scope.attributes` (flattened), `modality`, `kind`, `effective_period`, `embedding` (dense_vector for hybrid search), `language`.
- Use BM25 + kNN hybrid scoring. Rerank top-k with the LLM only when the user requests "smart" search.
- Re-index on rule revision; do not run partial updates that risk drift.

### 10.4 Neo4j (relationship graph)

- One node label: `Rule`. Node `id` matches the Postgres rule ID.
- Relationships: `REFINES`, `OVERRIDES`, `CONFLICTS_WITH`, `DEPENDS_ON`, `DERIVES_FROM`, `SUCCEEDS`. Direction matters and is documented in PROJECT.md §5.4.
- Postgres is the source of truth for rule existence; Neo4j is a derived projection. If they disagree, Postgres wins.
- Provide a reconciler script (`scripts/reconcile_graph.py`) that rebuilds Neo4j from Postgres.

---

## 11. Domain Pack Development

### 11.1 What a Domain Pack Provides

A Domain Pack is a self-contained extension for one functional domain (legal, HR, finance, sales, engineering). It provides:

- **`pack.yaml`** — manifest with display names, metadata extensions, default subject types, default rule kinds, extraction strategy hints.
- **`prompts/`** — domain-specific extraction and evaluation prompt templates.
- **`analyzers/`** — domain-specific structural parsers (e.g., legal article/paragraph hierarchy).
- **`templates/`** — YAML rule templates that can be imported.
- **`samples/`** — sample source documents for testing.
- **`ui_hints.yaml`** — persona-specific labels, glossary, default filters for the frontend.

### 11.2 Pack Manifest Example

```yaml
# packages/domain-packs/legal/pack.yaml
name: legal
display_name:
  en: "Legal"
  ja: "Legal department"
metadata_extensions:
  jurisdiction:
    type: string
    enum: ["jp", "us", "eu", "uk", "global"]
  statute_id:
    type: string
default_subject_types: [contract, clause, regulation]
default_rule_kinds: [normative, definitional, principle]
extraction_strategy:
  hierarchical_structure: ["Article", "Paragraph", "Item"]
  reference_resolution: true
  effective_date_extraction: true
```

### 11.3 Loading Mechanics

`services/domain_packs/loader.py` discovers packs at server startup, validates manifests, registers prompts and analyzers, and exposes the metadata extensions to API schemas. Pack-specific behavior is injected through registered handlers; the core stays domain-agnostic.

### 11.4 Adding a New Pack

1. Create `packages/domain-packs/{name}/`.
2. Author `pack.yaml`.
3. Add extraction and evaluation prompts under `prompts/`.
4. Add structural analyzers if the domain has unique document structure.
5. Author at least one YAML rule template.
6. Add sample documents.
7. Add tests in `tests/domain_packs/{name}/`.
8. Register the pack in the integration test suite.

### 11.5 Engineering Pack

The previous "core" engineering implementation has been repackaged as `packages/domain-packs/engineering/`. It is **one pack among five**, not the system's center.

---

## 12. Testing

### 12.1 Test Layers

- **Unit tests** (`tests/unit/`): pure logic in `domain/`. No external services. Fast.
- **Integration tests** (`tests/integration/`): spin up docker-compose services in CI. Use `testcontainers-python` if running outside compose.
- **Subject handler tests** (`tests/handlers/{kind}/`): mock the LLM and validate prompt construction, rule selection, verdict aggregation, per kind.
- **Domain pack tests** (`tests/domain_packs/{name}/`): pack manifest validation, prompt rendering, template loading.
- **Scenario tests** (`tests/scenarios/`): the five cross-domain validation scenarios from PROJECT.md §8. Mock LLM by default. Enable real Gemini calls with `LIVE_LLM=1` env var.
- **Eval harness** (`tests/eval/`): per-domain extraction quality (Faithfulness, Atomicity, Modality Accuracy). Runs nightly, not on every PR.

### 12.2 Test Markers

```
@pytest.mark.unit            # pure unit
@pytest.mark.integration     # needs docker compose
@pytest.mark.scenario        # cross-domain validation
@pytest.mark.eval            # extraction quality (nightly)
@pytest.mark.frozen          # frozen features (only runs with RUN_FROZEN_TESTS=1)
@pytest.mark.live_llm        # real Gemini calls (only runs with LIVE_LLM=1)
```

### 12.3 Coverage Targets

- Per `services/evaluation/handlers/{kind}/`: minimum 80% line coverage.
- Per `packages/domain-packs/{name}/`: minimum 70% coverage for `analyzers/`, schema validation for `pack.yaml`.
- Per `services/extraction/domain/{name}/`: minimum 70% coverage with at least 5 sample documents.

### 12.4 LLM Mocking

Never call the real Gemini API in unit or integration tests. Use the mock `Evaluator` in `tests/utils/mock_evaluator.py`. The mock returns scripted verdicts based on input patterns. For new prompts, add fixtures.

For nightly eval tests, real Gemini calls are gated by `LIVE_LLM=1` and a Gemini API key in CI secrets.

---

## 13. Environment Variables

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

# Feature Flags (frozen features default off)
FEATURE_MARKETPLACE_ENABLED=false
FEATURE_GATEWAY_WEBHOOKS_EXTERNAL_ENABLED=false
FEATURE_GITHUB_INTEGRATION_ENABLED=false
FEATURE_WEEKLY_DIGEST_DELIVERY_ENABLED=false
FEATURE_AGENT_TRUST_AUTONOMY_ENABLED=false
FEATURE_AGENT_TRACKING_ENABLED=true
FEATURE_PROPOSALS_ENABLED=true

# Domain Packs (all default on; disable to hide a domain)
FEATURE_DOMAIN_LEGAL_ENABLED=true
FEATURE_DOMAIN_HR_ENABLED=true
FEATURE_DOMAIN_FINANCE_ENABLED=true
FEATURE_DOMAIN_SALES_ENABLED=true
FEATURE_DOMAIN_ENGINEERING_ENABLED=true
```

When you add a new env var, update `.env.example` in the same change.

---

## 14. Feature Flags

Feature flags live in `core/feature_flags.py` as a Pydantic `BaseSettings` class with `env_prefix="FEATURE_"`. Each flag gates one or more of:

- A router (in `api/v1/__init__.py`): `if flags.marketplace_enabled: app.include_router(marketplace_router)`.
- MCP tools (in `mcp/tools.py`): conditional registration.
- arq workers (in `workers/settings.py`): conditional cron registration.
- Frontend navigation items (via `NEXT_PUBLIC_FEATURE_*` env passthrough).

**Do not delete code** when freezing a feature. The implementation remains available for future re-activation. Tables for frozen features live in the `frozen` Postgres schema.

---

## 15. Important Rules for Claude Code

These are non-negotiable. Violating them breaks the system or wastes review time.

1. **Read PROJECT.md before designing anything new.** Domain decisions belong there, not here.
2. **The Evaluation Dispatcher is the only entry into evaluation logic.** Do not add code paths that bypass it.
3. **Use the multi-axis `Scope` for any new rule-selection logic.** The legacy `scope: str` is in deprecation; do not extend it.
4. **Do not add engineering bias to cross-domain code.** Code in `services/evaluation/`, `services/search/`, `domain/`, `adapters/` must work for any subject kind. Engineering-specific behavior goes in `services/evaluation/handlers/code_change/` and `packages/domain-packs/engineering/`.
5. **Run linters, formatters, and type checkers before claiming a task is done.** `ruff`, `mypy`, `pnpm lint`, `pnpm typecheck`. CI will reject otherwise.
6. **Never commit secrets.** No API keys, no DB passwords, nothing in code. Use `.env` and `.env.example`.
7. **Never tweak Gemini `temperature`.** Default 1.0 stays.
8. **Never use deprecated Gemini params.** Use `thinking_level`, not `thinking_budget`. Use `google-genai`, not `google-generativeai`.
9. **Never bypass the extraction pipeline** to call Gemini directly from random services. There is one place that talks to Gemini for ingestion.
10. **Never write to the audit log table from application code.** Only the dispatcher and extraction services write, and only through the audit-log adapter that enforces hash chaining.
11. **Never make Postgres and Neo4j disagree silently.** If you write to one, write to the other through the same service. If you can only write to one, queue the other change.
12. **Never delete rules.** Use `effective_period.valid_until` to retire them. Past evaluations must remain re-explainable.
13. **Keep `make up` working.** If your change breaks the local stack, fix it before merging. The local stack is the developer onboarding path.
14. **Update PROJECT.md and CLAUDE.md** when introducing a new dependency, service, subject kind, rule kind, or architectural decision. Code without doc updates does not ship.
15. **Prefer fewer dependencies.** Every added library is a long-term cost. Justify additions in the PR description.
16. **Write structured logs, not `print`.** Logs are operational data.
17. **Tests for LLM-driven features must mock the LLM** unless the test is explicitly an eval test.
18. **Frozen features stay frozen.** Do not unfreeze without an explicit decision recorded in the PR. Code in frozen routers/services must continue to compile but should not be invoked in default deployments.
19. **When unsure, ask.** Open an issue or a draft PR with the question. Do not guess on domain semantics — wrong rules are worse than no rules.

---

## 16. v1 Implementation Guidance

These are the architecture decisions and patterns for ongoing v1 work. Read before implementing any improvement.

### 16.1 Subject Handler Pattern

Every subject kind has a handler at `services/evaluation/handlers/{kind}/handler.py` implementing `SubjectHandler`. Handlers share infrastructure (LLM calls, caching, audit) and own only kind-specific logic.

**Template for a new handler:**

```python
class BusinessEventHandler:
    async def normalize(self, subject: BusinessEventSubject) -> NormalizedBusinessEvent:
        # Hydrate actor, look up org_unit context, resolve attributes
        ...

    async def select_rules(self, normalized) -> list[Rule]:
        # Use multi-axis Scope to filter; query rule_selector with
        # domain=<inferred>, subject_type=<event_type related>, attributes=<actor attrs>
        ...

    def build_prompt(self, normalized, rules) -> str:
        # Load prompt template from handlers/business_event/prompts/evaluate.txt
        # Render with normalized event + rules
        ...

    def aggregate(self, verdicts, rules, normalized) -> EvaluationResult:
        # Combine per-rule verdicts, build reason graph, surface remediations
        ...

    @property
    def verdict_schema(self) -> dict:
        # JSON schema for the LLM's structured output
        ...
```

### 16.2 Scope Migration

The `scope_structured` JSONB column was added in migration 023 (Phase A). To migrate an existing rule:

1. Parse the legacy `scope: str` (e.g., `"engineering/python"`) into `{domain: "engineering", subject_type: "code_file"}`.
2. Run `scripts/reconcile_scope_structured.py` for bulk migration. Output is a YAML preview file; review before commit.
3. New rule creation requires `scope_structured`. The system synthesizes `scope: str` from it for backward compatibility.

### 16.3 Hybrid Evaluation

When implementing a `COMPUTATIONAL` rule's deterministic check:

1. Add the expression to `evaluation_spec.expression` (validated against an allowlist of safe operations).
2. The deterministic layer evaluates the expression in `services/evaluation/deterministic/computational.py` using `asteval`.
3. The LLM is then called with the deterministic verdict and asked: "Does the rule's intent agree with this verdict?"
4. If yes → return the deterministic verdict with the LLM's human-readable reason.
5. If no (disagreement) → return `NEEDS_CONFIRMATION` with both verdicts logged.

### 16.4 ABAC Authorization

Authorization is enforced in API middleware (`core/auth.py`). For each request:

1. Resolve the principal (user, group, role).
2. For each rule or evaluation result being returned, compute the allowed actions.
3. Filter out rules the principal is not authorized to see.
4. For mutations, reject if the action is not in the principal's allowed set for the rule's scope.

### 16.5 Frozen Feature Discipline

If your work touches a frozen feature:

- Confirm it remains gated by its feature flag.
- If you must modify the code, document why in the PR description.
- Do not add new functionality to frozen features.
- If you find a bug that affects core code while looking at frozen code, fix the core code, not the frozen feature.

### 16.6 Persona-Aware Frontend Development

When adding a new frontend page:

1. Identify which personas need it. If multiple, check if the differences are substantial (different data, different UX) or cosmetic (different labels).
2. Substantial differences → separate pages under each persona dir.
3. Cosmetic differences → one shared page, with `usePersona()` hook for labels and defaults.
4. Always populate the engineering persona first (the existing baseline). Other personas can ship as skeletons that grow over sprints.

### 16.7 New Domain Pack Workflow

To add a new domain pack:

1. Create `packages/domain-packs/{name}/` with `pack.yaml`, `prompts/`, `analyzers/` (optional), `templates/`, `samples/`.
2. Add tests in `tests/domain_packs/{name}/`.
3. Add a frontend persona in `apps/frontend/app/(personas)/{name}/` (skeleton is fine initially).
4. Add a `FEATURE_DOMAIN_{NAME}_ENABLED` flag (default true).
5. Update `docs/domains/{name}.md`.
6. Update PROJECT.md §6.8 if the pack introduces new architectural concepts.

### 16.8 Per-Domain Quality Metrics

When working on extraction or evaluation in a domain:

- The Intelligence view reports Faithfulness, Atomicity, Modality Accuracy per domain.
- If your change touches extraction for `domain X`, run the eval harness against at least 20 documents in that domain.
- Quality must not regress. If it does, the change needs a corresponding prompt or analyzer improvement.

### 16.9 v0 Legacy Sections

Earlier phases (Phase 1–5, Phase 6a) have implementation notes in `development/`. These remain accurate for their respective subsystems and should be consulted for areas not affected by v1 generalization. v1-affected areas have their guidance here in §16.

---

## 17. References

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
- asteval: https://newville.github.io/asteval/

---

*This file is a contract. If you (Claude Code) find a conflict between this file and the user's request, surface the conflict and ask. Do not silently override.*

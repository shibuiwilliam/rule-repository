# CLAUDE.md

> Operational guide for Claude Code when working on the **Rule Repository** project.
> For the project vision, domain model, and roadmap, see **`PROJECT.md`**.
> For the gap analysis that motivates Phase 7 (cross-organizational rebrand), see **`IMPROVEMENT.md`**.

This file is the working contract between you (Claude Code) and the project. Read it before making changes. When in doubt, follow the rules in this file over your prior conventions.

---

## 1. Project at a Glance

The Rule Repository is an **organization-wide natural-language rule platform**. It stores rules from many domains (laws, contracts, HR policies, financial controls, marketing standards, engineering guidelines, documentation conventions) and makes them searchable, evaluable, and enforceable through LLM-assisted services and SDKs.

This is **not** a coding-rule manager. Coding governance is one important use case, but HR, legal, finance, sales/marketing, and regulatory compliance are equally first-class. When you write code, examples, docs, or templates, default to language and use cases that are domain-balanced — not engineering-only.

This repository is a monorepo containing the backend server, frontend, Python client SDKs, MCP server, CLI tools, and local dev infrastructure. The first deliverable is a fully working local stack via **Docker Compose** (`make up`).

---

## 2. Tech Stack (authoritative)

| Layer | Technology | Notes |
|---|---|---|
| Backend | **Python 3.13** + FastAPI | Library management with **uv** |
| Frontend | **TypeScript**, **React 19**, **Next.js 15**, **Tailwind CSS** | Library management with **pnpm** |
| Python clients | Python 3.13 (Rule Client, Agentic Rule Client) | uv |
| LLM | **Gemini 3 Flash** (`gemini-3-flash-preview`) and **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`) | via `google-genai` SDK |
| Document parsing / OCR | **Gemini Files API** + document understanding | PDF, text, markdown, DOCX |
| Relational DB | PostgreSQL 17 | rules, revisions, audit log, evaluations |
| Search | Elasticsearch 8.17 | full-text + hybrid search |
| Graph DB | Neo4j 5 | rule relationships |
| Job queue | Redis 7 + arq | 6 cron jobs |
| MCP | FastMCP (mcp ≥ 1.9) | 12 tools |
| Audit | Postgres append-only + hash chain; optional WORM (S3 Object Lock) + TSA | regulated-domain support |
| Local orchestration | Docker Compose | dev + integration tests |

Do not introduce additional frameworks or services without updating this file and `PROJECT.md` first.

---

## 3. Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                    # FastAPI backend (Python 3.13, uv)
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/            # 18 routers
│   │   │   ├── services/          # 13+ service areas
│   │   │   ├── domain/            # pure domain types (Rule, Verdict, Subject, Remediation)
│   │   │   ├── adapters/          # postgres, elasticsearch, neo4j, gemini, files
│   │   │   ├── subjects/          # SubjectAdapter implementations (Phase 7b)
│   │   │   ├── integrations/
│   │   │   │   ├── github/        # PR review, webhooks
│   │   │   │   ├── ci/            # CI formatters
│   │   │   │   └── business_systems/  # SaaS connectors (Phase 7d)
│   │   │   ├── mcp/               # MCP server
│   │   │   ├── gateway/           # webhook normalizers, policy engine
│   │   │   ├── workers/           # arq cron jobs
│   │   │   └── audit/             # hash chain, WORM, TSA
│   │   ├── prompts/               # versioned LLM prompts
│   │   │   └── evaluate/          # per-subject-type prompts
│   │   ├── alembic/               # migrations
│   │   └── tests/
│   └── frontend/                  # Next.js 15 (pnpm)
│       └── app/(dashboard)/       # 23+ pages, persona-aware
├── packages/
│   ├── rule-client/               # Python SDK
│   ├── agentic-client/            # Agentic SDK
│   └── cli/                       # rulerepo-check / -hook / -ingest / -export
├── sample_rules/
│   ├── coding_rules/              # engineering-domain documents
│   ├── company_rules/             # corporate-policy documents
│   ├── sales_team_rules/          # sales-domain documents
│   ├── hr_rules/                  # HR / labor (Phase 7a)
│   ├── contract_rules/            # legal / contracts (Phase 7a)
│   ├── finance_rules/             # finance / expense (Phase 7a)
│   ├── compliance_rules/          # AML / bribery / privacy (Phase 7a)
│   └── templates/                 # YAML rule packs (engineering + business)
├── infra/                         # Dockerfiles, init SQL, ES templates, Neo4j constraints
├── scripts/                       # seed, reconcile, reindex, generate_claude_md
├── development/                   # technical docs
├── docs/                          # mkdocs site
├── docker-compose.yml
├── Makefile                       # 60+ targets
├── PROJECT.md                     # vision, domain model, roadmap
├── IMPROVEMENT.md                 # gap analysis and Phase 7 plan
└── CLAUDE.md                      # this file
```

When adding a new package, place it under `apps/` (deployable apps) or `packages/` (libraries). Update `pyproject.toml` (uv workspace) or `pnpm-workspace.yaml` accordingly.

---

## 4. Quick Start

The whole stack must come up with one command. If your changes break this, fix it before continuing.

```bash
cp .env.example .env            # then fill in GEMINI_API_KEY
make up                         # or: docker compose up --build -d
make seed                       # load sample rules and templates
```

Expected services:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | REST + Intent + Evaluate + Gateway APIs |
| API docs | http://localhost:8000/docs | FastAPI Swagger UI |
| Frontend | http://localhost:3000 | Operator console (persona-aware) |
| MCP Server | localhost:8001 | AI agent tool integration |
| PostgreSQL | localhost:5432 | system of record |
| Elasticsearch | http://localhost:9200 | search index |
| Neo4j Browser | http://localhost:7474 | rule graph |
| Redis | localhost:6379 | background jobs |

---

## 5. Common Commands

```bash
make help                       # show all targets
make up                         # start full stack
make down                       # stop
make reset                      # wipe volumes and rebuild

make dev.server                 # FastAPI with hot reload on :8000
make dev.frontend               # Next.js with hot reload on :3000

make precommit.install          # install git hooks
make test                       # run all tests
make check                      # format + lint + test (run before committing)
```

### Backend (apps/server)
```bash
cd apps/server
uv sync
uv run uvicorn rulerepo_server.main:app --reload
uv run pytest
uv run ruff check . && uv run ruff format .
uv run mypy src
```

### Frontend (apps/frontend)
```bash
cd apps/frontend
pnpm install
pnpm dev
pnpm build && pnpm start
pnpm lint && pnpm typecheck && pnpm test
```

### Python SDKs (packages/...)
```bash
cd packages/rule-client    # or packages/agentic-client
uv sync
uv run pytest
uv build
```

---

## 6. Coding Conventions

### Python (server, clients, CLI)
- **Python 3.13.** Modern syntax: built-in generics (`list[str]`), `match`, structural pattern matching where it improves clarity.
- **Type hints mandatory** on all public functions. mypy must pass on `src/`.
- **Formatter and linter**: `ruff` (linting + formatting). No `black`, no `isort`.
- **Naming**: snake_case for functions/vars, PascalCase for classes, SCREAMING_SNAKE_CASE for constants. Module names lowercase.
- **Docstrings**: Google style, required on public APIs.
- **Errors**: project-specific exception hierarchy. Never raise bare `Exception`.
- **Logging**: `structlog` JSON. Never `print()` outside one-off scripts.
- **Pydantic v2** for all data validation at API boundaries.
- **Tests**: `pytest` + `pytest-asyncio`. Unit tests on pure logic; integration tests against the docker-compose stack.

### TypeScript (frontend)
- **Strict TS**. No `any` without justification.
- **App Router** (Next.js 15). Server Components by default; Client Components only when needed.
- **Tailwind**: prefer utility classes; centralize design tokens in `tailwind.config.ts`.
- **State**: prefer Server Components and URL state. Client state via `zustand`. Server-state caching via `@tanstack/react-query`.
- **Components**: PascalCase files, one component per file unless tightly coupled.
- **API types**: generate TypeScript client from the backend's OpenAPI spec. Do not hand-write types that already exist in the API contract.
- **Lint**: ESLint + Prettier. `pnpm lint` and `pnpm typecheck` must pass.

### Commits / branches
- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- Branch from `main`. Open PRs even for solo work.

---

## 7. Backend Architecture Notes

The server is a single FastAPI application exposing REST, Intent, Evaluate, Gateway, and MCP surfaces.

```
src/rulerepo_server/
├── main.py                 # FastAPI app factory
├── api/v1/                 # 18 routers
├── core/                   # config, logging, errors, deps
├── domain/                 # pure types: Rule, Verdict, Subject, Remediation, ReasonGraph
├── subjects/               # SubjectAdapter implementations (one module per type)
├── services/               # extraction, search, evaluation, governance, etc.
├── adapters/               # postgres, elasticsearch, neo4j, gemini, files
├── integrations/           # github, ci, business_systems
├── mcp/                    # MCP server
├── gateway/                # webhook ingestion, policy engine
├── workers/                # arq cron jobs
├── audit/                  # hash chain, WORM, TSA
└── schemas/                # Pydantic request/response models
```

**Layering rule.** `api` depends on `services`; `services` depends on `domain` and `adapters`; `domain` depends on nothing else in the project. `subjects/` depends on `domain` only. Do not import upward.

**Async.** The API layer is fully async. DB calls use `asyncpg` (or `sqlalchemy[asyncio]`), Elasticsearch via the async client, Neo4j via the official async driver, Gemini via `google-genai`.

---

## 8. The Subject Adapter Pattern (Critical)

This is the architectural cornerstone introduced in Phase 7b. **Read this section before touching the evaluation engine, prompts, or remediation code.**

### 8.1 The principle
The evaluation engine does not assume what is being evaluated. The subject of evaluation is **pluggable**. Today there is `code_change`; tomorrow `hr_event`, `contract_clause`, `expense_claim`, `marketing_copy`, `transaction`, etc.

### 8.2 The interface
Every subject type implements the `SubjectAdapter` interface:

```python
class SubjectAdapter(Protocol):
    subject_type: SubjectType

    async def parse_payload(self, payload: dict) -> ParsedSubject: ...
    async def assemble_context(self, parsed: ParsedSubject) -> SubjectContext: ...
    def format_prompt(self, parsed: ParsedSubject, ctx: SubjectContext, rules: list[Rule]) -> str: ...
    def interpret_remediation(self, raw: dict, parsed: ParsedSubject) -> Remediation: ...
```

### 8.3 What this means in practice
- **Never write subject-specific logic in `evaluation_core.py`.** It belongs in the adapter.
- **Never assume the input is a diff.** Always go through the adapter.
- **Prompt templates are per subject** under `prompts/evaluate/{subject_type}.txt`.
- **Remediations are subject-typed.** A `ContractClauseRemediation` has different fields and `auto_applicable` semantics than a `CodeRemediation`.
- **Adding a new subject** means adding a new adapter, a new prompt template, and (often) a new context-source connector. It does not mean editing the core engine.

### 8.4 Backward compatibility
The existing `code_change` flow remains operational. Callers that send the legacy `diff` field are routed through a compatibility shim that wraps it as `Subject(type='code_change', payload={'diff': ...})`. Do not break this shim.

---

## 9. Frontend Notes

The frontend is the operator console. It supports multiple personas:

- `Compliance Officer`, `Legal Counsel`, `HR Manager`, `Finance Controller`, `Engineering Lead`, `Sales Manager`, `Executive`.

A **persona switcher** in the header changes the dashboard, default scope filters, and surfaced alerts. Adding a new feature page should consider which personas it serves and where it appears in the navigation.

The graph view (Neo4j-backed) renders using `react-flow` (canonical choice for this project).

**i18n.** UI strings are localized via `next-intl` with `en` and `ja` locales. Do not hard-code English strings. Rule statements themselves remain unlocalized — multilingual rules use the `translates` relationship and Polyglot Rule pairs.

---

## 10. Gemini API Integration (read carefully)

The LLM layer is the heart of this system. Get this right.

### 10.1 SDK
- Use `google-genai` (the new unified SDK). Do **not** use the deprecated `google-generativeai`.
- Install via uv: `uv add google-genai httpx`.

### 10.2 Models

| Use case | Model ID | Why |
|---|---|---|
| High-throughput tasks (search ranking, simple extraction, classification) | `gemini-3-flash-preview` | fast, cheap |
| High-stakes judgment (rule extraction QC, conflict detection, CRITICAL evaluation) | `gemini-3.1-pro-preview` | strongest reasoning |

Centralize model selection in one config module (`core/llm.py`). Never hardcode model IDs in business logic.

### 10.3 Mandatory rules when calling Gemini
- **Do not change `temperature`** away from the default (1.0). Lower temperatures degrade Gemini 3 reasoning and can cause loops.
- Use **`thinking_level`** (not `thinking_budget`). Defaults: `low` for high-throughput, `high` for judgment.
- For function calling, **thought signatures must be cycled through**. The SDK and standard chat history handle this automatically — do not strip signatures.
- For PDFs, set `media_resolution: "media_resolution_medium"` (560 tokens/page).
- Use **structured output** (`response_mime_type="application/json"` + `response_json_schema`) for any call the system parses.

### 10.4 Document ingestion
- **PDFs**: upload via the **Files API** for documents > a few pages. Files API is free, files persist 48 hours, max 50 MB / 1000 pages.
- For small / one-shot PDFs, inline `Part.from_bytes(...)` is fine.
- **Text and markdown**: pass as plain text. Note that document understanding only meaningfully renders PDFs; for `.md`/`.txt`, treat as text-only.
- **DOCX**: convert to PDF before passing to Gemini (Gemini does not parse DOCX directly). Use a deterministic LibreOffice-based conversion.

### 10.5 Cost and latency discipline
- Cache LLM responses by `hash(inputs + model + prompt_version)` in Postgres. Invalidate on rule revision.
- Use the **batched evaluator** by default — single Gemini call evaluates all selected rules at once (5–20× fewer API calls).
- Long-context calls should use **context caching** for repeated reuse.

### 10.6 Determinism and audit
Every LLM call that produces a verdict, a candidate rule, or a relationship suggestion **must** log: model ID, prompt version (a content hash), inputs, outputs, latency, timestamp. This goes to the audit log. Prompts live in `prompts/<area>/` as standalone files, versioned in git. No inline strings scattered across the codebase.

---

## 11. Data Layer

### 11.1 PostgreSQL (system of record)
- Stores rules, revisions, source documents, evaluations, audit log.
- Migrations: `alembic`. One head per branch; rebase before merging.
- The audit log table is **append-only**. Enforced with a Postgres trigger that rejects updates and deletes. Hash chain column links each row to the previous.
- `tenant_id` column reserved on all relevant tables (NULLable, default NULL) for future multi-tenancy.

### 11.2 Elasticsearch (search)
- Index `rules` with: `statement` (analyzed), `tags`, `scope`, `applicable_subject_types`, `modality`, `jurisdiction`, `legal_force`, `effective_period`, `embedding` (dense_vector).
- Hybrid scoring: BM25 + kNN. LLM reranking only on user-requested smart search.
- Re-index on rule revision; do not run partial updates that risk drift.

### 11.3 Neo4j (relationship graph)
- One node label: `Rule`. Node `id` matches the Postgres rule ID.
- Relationships: `REFINES`, `OVERRIDES`, `CONFLICTS_WITH`, `DEPENDS_ON`, `DERIVES_FROM`, `SUCCEEDS`, `TRANSLATES`. Direction matters — see `PROJECT.md` §5.2.
- Postgres is the source of truth. Neo4j is a derived projection. Provide a reconciler script (`scripts/reconcile_graph.py`) that rebuilds Neo4j from Postgres.

### 11.4 Audit storage tiers
- Tier 1 (default): Postgres append-only with hash chain.
- Tier 2 (regulated): Tier 1 + S3 Object Lock dual-write (WORM).
- Tier 3 (legal-grade): Tier 2 + TSA time-stamping per row.
- Tier is selected per rule category via configuration. Adding a new tier is a contained extension to `audit/`.

---

## 12. Business-System Integration

The system is not just for AI agents. Connectors live under `integrations/business_systems/`.

A connector is a pair of:
- **Inbound** — a webhook receiver that normalizes the SaaS payload into a `BusinessEvent`.
- **Outbound** — an action dispatcher that issues SaaS-native actions (return-for-revision, comment, notification).

Common contract: every connector emits and consumes the same `BusinessEvent` schema. Do not let SaaS-specific shapes leak past the connector boundary. The evaluation engine, audit log, and intelligence layer never see SaaS-specific data — they see `BusinessEvent`s.

When adding a connector:
1. Implement inbound and outbound under `integrations/business_systems/<vendor>/`.
2. Add policy mappings under `gateway/policies/`.
3. Register the SubjectAdapter you depend on (e.g., `expense_claim` for Concur, `hr_event` for SmartHR).
4. Add a sample policy in `infra/sample_policies/`.
5. Document in `docs/integrations/<vendor>.md`.

---

## 13. Testing

- **Unit tests**: pure logic in `domain/` and `subjects/`. No external services. Fast.
- **Integration tests**: spin up docker-compose services. Use `testcontainers-python` if running in CI without compose.
- **LLM tests**: never call the real Gemini API in unit tests. Use the mock client in `tests/mocks/gemini.py`. For integration, gate behind `RULEREPO_LIVE_LLM=1`.
- **Subject-adapter tests**: each adapter must have round-trip tests for parse → assemble → format → interpret.
- **Frontend tests**: Vitest + React Testing Library. Playwright for end-to-end.
- **Eval harness**: separate test suite validating LLM-driven features (rule extraction quality, conflict detection precision/recall, per-subject-type evaluation accuracy) against curated fixtures. Runs nightly, not on every PR.

---

## 14. Environment Variables

All env vars live in `.env.example`. Never commit `.env`. Required for local dev:

```
GEMINI_API_KEY=...
DATABASE_URL=postgresql+asyncpg://rule:rule@postgres:5432/ruledb
ELASTICSEARCH_URL=http://elasticsearch:9200
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=ruledev
REDIS_URL=redis://redis:6379/0
RULEREPO_SERVER_URL=http://server:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO
LLM_DEFAULT_MODEL=gemini-3-flash-preview
LLM_JUDGE_MODEL=gemini-3.1-pro-preview
DIGEST_WEBHOOK_URL=
ALERT_WEBHOOK_URL=
AUDIT_WORM_BUCKET=                 # optional, regulated-domain
AUDIT_TSA_URL=                     # optional, regulated-domain
```

When you add a new env var, update `.env.example` in the same change.

---

## 15. Important Rules for Claude Code

These are non-negotiable. Violating them breaks the system or wastes review time.

1. **Read PROJECT.md before designing anything new.** Domain decisions belong there, not here. Read IMPROVEMENT.md for the rationale behind Phase 7.
2. **The system is organization-wide, not coding-only.** When you write features, examples, docs, or templates, do not default to engineering use cases. If a new feature would only serve coding teams, ask whether it generalizes — and if not, justify why.
3. **Never assume the subject of evaluation is a code change.** Use the SubjectAdapter pattern. New domains plug in as new adapters; they do not modify the core engine.
4. **Run linters, formatters, and type checkers before claiming a task is done.** `make check` must pass.
5. **Never commit secrets.** No API keys, no DB passwords. Use `.env` and `.env.example`.
6. **Never tweak Gemini `temperature`.** Default 1.0 stays.
7. **Never use deprecated Gemini params.** Use `thinking_level`, not `thinking_budget`. Use `google-genai`, not `google-generativeai`.
8. **Never bypass the extraction pipeline** to call Gemini directly from random services. There is one place that talks to Gemini for ingestion.
9. **Never write to the audit log table from application code.** Only the audit-log adapter writes, and only with hash-chain enforcement (and WORM/TSA dispatch when configured).
10. **Never let Postgres and Neo4j (or Elasticsearch) disagree silently.** Writes go through the same service. If a downstream write fails, queue and retry.
11. **Never delete rules.** Use `effective_period.valid_until` to retire them. Past evaluations must remain re-explainable.
12. **Never let business-system payloads leak past connector boundaries.** Inside the engine, only `BusinessEvent`s exist.
13. **Keep `make up` working.** If your change breaks the local stack, fix it before merging.
14. **Update PROJECT.md, CLAUDE.md, and (when applicable) IMPROVEMENT.md** when introducing new dependencies, services, subject types, or architectural decisions. Code without doc updates does not ship.
15. **Prefer fewer dependencies.** Every added library is long-term cost. Justify additions in the PR description.
16. **Write structured logs, not `print`.** Logs are operational data and may end up in the audit trail.
17. **Tests for LLM-driven features must mock the LLM** unless explicitly an eval test.
18. **Templates that require legal expertise must be flagged.** `expert_reviewed: true | false (reference only)`. Shipping legal templates as `expert_reviewed: true` without actual expert review is a firing offense.
19. **i18n: never hard-code user-facing English in the frontend.** Use `next-intl` keys.
20. **When unsure, ask.** Open an issue or a draft PR with the question. Wrong rules are worse than no rules — and wrong business rules can be worse than wrong code rules.

---

## 16. References

- `PROJECT.md` — vision, domain model, roadmap.
- `IMPROVEMENT.md` — gap analysis and Phase 7 plan.
- `development/` — technical deep dives.
- `docs/` — mkdocs site.
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
- arq (job queue): https://arq-docs.helpmanual.io/

---

*This file is a contract. If you (Claude Code) find a conflict between this file and the user's request, surface the conflict and ask. Do not silently override.*

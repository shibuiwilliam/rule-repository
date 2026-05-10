# CLAUDE.md

> Operational guide for Claude Code when working on the **Rule Repository** project.
> For the project vision, domain model, and roadmap, see **PROJECT.md**.
> For the analysis and rationale of Phase 7, see **IMPROVEMENT.md**.

This file is the working contract between you (Claude Code) and the project. Read it before making changes. When in doubt, follow the rules in this file over your prior conventions.

---

## 1. Project at a Glance

The Rule Repository is a **Cross-Organizational Rule Platform**. It stores natural-language rules (laws, contracts, internal policies, financial rules, sales communication standards, engineering rules, documentation conventions) and makes them searchable, evaluable, and enforceable through LLM-assisted services and SDKs across departments (Legal, HR, Finance, Sales, Engineering, IT, General Affairs, Compliance, Executive). See `PROJECT.md` for the full design.

**This repository is a monorepo** containing the backend server, frontend, Python client SDKs, and local dev infrastructure. The deliverable is a fully working local stack via **Docker Compose**.

**Current state**: Phase 8 (Cross-Organizational Parity) is **complete**. Phase 7 established the multi-domain architecture; Phase 8 eliminated code-centric bias and achieved full domain parity across all surfaces, plugins, SDKs, and frontend dashboards. Phases 1–7 are in maintenance.

**Out of scope under the current direction**: multi-agent governance sessions. This feature exists in code but is disabled by default.

---

## 2. Tech Stack (authoritative)

| Layer | Technology | Notes |
| --- | --- | --- |
| Backend | **Python 3.13** + FastAPI | Library management with **uv** |
| Frontend | **TypeScript**, **React**, **Next.js**, **Tailwind CSS** | Library management with **pnpm** |
| Python clients | **Python 3.13** (Rule Client, Agentic Rule Client) | Library management with **uv** |
| LLM | **Gemini 3 Flash** (`gemini-3-flash-preview`) and **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`) | via `google-genai` SDK |
| Document parsing / OCR | **Gemini Files API** + document understanding | PDF, text, markdown |
| Spreadsheet parsing | **openpyxl** | for the new tabular extractor |
| Email parsing | **email** stdlib + **mail-parser** | for the new email_archive extractor |
| Relational DB | **PostgreSQL** | rules, revisions, audit log, memberships |
| Search | **Elasticsearch** | full-text + hybrid search |
| Graph DB | **Neo4j** | rule relationships |
| Job Queue | **arq** + **Redis** | background tasks (health scoring, recommendations, correction analysis, polyglot verification) |
| Local orchestration | **Docker Compose** | dev + integration tests |

Do **not** introduce additional frameworks or services without updating this file and PROJECT.md first.

---

## 3. Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                     # FastAPI backend (Python 3.13, uv)
│   │   ├── pyproject.toml
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/             # REST API routers
│   │   │   ├── core/               # config, logging, errors, auth, middleware, PII, deps
│   │   │   ├── domain/             # Rule, Evaluation, Verdict, Subject, BusinessEvent, Department (pure)
│   │   │   ├── services/
│   │   │   │   ├── evaluation/     # Subject Evaluation Engine
│   │   │   │   │   ├── service.py          # orchestrator (subject dispatch)
│   │   │   │   │   ├── rule_selector.py    # subject-agnostic rule selection
│   │   │   │   │   ├── batch_evaluator.py  # subject-agnostic batched LLM call
│   │   │   │   │   ├── verdict_aggregator.py # subject-agnostic
│   │   │   │   │   ├── conflict_aggregator.py
│   │   │   │   │   ├── graph_resolver.py
│   │   │   │   │   ├── impact_preview.py
│   │   │   │   │   ├── code/               # Code evaluation path
│   │   │   │   │   │   ├── evaluator.py
│   │   │   │   │   │   ├── diff_parser.py
│   │   │   │   │   │   ├── context_assembler.py
│   │   │   │   │   │   └── prompts/
│   │   │   │   │   ├── document/           # NEW: Document evaluation path (Phase 7b)
│   │   │   │   │   │   ├── evaluator.py
│   │   │   │   │   │   ├── span_finder.py
│   │   │   │   │   │   ├── context_assembler.py
│   │   │   │   │   │   └── prompts/        # contract_clause.txt, email.txt, minutes.txt, ...
│   │   │   │   │   ├── transaction/        # NEW: Transaction evaluation path (Phase 7c)
│   │   │   │   │   │   ├── evaluator.py
│   │   │   │   │   │   ├── field_locator.py
│   │   │   │   │   │   └── prompts/
│   │   │   │   │   ├── text/               # NEW: Communication evaluation
│   │   │   │   │   ├── workflow/           # NEW: Workflow step evaluation
│   │   │   │   │   └── agent/              # Agent-action evaluation (existing, kept)
│   │   │   │   ├── extraction/             # Document ingestion pipeline
│   │   │   │   │   ├── pipeline.py
│   │   │   │   │   └── extractors/
│   │   │   │   │       ├── generic.py      # existing
│   │   │   │   │       ├── claude_md.py    # existing (moved)
│   │   │   │   │       ├── linter_config.py
│   │   │   │   │       ├── code_patterns.py
│   │   │   │   │       ├── contract.py     # NEW
│   │   │   │   │       ├── regulation.py   # NEW
│   │   │   │   │       ├── handbook.py     # NEW
│   │   │   │   │       ├── minutes.py      # NEW
│   │   │   │   │       ├── tabular.py      # NEW
│   │   │   │   │       └── email_archive.py # NEW
│   │   │   │   ├── intelligence/           # health, analytics, recommendations
│   │   │   │   ├── compliance/             # NEW: Compliance Cockpit (Phase 7h)
│   │   │   │   │   └── cockpit.py
│   │   │   │   ├── context_delivery/       # smart rule selection + formatting for agents
│   │   │   │   ├── context/                # NEW: Context Provider abstraction (Phase 7k)
│   │   │   │   │   └── providers.py
│   │   │   │   ├── discovery/              # automatic rule discovery
│   │   │   │   ├── feedback/               # correction feedback loop
│   │   │   │   ├── federation/             # cross-project rule federation
│   │   │   │   ├── department/             # NEW: Department RBAC (Phase 7d)
│   │   │   │   │   ├── authz.py
│   │   │   │   │   └── membership.py
│   │   │   │   ├── events/                 # NEW: Business Event ingestion (Phase 7e)
│   │   │   │   │   ├── ingest.py
│   │   │   │   │   └── scope_resolver.py
│   │   │   │   ├── assistant/              # NEW: Conversational Assistant (Phase 7g)
│   │   │   │   │   └── orchestrator.py
│   │   │   │   ├── playground/             # rule sandbox + test cases
│   │   │   │   ├── snapshots/              # rule set versioning
│   │   │   │   ├── polyglot/               # NEW: Polyglot rule verification (Phase 7i)
│   │   │   │   │   └── verifier.py
│   │   │   │   ├── search.py
│   │   │   │   ├── rule_service.py
│   │   │   │   └── intent.py
│   │   │   ├── adapters/                   # postgres, elasticsearch, neo4j, gemini, files
│   │   │   ├── mcp/                        # MCP server (tools, resources, prompts)
│   │   │   ├── gateway/                    # generic webhook gateway (engineering opt-in)
│   │   │   ├── integrations/               # GitHub App (opt-in), CI formatters
│   │   │   ├── schemas/                    # Pydantic request/response models
│   │   │   └── workers/                    # background jobs (arq)
│   │   ├── alembic/                        # database migrations
│   │   └── tests/
│   └── frontend/                           # Next.js + TS + Tailwind (pnpm)
│       ├── package.json
│       └── app/(dashboard)/
│           ├── (existing pages)
│           ├── assistant/                  # NEW: Conversational Assistant (Phase 7g)
│           ├── compliance/                 # NEW: Compliance Cockpit (Phase 7h)
│           └── departments/                # NEW: Department admin (Phase 7d)
├── packages/
│   ├── rule-client/                        # Python SDK
│   ├── agentic-client/                     # Python SDK
│   └── cli/                                # rulerepo-check, rulerepo-hook, rulerepo-ingest, rulerepo-context
├── infra/
│   ├── docker/
│   ├── postgres/
│   ├── elasticsearch/
│   └── neo4j/
├── scripts/
│   └── seed_data.py                        # extended with department & business-domain templates
├── sample_rules/
│   ├── coding_rules/                       # existing engineering samples
│   ├── company_rules/                      # existing
│   ├── sales_team_rules/                   # existing
│   └── templates/
│       ├── python-fastapi.yaml             # existing
│       ├── typescript-react.yaml           # existing
│       ├── security-owasp.yaml             # existing
│       ├── api-design.yaml                 # existing
│       ├── testing-standards.yaml          # existing
│       ├── hr-attendance-jp.yaml           # NEW (Phase 7l)
│       ├── expense-policy-jp.yaml          # NEW (Phase 7l)
│       ├── contract-clause-standard.yaml   # NEW (Phase 7l)
│       ├── bribery-prevention.yaml         # NEW (Phase 7l)
│       ├── privacy-protection-jp.yaml      # NEW (Phase 7l)
│       ├── internal-communication.yaml     # NEW (Phase 7l)
│       ├── documentation-standard.yaml     # NEW (Phase 7l)
│       └── procurement-rules.yaml          # NEW (Phase 7l)
├── docker-compose.yml
├── pyproject.toml
├── pnpm-workspace.yaml
├── .env.example
├── PROJECT.md                              # vision and specification
├── CLAUDE.md                               # this file
└── IMPROVEMENT.md                          # Phase 7 rationale
```

When adding a new package, place it under `apps/` or `packages/`. Update `pyproject.toml` (uv workspace) or `pnpm-workspace.yaml` accordingly.

---

## 4. Quick Start (local dev)

The whole stack must come up with one command. If your changes break this, fix it before continuing.

```bash
cp .env.example .env            # then fill in GEMINI_API_KEY
docker compose up --build       # brings up: server, frontend, postgres, elasticsearch, neo4j, redis, mcp, arq-worker
```

Expected services after `up`:

| Service | URL | Purpose |
| --- | --- | --- |
| Backend API | http://localhost:8000 | REST + Intent + Evaluate (code/document/transaction) + Events + Assistant |
| API docs (OpenAPI) | http://localhost:8000/docs | FastAPI Swagger UI |
| Frontend | http://localhost:3000 | Operator console + Assistant + Compliance Cockpit |
| PostgreSQL | localhost:5432 | `ruledb` |
| Elasticsearch | http://localhost:9200 | search index |
| Neo4j Browser | http://localhost:7474 | rule graph |
| MCP Server | http://localhost:8001 | Streamable-HTTP MCP for agents |
| Redis | localhost:6379 | Job queue (arq) |
| arq-worker | — | Background task processor |

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

### Python SDKs

```bash
cd packages/rule-client
uv sync
uv run pytest
uv build
```

### CLI Tools

```bash
rulerepo-check --diff "$(git diff origin/main...HEAD)" --format github-actions   # CI (engineering)
rulerepo-hook preflight --file src/api/handler.py     # agent hook: before edit
rulerepo-hook posthoc --file src/api/handler.py       # agent hook: after edit
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python
rulerepo-context update --file CLAUDE.md
```

### MCP Server

```bash
uv run rulerepo-mcp                                   # stdio (local)
MCP_TRANSPORT=streamable-http uv run rulerepo-mcp     # HTTP (remote agents)
```

### Whole repo

```bash
docker compose up --build
docker compose down -v
docker compose logs -f server
uv run python -m pytest
make seed                       # seed sample rules including new business-domain templates
make crossorg.acceptance        # NEW: run the four cross-organizational acceptance tests
```

---

## 6. Coding Conventions

### Python (server + clients)
- **Python 3.13**. Modern syntax: built-in generics, `match` where clarity helps.
- **Type hints mandatory** on all public functions. mypy must pass on `src/`.
- **Formatter and linter**: `ruff` (both linting and formatting). No `black`, no `isort`.
- **Naming**: snake_case for functions/vars, PascalCase for classes, SCREAMING_SNAKE_CASE for constants.
- **Docstrings**: Google style. Required on all public APIs.
- **Errors**: project-specific exception hierarchy under `rulerepo_server.errors` / `rulerepo.errors`. Never raise bare `Exception`.
- **Logging**: `structlog` with JSON output. Never `print()` outside one-off scripts.
- **Pydantic** for all data validation at API boundaries. Pydantic v2 idioms.
- **Tests**: `pytest` + `pytest-asyncio`. Unit tests on pure logic, integration tests against the docker-compose stack.

### TypeScript (frontend)
- **Strict TS**: `"strict": true`. No `any` without justification.
- **App Router** (Next.js 14+ idioms). Server Components by default, Client Components only when needed.
- **Tailwind**: prefer utility classes. Centralize design tokens in `tailwind.config.ts`.
- **State**: Server Components and URL state preferred. `zustand` for client state, `@tanstack/react-query` for server-state caching.
- **Components**: PascalCase files. One component per file unless tightly coupled.
- **API calls**: generated TypeScript client from OpenAPI spec.
- **Linting**: ESLint + Prettier. `pnpm lint` must pass.

### Commits / branches
- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- For Phase 7 work, prefix the body with `[phase-7x]` referencing the sub-phase (e.g., `[phase-7b]` for document evaluation).
- Branch from `main`. Open PRs even for solo work.

---

## 7. Backend Architecture Notes

The server is a single FastAPI application that exposes:

- **REST API** at `/api/v1/...` for CRUD on rules, documents, evaluations.
- **Evaluate APIs**:
  - `/api/v1/evaluate` — polymorphic, accepts a Subject (or legacy diff/files for backward compatibility).
  - `/api/v1/evaluate/document` — convenience endpoint for `DOCUMENT_DRAFT` subjects.
  - `/api/v1/evaluate/transaction` — convenience endpoint for `TRANSACTION` subjects.
- **Events API** at `/api/v1/events/ingest` — universal business event ingestion.
- **Intent API** at `/api/v1/intent` — natural language query routing.
- **Assistant API** at `/api/v1/assistant/...` — conversational assistant orchestrator.
- **Compliance API** at `/api/v1/compliance/...` — Cockpit data.
- **Department API** at `/api/v1/departments/...` — membership management.
- **Existing routers** (rules, search, intelligence, discovery, feedback, federation, integrations, playground, alerts, snapshots, proposals, agent-governance) preserved.
- **Frozen routers** (multi-agent sessions) return 404 unless feature flag enabled.
- **MCP Server** on a separate port (8001).

**Layering rule**: `api → services → domain/adapters`. `domain` depends on nothing else in the project.

**Subject dispatch pattern**: `services/evaluation/service.py` is the orchestrator. It receives an `EvaluationSubject`, runs subject-agnostic Rule Selection, then dispatches to the matching subject path under `services/evaluation/{code,document,transaction,text,workflow,agent}/`. Each path has its own evaluator and prompt templates but shares the rule selector, batch evaluator, and verdict aggregator.

**Async**: API layer is fully async. DB via `asyncpg` / `sqlalchemy[asyncio]`, Elasticsearch via async client, Neo4j via official async driver, Gemini via `google-genai`.

---

## 8. Frontend Notes

The frontend serves two audiences:

- **Operators** (existing): browse and search rules, upload documents, run extraction, review candidates, view the relationship graph, inspect evaluations and audit logs, manage governance.
- **End users (new)**: the `/assistant` route is an end-user chat surface; the `/compliance` route is the Compliance Cockpit for Compliance/Legal/Exec.

Use the Next.js App Router. Co-locate route segments under `app/(dashboard)/...`. Server Components for data fetching, Client Components for interactivity.

The graph view (Neo4j-backed) renders using `react-flow` or `cytoscape` — pick one early and stick with it.

The sidebar is reorganized for Cross-Organizational use:

- **Manage**: Rules, Discover, Documents, Proposals, Snapshots, Departments
- **Observe**: Compliance Cockpit, Intelligence, Agents (single-agent view), Notifications, Alerts
- **Use**: Assistant, Search, Playground
- **Hidden by default** (feature-flagged): multi-agent Sessions, GitHub App settings

---

## 9. Gemini API Integration (read carefully)

The LLM layer is the heart of this system. Get this right.

### 9.1 SDK
- **Use `google-genai`** (the unified SDK). Do **not** use the deprecated `google-generativeai`.
- Install via uv: `uv add google-genai httpx`.

### 9.2 Models

| Use case | Model ID | Why |
| --- | --- | --- |
| High-throughput, routine tasks (search ranking, simple extraction, classification, document spans) | `gemini-3-flash-preview` | fast, cheap |
| High-stakes judgment (rule extraction QC, conflict detection, evaluation of CRITICAL rules, contract risk analysis) | `gemini-3.1-pro-preview` | strongest reasoning |

Centralize model selection in `core/llm.py`. Never hardcode model IDs in business logic.

### 9.3 Mandatory rules when calling Gemini
- **Do NOT change `temperature`** away from the default (1.0). Lower temperatures degrade Gemini 3 reasoning quality and can cause loops.
- Use **`thinking_level`** (not the legacy `thinking_budget`). Default: `low` for high-throughput, `high` for judgment.
- For function calling, **thought signatures must be cycled through** every turn. The `google-genai` SDK and standard chat history handle this automatically — do not strip signatures from history.
- For PDFs in document processing, set `media_resolution: "media_resolution_medium"` (560 tokens/page).
- Use **structured output** (`response_mime_type="application/json"` + `response_json_schema`) for any call that must return data the system parses. Do not regex out fields from free-form LLM text.

### 9.4 Document ingestion (PDF, text, markdown, DOCX, XLSX, EML)
- **PDFs**: upload via the **Files API** for documents > a few pages. Files API is free, files persist 48 hours, max 50 MB / 1000 pages.
- **DOCX**: convert to PDF or extract text with `python-docx` then send as text. Prefer PDF if visual structure matters.
- **XLSX**: never sent to Gemini directly. The `tabular` extractor uses `openpyxl` to materialize each row, then passes structured rows to Gemini.
- **EML**: extract headers + body with stdlib `email`, then process the body as text.
- Each PDF page is roughly 258 tokens for image content; extracted native text is included free.
- The extraction pipeline wraps these calls; do not bypass it.

### 9.5 Cost and latency discipline
- Cache LLM responses by `hash(inputs + model + prompt_version)` in Postgres. Invalidate on rule revision.
- Use `gemini-3.1-flash-lite-preview` only if explicitly approved.
- Long-context calls (rule corpus + large doc) use **context caching**.
- Document evaluation prompts are typically larger than code prompts. Keep document evaluation prompts under 30 K characters; if exceeded, split into multiple calls.

### 9.6 Determinism and audit
- Every LLM call that produces a verdict, a candidate rule, or a relationship suggestion **must** log: model ID, prompt version (a content hash), inputs, outputs, latency, timestamp, **subject type**.
- Prompts live in `services/<area>/prompts/` as standalone files, versioned in git. No inline strings.

### 9.7 Subject-specific prompt patterns
- Code path: present diff + applicable rules; ask for line-level Remediations.
- Document path: present full document text + applicable rules; ask for span-level Remediations with `offset_start`/`offset_end` byte offsets into the original text. Verify offsets server-side; reject if they don't align.
- Transaction path: present transaction as JSON + applicable rules; ask for `field_change`/`approval_add`/`process_reroute` Remediations referring to specific JSON paths.
- Communication path: similar to document path but with shorter context windows and tighter latency budget.
- Always include the rule's `context`, `rationale`, `preconditions`, `following_examples`, `violation_examples` in the prompt when available.

---

## 10. Data Layer

### 10.1 PostgreSQL (system of record)
- Stores rules, revisions, source documents, evaluations, audit log, departments, memberships.
- Migrations: `alembic`. One head per branch; rebase migrations before merging.
- Phase 7 migrations (proposed numbering, append after the existing latest):
  - `add_subject_type_columns.sql`: add `applicable_subject_types` to `rules`.
  - `add_department_to_rules.sql`: add `department` column with default `'public'`.
  - `add_polyglot_columns.sql`: add `primary_language`, `translations`, `equivalence_verified_at`.
  - `add_kind_and_confidence_required.sql`: add `kind` and `confidence_required`.
  - `create_memberships_table.sql`: `(user_id, department, role)`.
  - `create_business_events_table.sql`: stores accepted business events for replay/audit.
  - `add_subject_type_to_evaluations.sql`: track which subject type each evaluation was run against.
  - `create_polyglot_drift_alerts.sql`: per-translation drift records.
- The audit log table is **append-only**. Postgres trigger rejects updates/deletes. Hash chain column.

### 10.2 Elasticsearch (search)
- Index `rules` with: `statement` (analyzed), `tags`, `scope`, `modality`, `effective_period`, `embedding`, **`department`**, **`kind`**, **`primary_language`**, **`applicable_subject_types`**.
- BM25 + kNN hybrid scoring. Rerank top-k with the LLM only when "smart" search is requested.
- Re-index on rule revision; no partial updates that risk drift.

### 10.3 Neo4j (relationship graph)
- One node label: `Rule`. Node `id` matches the Postgres rule ID.
- Relationships: `REFINES`, `OVERRIDES`, `CONFLICTS_WITH`, `DEPENDS_ON`, `DERIVES_FROM`, `SUCCEEDS`, **`CROSS_REFERENCES`** (new in Phase 7 — for cross-departmental rule references).
- Postgres is the source of truth; Neo4j is a derived projection. If they disagree, Postgres wins and Neo4j is rebuilt via `scripts/reconcile_graph.py`.

---

## 11. Testing

- **Unit tests**: pure logic in `domain/`. No external services. Fast.
- **Integration tests**: spin up docker-compose services in CI. `testcontainers-python` if running in CI without compose.
- **LLM tests**: never call the real Gemini API in unit tests. Mock client. For integration, gate behind env flag (`RULEREPO_LIVE_LLM=1`).
- **Frontend tests**: Vitest + React Testing Library; Playwright for end-to-end if added.
- **Eval harness**: validates LLM-driven features against curated fixtures. Runs nightly.
- **Cross-Organizational acceptance suite** (NEW): four scenarios in `tests/acceptance/cross_org/`:
  1. `test_expense_roundtrip.py` — extract → approve → evaluate transaction → expect DENY + `field_change`
  2. `test_contract_review.py` — evaluate document → expect dangerous-clause detection + `text_rewrite` Remediations
  3. `test_hr_attendance.py` — evaluate transaction → expect overtime DENY + repair suggestion
  4. `test_sales_email.py` — evaluate document → expect privacy/pharmaceutical/consumer-protection flags

  These run on every PR. Failure blocks merge.
- **Subject-type test coverage**: each subject path under `services/evaluation/<path>/` has its own tests directory. Document/transaction tests use canned text/JSON fixtures, not live API calls.

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

# Cross-Organizational direction (Phase 7)
CROSS_ORG_FEATURES_ENABLED=true
DEPARTMENT_RBAC_ENABLED=true
ASSISTANT_ENABLED=true
COMPLIANCE_COCKPIT_ENABLED=true
POLYGLOT_VERIFICATION_ENABLED=true

# Opt-in features (default OFF)
MULTI_AGENT_SESSIONS_ENABLED=false
GITHUB_APP_ENABLED=false

# GitHub Integration (only used when GITHUB_APP_ENABLED=true)
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=
GITHUB_TOKEN=

# Alerts (local file output by default; webhook delivery is opt-in)
ALERT_OUTPUT_MODE=local            # "local" | "webhook" | "both"
ALERT_WEBHOOK_URL=
DIGEST_OUTPUT_MODE=local
DIGEST_WEBHOOK_URL=
```

When you add a new env var, update `.env.example` in the same change.

---

## 13. Important Rules for Claude Code

These are non-negotiable. Violating them breaks the system or wastes review time.

1. **Read PROJECT.md before designing anything new.** Domain decisions belong there, not here.
2. **Read IMPROVEMENT.md before working on Phase 7.** It contains the rationale and acceptance criteria.
3. **Run linters, formatters, and type checkers before claiming a task is done.** `ruff`, `mypy`, `pnpm lint`, `pnpm typecheck`. CI will reject otherwise.
4. **Never commit secrets.** No API keys, no DB passwords, nothing in code. Use `.env` and `.env.example`.
5. **Never tweak Gemini `temperature`.** Default 1.0 stays.
6. **Never use deprecated Gemini params.** Use `thinking_level`, not `thinking_budget`. Use `google-genai`, not `google-generativeai`.
7. **Never bypass the extraction pipeline** to call Gemini directly from random services. There is one place that talks to Gemini for ingestion.
8. **Never write to the audit log table from application code.** Only the evaluation/extraction services write, and only through the audit-log adapter that enforces hash chaining.
9. **Never make Postgres and Neo4j disagree silently.** If you write to one, write to the other through the same service. If you can only write to one, queue the other change.
10. **Never delete rules.** Use `effective_period.valid_until` to retire them. Past evaluations must remain re-explainable.
11. **Keep `docker compose up --build` working.** If your change breaks the local stack, fix it before merging.
12. **Update PROJECT.md, CLAUDE.md, and IMPROVEMENT.md** when introducing a new dependency, service, or architectural decision.
13. **Prefer fewer dependencies.** Every added library is a long-term cost. Justify additions in the PR description.
14. **Write structured logs, not `print`.** Logs are operational data.
15. **Tests for LLM-driven features must mock the LLM** unless the test is explicitly an eval test.
16. **Cross-Organizational acceptance tests must pass on every PR.** Do not merge with red.
17. **Do not extend frozen components.** Multi-agent sessions — leave at current state. If a need arises, raise it in PROJECT.md first.
18. **Subject Type abstraction is load-bearing.** Do not add subject-type-specific logic to subject-agnostic modules (`rule_selector.py`, `batch_evaluator.py`, `verdict_aggregator.py`). If you find yourself wanting to, refactor into the appropriate subject path.
19. **Department RBAC is non-bypassable.** Every API endpoint that returns or mutates rules must apply department visibility. Do not add a new endpoint without an authorization check.
20. **Polymorphic Remediation kinds must be exhaustively handled.** When new code consumes Remediations, use exhaustive `match` on `RemediationKind`. Adding a new kind requires updating all consumers.
21. **When unsure, ask.** Open an issue or a draft PR with the question. Do not guess on domain semantics — wrong rules are worse than no rules.

---

## 14. References

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
- openpyxl: https://openpyxl.readthedocs.io/

---

*This file is a contract. If you (Claude Code) find a conflict between this file and the user's request, surface the conflict and ask. Do not silently override. The Cross-Organizational direction is the canonical project direction; features outside it are frozen by design.*

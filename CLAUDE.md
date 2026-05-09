# CLAUDE.md

> Operational guide for Claude Code when working on the **Rule Repository** project.
> For the project vision, domain model, and roadmap, see **PROJECT.md**.
> For the diagnosis of the historical drift and the rationale for Phase 7+, see **IMPROVEMENT.md**.

This file is the working contract between you (Claude Code) and the project. Read it before making changes. When in doubt, follow the rules in this file over your prior conventions.

---

## 1. Project at a Glance

The Rule Repository is an **organization-wide normative management platform**. It manages laws, contracts, internal policies, HR regulations, financial procedures, sales playbooks, communication standards, documentation conventions, and engineering rules in their original natural language. Every team — Legal, HR, Finance, Sales, Compliance, IT, executive, and engineering — uses it through APIs, AI agents, and persona-specific consoles.

**Code is one Surface among many.** The project's current implementation is the most mature on the Code Surface, but the architecture treats Contract, Human Action, Transaction, Document, and Message Surfaces as equal first-class citizens. Phase 7–9 work is restoring this balance. Read PROJECT.md §4 and IMPROVEMENT.md §4 before designing anything that touches the evaluation core, the discovery pipeline, the MCP tools, or the frontend dashboard structure.

**This repository is a monorepo** containing the backend server, frontend, Python client SDKs, CLI tools, MCP server, infrastructure, and Domain Packs. The full local stack comes up via **Docker Compose**.

---

## 2. Tech Stack (authoritative)

| Layer | Technology | Notes |
|---|---|---|
| Backend | **Python 3.13** + FastAPI | Library management with **uv** |
| Frontend | **TypeScript**, **React 19**, **Next.js 15**, **Tailwind CSS** | Library management with **pnpm** |
| Python clients | **Python 3.13** (Rule Client, Agentic Rule Client) | Library management with **uv** |
| LLM | **Gemini 3 Flash** (`gemini-3-flash-preview`) and **Gemini 3.1 Pro** (`gemini-3.1-pro-preview`) | via `google-genai` SDK |
| Document parsing / OCR | **Gemini Files API** + document understanding | PDF, docx, markdown, txt, regulatory XML |
| Relational DB | **PostgreSQL 17** | rules, revisions, audit log |
| Search | **Elasticsearch 8.17** | full-text + dense vector hybrid search |
| Graph DB | **Neo4j 5** | rule relationships including the Norm Lineage spine |
| Job Queue | **arq** + **Redis 7** | Background tasks (health, recommendations, correction analysis, lineage propagation, drift checking) |
| MCP | FastMCP (mcp >= 1.9), 12+ tools | subject-agnostic |
| Local orchestration | **Docker Compose** | dev + integration tests |

Do **not** introduce additional frameworks or services without updating this file and PROJECT.md first.

---

## 3. Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                            # FastAPI backend (Python 3.13, uv)
│   │   ├── pyproject.toml
│   │   ├── src/rulerepo_server/
│   │   │   ├── main.py                    # FastAPI app factory
│   │   │   ├── api/v1/                    # REST routers
│   │   │   ├── core/                      # config, logging, errors, auth, middleware
│   │   │   │   └── pii/                   # surface-aware PII sanitization
│   │   │   ├── domain/                    # Rule, Subject, Surface, Actor, Verdict (pure)
│   │   │   ├── services/
│   │   │   │   ├── evaluation/            # Subject-Aware Evaluation Engine
│   │   │   │   │   ├── service.py         # surface-agnostic orchestrator
│   │   │   │   │   ├── core/              # universal evaluator + prompts
│   │   │   │   │   │   ├── evaluator.py
│   │   │   │   │   │   ├── batch_evaluator.py
│   │   │   │   │   │   ├── rule_selector.py
│   │   │   │   │   │   ├── graph_resolver.py
│   │   │   │   │   │   ├── conflict_aggregator.py
│   │   │   │   │   │   ├── verdict_aggregator.py
│   │   │   │   │   │   ├── impact_preview.py
│   │   │   │   │   │   └── prompts/
│   │   │   │   │   │       ├── evaluate_subject.txt
│   │   │   │   │   │       └── evaluate_subject_batch.txt
│   │   │   │   │   └── surfaces/          # per-surface adapters
│   │   │   │   │       ├── base.py        # Surface ABC, SurfaceAdapter ABC
│   │   │   │   │       ├── code/          # CodeChange subject + diff parser
│   │   │   │   │       ├── contract/      # ContractClause subject + clause splitter
│   │   │   │   │       ├── human_action/  # HumanAction subject + event normalizer
│   │   │   │   │       ├── transaction/   # BusinessTransaction subject
│   │   │   │   │       ├── document/      # DocumentRegion subject
│   │   │   │   │       ├── message/       # Message subject
│   │   │   │   │       └── generic/       # GenericSubject (free-form)
│   │   │   │   ├── extraction/            # multi-format ingestion pipeline
│   │   │   │   ├── search.py
│   │   │   │   ├── intent.py
│   │   │   │   ├── intelligence/          # health, analytics, recommendations, persona dashboards
│   │   │   │   ├── discovery/
│   │   │   │   │   └── analyzers/         # claude_md, linter_config, code_patterns, policy_pdf, handbook_md, contract_template, regulation_xml, sales_playbook, ad_compliance_doc
│   │   │   │   ├── feedback/              # correction-to-rule flywheel (multi-surface)
│   │   │   │   ├── federation/            # organizational hierarchy
│   │   │   │   ├── norm_lineage/          # legal/regulatory hierarchy + propagation
│   │   │   │   ├── playground/
│   │   │   │   ├── snapshots/
│   │   │   │   ├── proposals/
│   │   │   │   └── agent_governance/      # generalized to any Actor
│   │   │   ├── domain_packs/              # vertical bundles
│   │   │   │   ├── code/
│   │   │   │   ├── contract/
│   │   │   │   ├── hr_attendance/
│   │   │   │   ├── expense/
│   │   │   │   ├── procurement/
│   │   │   │   ├── communication/
│   │   │   │   ├── compliance/
│   │   │   │   ├── governance/
│   │   │   │   └── marketing/
│   │   │   ├── adapters/
│   │   │   │   ├── postgres/
│   │   │   │   ├── elasticsearch/
│   │   │   │   ├── neo4j/
│   │   │   │   ├── gemini/
│   │   │   │   ├── files/
│   │   │   │   └── connectors/
│   │   │   │       ├── base.py            # SubjectConnector ABC
│   │   │   │       ├── github/
│   │   │   │       ├── slack/
│   │   │   │       ├── email/
│   │   │   │       ├── salesforce/
│   │   │   │       ├── workday/
│   │   │   │       ├── sap/
│   │   │   │       ├── docusign/
│   │   │   │       ├── kintone/
│   │   │   │       ├── teams/
│   │   │   │       └── webhook_generic/
│   │   │   ├── mcp/                       # subject-agnostic tools, resources, prompts
│   │   │   ├── gateway/
│   │   │   ├── integrations/
│   │   │   ├── schemas/
│   │   │   └── workers/                   # arq cron jobs (incl. norm lineage propagation, drift checking)
│   │   ├── alembic/
│   │   └── tests/
│   └── frontend/                          # Next.js 15 + TS + Tailwind (pnpm)
│       └── app/
│           ├── (admin)/                   # rule administrators
│           ├── (engineering)/             # engineering operations
│           ├── (legal)/                   # legal counsel
│           ├── (hr)/                      # HR managers
│           ├── (finance)/                 # finance, accounting, audit
│           ├── (compliance)/              # compliance, executive
│           └── components/
├── packages/
│   ├── rule-client/                       # Python SDK
│   ├── agentic-client/                    # Python agentic SDK
│   └── cli/                               # rulerepo-* CLI tools
├── infra/
│   ├── docker/
│   ├── postgres/
│   ├── elasticsearch/
│   └── neo4j/
├── sample_rules/
│   ├── coding_rules/
│   ├── company_rules/
│   ├── sales_team_rules/
│   ├── legal_rules/                       # NEW (Phase 7)
│   ├── hr_rules/                          # NEW (Phase 7)
│   ├── finance_rules/                     # NEW (later phases)
│   └── templates/                         # YAML rule templates per pack
├── scripts/
├── development/                           # technical docs
├── docs/                                  # mkdocs site
├── docker-compose.yml
├── Makefile
├── pyproject.toml                         # uv workspace root
├── pnpm-workspace.yaml
├── .env.example
├── PROJECT.md
├── IMPROVEMENT.md
└── CLAUDE.md                              # this file
```

When adding a new package, place it under `apps/` (deployable apps) or `packages/` (libraries). When adding a new surface, follow §13. When adding a new domain pack, follow §14. Update `pyproject.toml` (uv workspace) or `pnpm-workspace.yaml` accordingly.

---

## 4. Quick Start (local dev)

The whole stack must come up with one command. If your changes break this, fix it before continuing.

```bash
cp .env.example .env            # then fill in GEMINI_API_KEY
make up                         # or: docker compose up --build -d
```

After about a minute:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | REST + Intent + Evaluate + Gateway + Lineage APIs |
| API docs (OpenAPI) | http://localhost:8000/docs | FastAPI Swagger UI |
| Frontend | http://localhost:3000 | Persona-specific consoles |
| MCP Server | http://localhost:8001 | Subject-agnostic MCP tools |
| PostgreSQL | localhost:5432 | `ruledb` |
| Elasticsearch | http://localhost:9200 | search index |
| Neo4j Browser | http://localhost:7474 | rule graph + norm lineage |
| Redis | localhost:6379 | Job queue |
| arq-worker | — | Background task processor |

The frontend talks to the backend over `NEXT_PUBLIC_API_BASE_URL`. The Python clients talk to the backend over `RULEREPO_SERVER_URL`.

`make seed` loads sample data. After Phase 7, the seed includes Code, Contract, and HR pack samples in equal weight.

---

## 5. Common Commands

### Backend (apps/server)

```bash
cd apps/server
uv sync                         # install deps
uv run uvicorn rulerepo_server.main:app --reload    # run dev server
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

### Python SDKs and CLI (packages/)

```bash
cd packages/rule-client
uv sync && uv run pytest && uv build

# CLI tools
rulerepo-check --diff "$(git diff origin/main...HEAD)" --format github-actions   # CI on Code Surface
rulerepo-hook preflight --file src/api/handler.py --agent-id claude-code         # agent hook (Code)
rulerepo-hook posthoc --file src/api/handler.py
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python
rulerepo-export --project backend-api --output rules.yaml
rulerepo-context generate --server $RULEREPO_SERVER_URL --project p1 --max-rules 30

# New surface-aware verbs (Phase 9+)
rulerepo-review-contract --file ./contracts/draft.docx
rulerepo-check-action --action register_overtime --actor user:E001 --json '{"hours":50}'
rulerepo-review-message --channel slack --file ./logs/channel-export.txt
```

### MCP Server

```bash
uv run rulerepo-mcp                       # stdio (local, for Claude Code)
MCP_TRANSPORT=streamable-http uv run rulerepo-mcp   # HTTP (remote agents)
```

### Whole repo (from root)

```bash
make up                          # start full stack
make down                        # stop
make reset                       # wipe volumes and rebuild
make seed                        # load sample data
make test                        # run all tests
make check                       # format + lint + test (run before committing)
make precommit.install           # install git hooks
```

---

## 6. Coding Conventions

### Python (server + clients)

- **Python 3.13**. Built-in generics (`list[str]`, `dict[str, int]`); `match` where it improves clarity.
- **Type hints are mandatory** on all public functions. mypy must pass on `src/`.
- **Formatter and linter**: `ruff` (both linting and formatting). No `black`, no `isort`.
- **Naming**: snake_case for functions/vars, PascalCase for classes, SCREAMING_SNAKE_CASE for constants.
- **Docstrings**: Google style. Required on all public APIs.
- **Errors**: project-specific exception hierarchy under `rulerepo_server.errors` / `rulerepo.errors`. Never raise bare `Exception`.
- **Logging**: `structlog` with JSON output. Never `print()` outside of one-off scripts.
- **Pydantic v2** for all data validation at API boundaries.
- **Tests**: `pytest` + `pytest-asyncio`.

### TypeScript (frontend)

- **Strict TS**: `"strict": true`. No `any` without justification.
- **App Router** (Next.js 14+ idioms). Server Components by default; Client Components only when needed.
- **Tailwind**: prefer utility classes; centralize design tokens in `tailwind.config.ts`.
- **State**: prefer Server Components and URL state. For client state, `zustand`. For server-state caching, `@tanstack/react-query`.
- **Components**: PascalCase files, one component per file unless tightly coupled.
- **API calls**: generated TypeScript client from the backend's OpenAPI spec. Do not hand-write types that already exist in the API contract.
- **Linting**: ESLint + Prettier.

### Persona separation in the frontend

Each persona route group (`(legal)`, `(hr)`, `(finance)`, `(compliance)`, `(engineering)`, `(admin)`) has its own layout and color accent. **Do not import components across persona groups** unless the component is in `app/components/shared/`. This separation is what keeps each persona's console focused.

### Commits / branches

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- Branch from `main`. Open PRs even for solo work.
- For Phase 7+ refactor work, use prefixed branches: `phase7/...`, `phase8/...`, `phase9/...`.

---

## 7. Backend Architecture Notes

The server is a single FastAPI application that exposes:

- **REST API** at `/api/v1/...` for CRUD on rules, documents, evaluations, projects, federations, norm lineage.
- **Evaluate API** at `/api/v1/evaluate` (backwards-compatible Code Surface) and `/api/v1/evaluate/{surface}` (subject-aware).
- **Intent API** at `/api/v1/intent` for natural-language query routing.
- **Gateway API** at `/api/v1/gateway/...` for webhook-driven enforcement.
- **Intelligence API** at `/api/v1/intelligence/...` for health, analytics, recommendations, digests, persona dashboards.
- **Discovery API** at `/api/v1/discover/...` for automatic rule discovery.
- **Feedback API** at `/api/v1/feedback/...` for correction feedback loop.
- **Federation API** at `/api/v1/federations/...` for organizational hierarchy.
- **Norm Lineage API** at `/api/v1/lineage/...` for upstream/downstream walks and amendment propagation.
- **Proposals / Agent Governance / Playground / Snapshots / Alerts** APIs as documented in PROJECT.md.
- **Integrations** at `/api/v1/integrations/...` for external system webhooks.
- **MCP Server** on a separate port (8001).

### 7.1 Layering rule

`api` depends on `services`, `services` depends on `domain` and `adapters`. `domain` depends on nothing else in the project. **Do not import upward.**

### 7.2 Surface separation

- `services/evaluation/core/` is **surface-agnostic**. It must compile and pass tests with no `surfaces/` imports beyond the registry/factory layer.
- `services/evaluation/surfaces/{surface}/` contains **everything surface-specific** for that surface: subject dataclass, adapter (input parsing), prompt hints, PII sanitizer, audit retention defaults.
- New surface-specific behavior **never goes into `core/`**.

### 7.3 Async

The API layer is fully async. DB calls use `asyncpg` (or `sqlalchemy[asyncio]`); Elasticsearch via the async client; Neo4j via the official async driver; Gemini via `google-genai`.

### 7.4 Domain Packs

Domain Packs (under `domain_packs/`) are **declarative** wherever possible. A pack contributes:

- A `pack.yaml` describing the pack.
- Rule templates in `rules/`.
- Surface adapter references (it does not own the adapter; surfaces live in `services/evaluation/surfaces/`).
- Pack-specific evaluation prompt hints in `prompts/`.
- Connector recommendations (the connector itself lives in `adapters/connectors/`).
- Sample seed data in `samples/`.
- Frontend route placeholders (the actual components live in `apps/frontend/app/(persona)/`).

A pack is loaded at startup. Packs declare their persona, default scopes, and required surfaces. Pack loading is governed by `services/domain_packs/loader.py`.

---

## 8. Frontend Notes

The frontend is the operator console — but **per persona**. Each persona route group is a self-contained console with its own hero metric, layout, and navigation.

### 8.1 Persona route groups

| Route group | Persona | Hero metric |
|---|---|---|
| `(admin)` | Rule administrators | Rule corpus health, total rule count, recent governance actions |
| `(engineering)` | Engineering operations | Compliance rate + 7-day trend (Code Surface) |
| `(legal)` | Legal counsel | Open contract reviews, unresolved conflicts, recent upstream-law amendments |
| `(hr)` | HR managers | This month's violations, 36-agreement headroom, regulation-affected employees |
| `(finance)` | Finance / audit | This month's transaction violations, expense-rejection rate, tax-rule-change impact |
| `(compliance)` | Compliance / executive | Regulatory-amendment-to-internal-rule lead time, regulations with active mappings, open critical alerts |

### 8.2 Shared components

Components shared across personas live in `apps/frontend/components/shared/`. Examples: `RuleCard`, `Badge`, `Pagination`, `RuleGraph`, `NormLineageViewer`, `EvaluationResultPanel`. **Persona-specific components stay inside their persona group.**

### 8.3 The graph view

Norm lineage and rule relationship graphs render with the same library (pick `react-flow` or `cytoscape` and stick with it). The Norm Lineage Viewer is its own component (`components/shared/NormLineageViewer.tsx`).

### 8.4 The home page

The home page picks the dashboard based on the user's role. Admins can switch between personas. Default for unauthenticated dev is `(admin)`.

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
| High-stakes judgment (rule extraction QC, conflict detection, evaluation of HIGH/CRITICAL rules, norm-lineage drift detection) | `gemini-3.1-pro-preview` | strongest reasoning |

Centralize model selection in one config module (`core/llm.py`). Never hardcode model IDs in business logic — always read from config.

### 9.3 Mandatory rules when calling Gemini

- **Do NOT change `temperature`** away from the default (1.0). Lower temperatures degrade Gemini 3 reasoning quality and can cause loops.
- Use **`thinking_level`** (not the legacy `thinking_budget`). Valid values: `minimal`, `low`, `medium`, `high`. Default to `low` for high-throughput tasks, `high` for judgment tasks.
- For function calling, **thought signatures must be cycled through** every turn. The `google-genai` SDK and standard chat history handle this automatically — do not strip signatures from history.
- For PDFs in document processing, set `media_resolution: "media_resolution_medium"` (560 tokens/page).
- Use **structured output** (`response_mime_type="application/json"` + `response_json_schema`) for any call that must return data the system parses.

### 9.4 Document ingestion (PDF, docx, text, markdown, regulatory XML)

- **PDFs**: Files API for documents > a few pages; inline `Part.from_bytes(...)` for small/one-shot.
- **docx**: parse to text via `python-docx` for structure; pass text to Gemini for normative-sentence detection.
- **text and markdown**: pass as plain text. Gemini's "document understanding" only renders PDFs meaningfully; for `.md`/`.txt`, treat as text-only.
- **Regulatory XML** (e.g., 法令標準データ形式): use the XML parser in `extraction/structural_parser.py`; pass structured text to Gemini.
- The extraction pipeline (`services/extraction/`) wraps these calls. Do not bypass it from random parts of the codebase.

### 9.5 Cost and latency discipline

- Cache LLM responses by `hash(inputs + model + prompt_version + locale)` in Postgres. Invalidate on rule revision.
- Use `gemini-3.1-flash-lite-preview` only if explicitly approved.
- Long-context calls (large rule corpus + large doc) should use **context caching** for repeated reuse.
- **Batched evaluation** (single LLM call for all selected rules) is the default; per-rule fallback is automatic.

### 9.6 Determinism, locale, and audit

- Every LLM call that produces a verdict, a candidate rule, or a relationship suggestion **must** log: `model_id`, `prompt_version`, `inputs`, `outputs`, `latency`, `timestamp`, `surface`, `locale`, `actor`. Goes to the audit log.
- Prompts live in `services/<area>/prompts/` (or `surfaces/<surface>/prompts/`) as standalone files, versioned in git. **No inline prompt strings scattered across the codebase.**
- For bilingual rules, evaluate against the rule statement in the matching `subject.locale` when available; otherwise use the canonical statement and log a `cross_locale_evaluation` warning.

### 9.7 Surface-specific prompt hints

Each surface has its own hint file in `surfaces/<surface>/prompts/`. The universal prompt `evaluate_subject.txt` injects the appropriate hint based on `subject.surface`. **Do not duplicate the universal prompt per surface.**

---

## 10. Data Layer

### 10.1 PostgreSQL (system of record)

- Stores rules, revisions, source documents, evaluations, audit log, federations, norm lineage edges (mirrored from Neo4j for transactional consistency).
- Migrations: `alembic`. One head per branch; rebase migrations before merging.
- The audit log table is **append-only**. Enforced by Postgres trigger that rejects updates/deletes. Hash chain links each row to its predecessor.
- **Surface-aware retention**: a daily worker (`prune_audit_log`) deletes rows older than the retention configured for their surface (see PROJECT.md §10.2). Configurable per scope.

### 10.2 Elasticsearch (search)

- Index `rules` with: `statement`, `statement_translations`, `tags`, `tech_scope`, `org_scope`, `modality`, `severity`, `effective_period`, `applies_to_surfaces`, `norm_tier`, `locale`, `embedding`.
- BM25 + kNN hybrid scoring. Rerank top-k with the LLM only when "smart" search is requested.
- Re-index on rule revision. Do not run partial updates that risk drift.

### 10.3 Neo4j (relationship graph + norm lineage)

- Node label: `Rule`. Node `id` matches the Postgres rule ID.
- Relationships: `REFINES`, `OVERRIDES`, `CONFLICTS_WITH`, `DEPENDS_ON`, `DERIVES_FROM`, `SUCCEEDS`, `TRANSLATES`. Direction documented in PROJECT.md §5.3.
- Postgres is the source of truth for rule existence; Neo4j is a derived projection. If they disagree, Postgres wins and Neo4j is rebuilt by `scripts/reconcile_graph.py`.
- The `DERIVES_FROM` chain is the Norm Lineage spine. The `norm_lineage` service walks it for upstream/downstream queries.

### 10.4 Surface-aware schema additions (Phase 8)

- `rules.applies_to_surfaces` (text[]): surfaces the rule applies to.
- `rules.tech_scope` (text[]) and `rules.org_scope` (text[]): split from the legacy `scope`.
- `rules.norm_tier` (enum): LAW / REGULATION / GUIDELINE / CORPORATE_POLICY / DEPARTMENT_RULE / OPERATIONAL_RULE.
- `rules.norm_authority` (text): citation of upstream authority.
- `rules.locale` (text, default `en`).
- `rules.statement_translations` (jsonb): locale → translated statement.
- `evaluations.surface` (text), `evaluations.actor_kind` (text), `evaluations.actor_identifier` (text), `evaluations.locale` (text).
- `evaluations.agent_id` is retained as a backwards-compatible view onto `actor_identifier` when `actor_kind = 'agent'`.

---

## 11. Testing

- **Unit tests**: pure logic in `domain/`. No external services. Fast.
- **Integration tests**: spin up docker-compose services in CI. Use `testcontainers-python` if running in CI without compose.
- **LLM tests**: never call the real Gemini API in unit tests. Use a mock client. For integration, gate behind an env flag (`RULEREPO_LIVE_LLM=1`).
- **Surface tests**: each surface has its own integration suite under `tests/surfaces/<surface>/` covering the adapter, the universal prompt with that surface's hints, and the audit log retention policy.
- **Pack tests**: each Domain Pack has a smoke test under `tests/domain_packs/<pack>/` that loads the pack, imports its rule templates, and runs sample evaluations end-to-end.
- **Frontend tests**: Vitest + React Testing Library for components; Playwright for end-to-end. Persona route groups have separate test files.
- **Eval harness**: a separate test suite that validates LLM-driven features (rule extraction quality, conflict detection precision/recall, norm-lineage drift accuracy) against curated fixtures. Runs nightly, not on every PR.

---

## 12. Environment Variables

All env vars live in `.env.example`. Never commit `.env`.

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
GITHUB_TOKEN=

# Alerts and digests
ALERT_WEBHOOK_URL=
DIGEST_WEBHOOK_URL=
NOTIFICATION_WEBHOOK_URL=
NOTIFICATION_WEBHOOK_TYPE=

# Domain Pack loading
ENABLED_PACKS=code,contract,hr_attendance      # comma-separated; controls which packs load at startup
DEFAULT_PERSONA=admin                          # for unauthenticated dev

# Surface-aware retention overrides (optional)
AUDIT_RETENTION_DAYS_CODE=365
AUDIT_RETENTION_DAYS_CONTRACT=3650
AUDIT_RETENTION_DAYS_HUMAN_ACTION=2555
AUDIT_RETENTION_DAYS_TRANSACTION=3650
AUDIT_RETENTION_DAYS_DOCUMENT=3650
AUDIT_RETENTION_DAYS_MESSAGE=1095

# Norm Lineage
LINEAGE_AMENDMENT_WEBHOOK_URL=                 # external system can post amendment signals here

# Multi-locale
DEFAULT_LOCALE=en
SUPPORTED_LOCALES=en,ja

# Connectors (per integration; only set those used)
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
EMAIL_IMAP_HOST=
EMAIL_IMAP_USER=
EMAIL_IMAP_PASSWORD=
SALESFORCE_CLIENT_ID=
SALESFORCE_CLIENT_SECRET=
WORKDAY_TENANT_URL=
WORKDAY_USERNAME=
WORKDAY_PASSWORD=
SAP_BASE_URL=
SAP_CLIENT_ID=
DOCUSIGN_INTEGRATION_KEY=
KINTONE_BASE_URL=
KINTONE_API_TOKEN=
TEAMS_TENANT_ID=
TEAMS_CLIENT_ID=
TEAMS_CLIENT_SECRET=

# Agent Governance
AGENT_TRUST_PROMOTION_ENABLED=true
AGENT_MASTERY_THRESHOLD=0.95
AGENT_PATTERN_MIN_EVIDENCE=10
```

When you add a new env var, update `.env.example` in the same change.

---

## 13. Important Rules for Claude Code

These are non-negotiable. Violating them breaks the system, the architecture, or wastes review time.

### 13.1 Universal rules

1. **Read PROJECT.md and IMPROVEMENT.md before designing anything new.** Domain decisions belong there, not here. The Phase 7+ direction is a course correction, not optional.
2. **Run linters, formatters, and type checkers before claiming a task is done.** `ruff`, `mypy`, `pnpm lint`, `pnpm typecheck`. CI will reject otherwise.
3. **Never commit secrets.** Use `.env` and `.env.example`.
4. **Never tweak Gemini `temperature`.** Default 1.0 stays.
5. **Never use deprecated Gemini params.** Use `thinking_level`, not `thinking_budget`. Use `google-genai`, not `google-generativeai`.
6. **Never bypass the extraction pipeline** to call Gemini directly from random services.
7. **Never write to the audit log table from application code.** Only the evaluation/extraction services write, and only through the audit-log adapter that enforces hash chaining.
8. **Never make Postgres and Neo4j disagree silently.** If you write to one, write to the other through the same service. If you can only write to one, queue the other change.
9. **Never delete rules.** Use `effective_period.valid_until` to retire them. Past evaluations must remain re-explainable.
10. **Keep `make up` working.** If your change breaks the local stack, fix it before merging.
11. **Update PROJECT.md and CLAUDE.md** when introducing a new dependency, service, surface, pack, or architectural decision. Code without doc updates does not ship.
12. **Prefer fewer dependencies.** Every added library is a long-term cost. Justify additions in the PR description.
13. **Write structured logs, not `print`.** Logs are operational data.
14. **Tests for LLM-driven features must mock the LLM** unless the test is explicitly an eval test.
15. **When unsure, ask.** Open an issue or a draft PR with the question. Do not guess on domain semantics — wrong rules are worse than no rules.

### 13.2 Phase 7+ refactor discipline (until non-code packs are in production)

16. **Do not add new code-only features.** Phase 5–6 sub-features in flight may complete; new ones do not start. Bug fixes and refactors are fine.
17. **Do not add code-specific concerns to `services/evaluation/core/`.** All code-specific behavior lives in `services/evaluation/surfaces/code/`. If you find yourself writing `if surface == "code"` inside `core/`, stop and reconsider.
18. **Do not add a new endpoint that takes `diff` or `file_paths` as the primary input.** New evaluation endpoints take a `Subject` payload. Existing code-specific endpoints remain for backwards compatibility.
19. **Do not add MCP tools whose signatures assume code.** New tools accept `subject_ref` / `subject_payload` / `surface`. Code-specific tools remain as backwards-compatible aliases.
20. **Do not extend the engineering dashboard with new metrics.** New metrics go on the relevant persona console (legal, HR, finance, compliance).
21. **Do not add new sample data or templates that are code-only.** Every PR that adds samples must add at least one non-code sample alongside.
22. **Do not extend Agent Governance with AI-agent-only assumptions.** Agent Governance is being generalized to any `Actor` (human, system, agent). New features must work for all `Actor.kind` values.

### 13.3 Surface and Pack discipline

24. **A new surface must include**: a `Subject` dataclass, a `SurfaceAdapter`, a prompt hints file, a PII sanitizer, and a default audit retention. All in `services/evaluation/surfaces/<name>/`. Add to `Surface` enum. Do not modify the universal prompt in `core/`.
25. **A new Domain Pack must include**: a `pack.yaml`, a `rules/` directory with at least 5 seed rules, a persona assignment, a `samples/` directory, and frontend route placeholders under the persona route group. Add to `ENABLED_PACKS` in `.env.example`.
26. **A pack does not own its surface.** The Code Pack uses the Code Surface; the Contract Pack uses the Contract Surface. Multiple packs can share a surface.
27. **A pack does not own its connector.** Connectors live in `adapters/connectors/`. Packs *recommend* connectors via `pack.yaml`.

### 13.4 Locale and norm-lineage discipline

28. **Never lose the canonical locale.** Translations are explicit; the `Rule.locale` field is authoritative. When evaluating with a non-canonical locale, log the warning.
29. **Never collapse Norm Lineage into Federation in the UI.** They are two trees, two pages, two query backends. If they appear together in a single component, the component is wrong.
30. **Never silently change a `norm_tier`.** Norm tier changes are governance events; they require a Proposal and approval.

---

## 14. Phase 7+ Implementation Guidance

These are architecture decisions and patterns for Phase 7 and beyond. Read before implementing any improvement.

### 14.1 Phase 7: Stop the Bleeding

Goal: prevent further drift, restore positioning.

- **README rewrite**: lead with cross-organizational mission. Code is one example among many.
- **GitHub About + Topics**: set as documented in IMPROVEMENT.md §7.3–§7.4.
- **PROJECT.md update**: §6.4 "Code-Aware Evaluation Engine" repositioned as the Code Surface Adapter, not "the core differentiator".
- **Sample data parity**: add Contract Pack v0.1 and HR Pack v0.1 seed data. `make seed` installs all three (Code, Contract, HR) in equal weight.
- **Topics order**: in the README "What You Can Do" section, put non-code workflows first.
- **Test that `make seed` produces a reasonable cross-org first impression**.

### 14.2 Phase 8: Surface Abstraction (the structural fix)

Goal: introduce `Subject`, `Surface`, `Actor`. Reorganize the evaluation core. Split `scope`. Replace `agent_id`.

#### 14.2.1 Domain types

In `domain/evaluation.py`:

```python
class Surface(StrEnum):
    CODE = "code"
    CONTRACT = "contract"
    HUMAN_ACTION = "human_action"
    TRANSACTION = "transaction"
    DOCUMENT = "document"
    MESSAGE = "message"
    GENERIC = "generic"

@dataclass(frozen=True)
class Actor:
    kind: Literal["human", "system", "agent"]
    identifier: str
    attributes: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Subject:
    surface: Surface
    identifier: str
    payload: dict[str, Any]
    facts: dict[str, Any]
    actor: Actor | None
    timestamp: datetime
    locale: str = "en"
```

In `domain/rule.py`, add to `Rule`:

```python
applies_to_surfaces: list[Surface] = [Surface.GENERIC]
norm_tier: NormTier = NormTier.OPERATIONAL_RULE
norm_authority: str | None = None
locale: str = "en"
statement_translations: dict[str, str] = field(default_factory=dict)
tech_scope: list[str] = field(default_factory=list)
org_scope: list[str] = field(default_factory=list)
```

`scope` is retained as a deprecated read-only property that concatenates `tech_scope` and `org_scope`.

#### 14.2.2 Evaluation core re-layout

Move `services/evaluation/diff_parser.py` and the diff-handling parts of `services/evaluation/context_assembler.py` into `services/evaluation/surfaces/code/adapter.py`. The remaining surface-agnostic logic stays in `services/evaluation/core/`. Authoring `evaluate_subject.txt` (universal) and `evaluate_subject_batch.txt` (universal batch) replaces the four legacy prompt files; the legacy prompts are kept as `surfaces/code/prompts/` hints for backwards compatibility.

#### 14.2.3 New API endpoint

```
POST /api/v1/evaluate/{surface}
Body: { subject: SubjectPayload, mode: preflight|posthoc|sidecar, options?: ... }
```

`POST /api/v1/evaluate` (no path param) remains as a backwards-compatible alias that constructs a Code Surface subject from `diff` / `file_paths` in the body.

#### 14.2.4 Migration

- Migration 023: add `applies_to_surfaces`, `norm_tier`, `norm_authority`, `locale`, `statement_translations`, `tech_scope`, `org_scope` to `rules`. Backfill `applies_to_surfaces = [code]` for existing rules. Backfill `tech_scope` and `org_scope` from legacy `scope` by prefix heuristic.
- Migration 024: add `surface`, `actor_kind`, `actor_identifier`, `locale` to `evaluations`. Backfill `surface = code`, `actor_kind = agent` where `agent_id IS NOT NULL`, otherwise `actor_kind = system`.

### 14.3 Phase 9: Contract Pack

Goal: ship the first non-code pack end-to-end.

- Surface adapter under `services/evaluation/surfaces/contract/`:
  - `subject.py` — `ContractClause` dataclass (text, position, clause_type, parties, locale).
  - `adapter.py` — splits a contract document into clauses; integrates `bilingual_pairer` for EN/JA pairs.
  - `prompts/contract_hints.txt` — surface hints injected into `evaluate_subject.txt`.
  - `pii.py` — natural-person-name redaction defaults.
- Domain Pack at `domain_packs/contract/`:
  - `pack.yaml` (persona: legal, surfaces: [contract, document]).
  - `rules/` with 30+ NDA / MSA / SOW template clauses.
  - `samples/` with 3 anonymized contracts.
- Frontend pages under `apps/frontend/app/(legal)/`:
  - `contracts/` — list of contracts under review.
  - `clauses/` — clause search and conflict detection.
  - `redlines/` — revision diffs (uses `redline_differ.py`).
  - `lineage/` — Norm Lineage Viewer (shared component).
- CLI: `rulerepo-review-contract --file ./draft.docx`.
- MCP tools: `find_clause_conflicts(contract_text)`.

### 14.4 Phase 10: Norm Lineage

Goal: make norm-tier hierarchy first-class with upstream-amendment propagation.

- Norm Lineage walker in `services/norm_lineage/walker.py`. Two methods: `upstream(rule_id)` returns the chain to the highest-tier norm; `downstream(rule_id)` returns all descendants.
- Amendment propagation worker in `workers/tasks.py`: `propagate_norm_amendment` runs on `effective_period` updates of LAW / REGULATION rules and flags downstream rules with status `pending_norm_change_review`.
- Norm Lineage Viewer at `apps/frontend/components/shared/NormLineageViewer.tsx`. Used by `(legal)/lineage/` and `(compliance)/regulatory/` pages.
- API endpoints: `GET /api/v1/lineage/{rule_id}/upstream`, `GET /api/v1/lineage/{rule_id}/downstream`.
- MCP tool: `lookup_norm_lineage(rule_id)`.

### 14.5 Phase 10: Multi-Language

Goal: support bilingual rules and Japanese-first operations.

- Translation worker in `workers/tasks.py`: `verify_translation_drift` runs daily, compares `statement_translations` pairs with the LLM, flags drift > threshold.
- Evaluation engine selects rule statement matching `subject.locale` when available; otherwise uses canonical and logs `cross_locale_evaluation` warning.
- Sample rules in `sample_rules/legal_rules/jp/` (Japanese contract clauses) and `sample_rules/hr_rules/jp/` (Japanese labor-law-derived rules).
- Frontend: locale switcher in the persona consoles; `LANG` cookie; default from `DEFAULT_LOCALE`.

### 14.6 Phase 11: HR and Communication Packs

Goal: prove Domain Pack architecture is general.

#### 14.6.1 HR Pack

- Surface adapter `services/evaluation/surfaces/human_action/`:
  - `subject.py` — `HumanAction` dataclass.
  - `adapter.py` — translates HRIS events into `HumanAction` subjects.
  - `prompts/action_hints.txt`.
  - `pii.py` — employee-name redaction by default.
- Pack at `domain_packs/hr_attendance/`:
  - 36-agreement tracking rules, overtime limit rules, leave-policy rules, child-care/elder-care rules.
  - Sample HRIS events.
- Connector `adapters/connectors/workday/` (initial; ADP and others later).
- Frontend pages under `(hr)/`.
- CLI: `rulerepo-check-action --action register_overtime --actor user:E001 --json '{...}'`.
- MCP tool: `check_action(actor, action, payload)`.

#### 14.6.2 Communication Pack

- Surface adapter `services/evaluation/surfaces/message/`:
  - `subject.py` — `Message` dataclass.
  - `adapter.py` — normalizes Slack / email / Teams messages.
  - `prompts/message_hints.txt`.
  - `pii.py` — email and customer-ID redaction.
- Pack at `domain_packs/communication/`:
  - Harassment, customer-data confidentiality, regulated-substance discussion, product-claim accuracy rules.
- Connectors `adapters/connectors/slack/` and `adapters/connectors/email/`.
- MCP tool: `review_communication(channel, content)`.

### 14.7 Phase 12: Connector Layer Maturation

Goal: standardize the connector contract; integrate with major business systems.

- `SubjectConnector` ABC in `adapters/connectors/base.py`:
  - `async def normalize(event: dict) -> Subject`
  - `async def push(subject: Subject) -> EvaluationResult` (preflight/posthoc/sidecar mode controlled at the gateway level)
- Implement Salesforce, SAP, DocuSign, Kintone, Teams connectors per pilot demand.
- Integration tests use mock servers (e.g., `responses`-style fixtures).
- `(compliance)` persona console aggregates cross-domain views.

### 14.8 Practical patterns

- **Surface registration**: each surface registers its `SurfaceAdapter` via a registry in `services/evaluation/surfaces/__init__.py`. The evaluation core consults the registry; never hardcoded surface lists.
- **Pack discovery**: at startup, `services/domain_packs/loader.py` scans `domain_packs/` for `pack.yaml`, validates, and registers. `ENABLED_PACKS` controls which load.
- **Persona route registration**: each pack's `pack.yaml` declares its `persona`; the frontend consults a generated manifest to know which routes to surface in the sidebar.
- **Audit retention**: a daily worker (`prune_audit_log`) reads per-surface retention from env or settings and deletes expired rows. Per-scope overrides are respected.
- **Locale fallback**: `Subject.locale` → `Rule.statement_translations` → `Rule.locale`. Always log when fallback occurs.

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
- arq: https://arq-docs.helpmanual.io/
- FastMCP: https://github.com/jlowin/fastmcp
- 法令標準データ形式 (Japanese regulation XML standard): https://www.digital.go.jp/

---

*This file is a contract. If you (Claude Code) find a conflict between this file and the user's request, surface the conflict and ask. Do not silently override.*

*This file supersedes any prior CLAUDE.md guidance that treats Code as the privileged surface. Phase 7+ rules take precedence over historical Phase 5–6 patterns where they conflict.*

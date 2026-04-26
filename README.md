# Rule Repository

A platform for managing, searching, and enforcing natural-language rules — laws, contracts, internal policies, engineering guidelines, and documentation standards — using LLMs and AI agents.

Where traditional rule engines require translating human rules into formal logic (and losing nuance), the Rule Repository keeps the rule as written and uses LLMs to interpret, search, and enforce them at runtime.

---

## Quick Start

```bash
# 1. Clone and configure
git clone <repo-url> && cd rule-repository
cp .env.example .env          # fill in your GEMINI_API_KEY

# 2. Start everything
docker compose up --build

# 3. Load sample rules
uv run python scripts/seed_data.py
```

That's it. You now have:

| Service | URL | What it does |
|---|---|---|
| Backend API | http://localhost:8000 | REST, Evaluate, Intent, Gateway, Intelligence APIs |
| API Docs | http://localhost:8000/docs | Interactive Swagger UI |
| Frontend | http://localhost:3000 | Operator console |
| MCP Server | localhost:8001 | AI agent tool integration |
| PostgreSQL | localhost:5432 | Rule storage (system of record) |
| Elasticsearch | http://localhost:9200 | Full-text + vector search |
| Neo4j Browser | http://localhost:7474 | Rule relationship graph |

---

## What Can It Do?

### Store rules in natural language

Every rule is a structured envelope around a natural-language statement — with modality (MUST / SHOULD / MAY), severity, scope, tags, rationale, governance, and source provenance. The statement is the source of truth; metadata exists for indexing, not to override meaning.

### Search rules five ways

- **Full-text** (BM25) — keyword matching with stemming
- **Vector** (semantic similarity) — meaning-based search using 768-dim embeddings
- **Hybrid** — BM25 + vector combined for best results
- **Category** — filter by modality, severity, scope, tags
- **Context** — give it facts about a situation, get applicable rules back

### Evaluate code changes against rules

The **Code-Aware Evaluation Engine** is the core product:

```
Input:  diff of changes to src/api/handlers/payment.py
Output:
  Rule #17 (MUST: All API handlers must validate input with Pydantic models)
    Verdict: DENY
    Location: payment.py:45-52, function process_refund()
    Issue: Raw dict access without Pydantic validation
    Fix: Define a ProcessRefundRequest model
```

It understands file paths (scope matching), diffs (evaluates only what changed), code structure (references specific functions), and returns actionable fix suggestions. Model selection is tiered by severity — Flash for routine rules, Pro for CRITICAL.

### Deliver rules to AI coding agents

Via the **MCP Server**, coding agents (Claude Code, Cursor, etc.) can:
- Get rules for their current file context before writing code
- Evaluate compliance of their changes
- Understand why a rule exists and how it relates to other rules

The key tool is `get_rules_for_context` — it delivers formatted rules to the agent's context window, grouped by MUST/SHOULD/MAY, without the agent needing to know the rules exist.

### Enforce rules in CI and PR review

- **GitHub PR Review** — webhook processes `pull_request` events, posts structured review comments with per-rule verdicts and fix suggestions
- **CI Pipeline** — `rulerepo-check` CLI exits 0 (ALLOW), 1 (DENY), 2 (NEEDS_CONFIRMATION). Supports `--format github-actions` for inline annotations
- **Agent Hooks** — `rulerepo-hook preflight` injects rules before edit, `posthoc` evaluates changes after edit

### Import rules from existing sources

Upload PDFs, text, or markdown files. The extraction pipeline (powered by Gemini) proposes candidate rules with modality, severity, and metadata. A human reviews and approves.

Import existing CLAUDE.md files: `rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python`

### Monitor rule health

The Intelligence dashboard scores every rule across 6 dimensions (completeness, clarity, test coverage, freshness, activity, owner engagement) and generates automated recommendations: retire dormant rules, clarify ambiguous wording, escalate persistent violations.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Rule Management Server                      │
│                                                                │
│  Extraction   Search      Code-Aware         Intelligence     │
│  Pipeline     (5 modes)   Evaluation Engine   & Observability │
│                           (LLM-as-Judge)                      │
│                                                                │
│  PostgreSQL   Elasticsearch   Neo4j         Audit Log         │
│  (truth)      (search)        (graph)       (hash-chained)    │
│                                                                │
│  REST API  │  Evaluate API  │  Intent API  │  Gateway API     │
└────────────┼────────────────┼──────────────┼──────────────────┘
             │                │              │
    ┌────────┼────────┐  ┌───┼──────┐  ┌───┼────────┐
    │        │        │  │   │      │  │   │        │
  Rule    Agentic   MCP    CLI    GitHub   Gateway
  Client  Client   Server  Tools  App      (webhooks)
  (SDK)   (SDK)   (agents) (CI)   (PRs)
```

**Three data stores, each for what it's best at:**
- **PostgreSQL** — source of truth for rules, revisions, audit log, documents, policies
- **Elasticsearch** — full-text + vector search (BM25 + dense_vector 768d)
- **Neo4j** — rule relationship graph (REFINES, OVERRIDES, CONFLICTS_WITH, DEPENDS_ON, DERIVES_FROM, SUCCEEDS)

If Neo4j and Postgres ever disagree, Postgres wins. `scripts/reconcile_graph.py` rebuilds Neo4j from scratch.

---

## Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                  # FastAPI backend (Python 3.13, uv)
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/          # 7 routers: rules, search, evaluate, intent, intelligence, extraction, relationships
│   │   │   ├── core/            # Config, logging, errors, auth, middleware, PII sanitization
│   │   │   ├── domain/          # Pure domain models (Rule, Evaluation, Verdict, AuditEntry)
│   │   │   ├── services/
│   │   │   │   ├── evaluation/  # Code-Aware Evaluation Engine (diff parser, rule selector, LLM judge)
│   │   │   │   ├── extraction/  # Document ingestion pipeline (Gemini-powered)
│   │   │   │   ├── intelligence/# Health scoring, analytics, recommendations
│   │   │   │   └── context_delivery/ # Smart rule selection + formatting for agents
│   │   │   ├── adapters/        # Postgres, Elasticsearch, Neo4j, Gemini, file storage
│   │   │   ├── mcp/             # MCP server (5 tools, 2 resources, 3 prompts)
│   │   │   ├── gateway/         # Enforcement gateway (normalizers, policies, SSE)
│   │   │   ├── integrations/    # GitHub webhook, CI output formatters
│   │   │   └── schemas/         # Pydantic request/response models
│   │   ├── alembic/             # 4 database migrations
│   │   └── tests/               # 15 test files (unit + integration)
│   └── frontend/                # Next.js 15 + TypeScript + Tailwind CSS 4
│       ├── app/(dashboard)/     # 6 pages: rules, search, documents, intelligence, gateway, integrations
│       ├── components/          # Badge, RuleCard, RuleGraph, RuleEditForm, Pagination, Providers
│       └── lib/api.ts           # Typed API client
├── packages/
│   ├── rule-client/             # Python SDK — async client with rules, search, intent, documents resources
│   ├── agentic-client/          # Python SDK — evaluation via POST /api/v1/evaluate
│   └── cli/                     # CLI tools: rulerepo-check, rulerepo-hook, rulerepo-ingest
├── infra/
│   ├── docker/                  # Multi-stage Dockerfiles (server + frontend with dev/prod targets)
│   ├── postgres/                # Init SQL (uuid-ossp, pgcrypto extensions)
│   ├── elasticsearch/           # Index template (768-dim dense_vector) + setup script
│   └── neo4j/                   # Uniqueness constraints + indexes
├── scripts/
│   ├── seed_data.py             # 10 sample rules (HR, engineering, contracts, compliance)
│   ├── reconcile_graph.py       # Rebuild Neo4j from Postgres
│   └── generate_claude_md.py    # Export rules as static CLAUDE.md sections
├── development/                 # 7 technical docs (architecture, API ref, evaluation engine, MCP, integrations, testing)
├── docs/                        # mkdocs site (20 pages across 8 sections)
├── docker-compose.yml           # Full local stack (8 services + 4 volumes)
└── pyproject.toml               # uv workspace root (4 members)
```

---

## API Overview

All endpoints under `/api/v1`. Interactive docs at [localhost:8000/docs](http://localhost:8000/docs).

### Rules

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/rules` | Create a new rule |
| `GET` | `/api/v1/rules` | List rules (paginated, filterable) |
| `GET` | `/api/v1/rules/{id}` | Get a single rule |
| `PATCH` | `/api/v1/rules/{id}` | Update a rule (creates revision) |
| `POST` | `/api/v1/rules/{id}/retire` | Retire a rule (never delete) |
| `GET` | `/api/v1/rules/{id}/revisions` | Revision history |
| `GET` | `/api/v1/rules/{id}/graph` | Neo4j subgraph |

### Evaluate

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/evaluate` | Full code-aware evaluation (diffs, files, or facts) |
| `POST` | `/api/v1/evaluate/quick` | Simplified non-code evaluation |
| `POST` | `/api/v1/evaluate/applicable-rules` | Which rules apply, without evaluation |

### Search

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/search/fulltext` | BM25 keyword search |
| `POST` | `/api/v1/search/vector` | Semantic similarity |
| `POST` | `/api/v1/search/hybrid` | BM25 + vector combined |
| `POST` | `/api/v1/search/category` | Filter by modality/severity/scope/tags |
| `POST` | `/api/v1/search/context` | Given facts, find applicable rules |

### Other

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/intent` | Natural language query (classify + route) |
| `POST` | `/api/v1/documents/upload` | Upload a document for extraction |
| `POST` | `/api/v1/documents/{id}/extract` | Run extraction pipeline |
| `GET` | `/api/v1/intelligence/dashboard` | Health scores, analytics, recommendations |
| `POST` | `/api/v1/gateway/ingest/{source}` | Webhook receiver (GitHub, Slack, generic) |
| `POST` | `/api/v1/integrations/webhooks/github` | GitHub PR review webhook |
| `GET` | `/healthz` | Liveness probe |
| `GET` | `/readyz` | Readiness probe (checks PG, ES, Neo4j) |

---

## Python SDKs

### Rule Client

```python
from rulerepo import RuleClient

async with RuleClient("http://localhost:8000", api_key="...") as client:
    # Search
    results = await client.search.hybrid("overtime monthly limit")

    # Ask in natural language
    answer = await client.intent.ask("What are the rules for overtime?")

    # CRUD
    rule = await client.rules.create(
        "Monthly overtime must not exceed 45 hours",
        modality="MUST_NOT", severity="HIGH", scope=["hr/attendance"],
    )
    await client.rules.retire(rule.id)

    # Document extraction
    upload = await client.documents.upload("policy.pdf")
    extraction = await client.documents.extract(upload.document_id)
```

### Agentic Client

```python
from rulerepo_agentic import AgenticRuleClient

async with AgenticRuleClient("http://localhost:8000", scope="hr/attendance") as client:
    result = await client.evaluate(
        context={"employee_id": "E001", "overtime_hours": 50},
        intent="register_overtime",
        mode="preflight",
        diff="...",  # optional: unified diff for code evaluations
    )
    # result["overall_verdict"] = "DENY"
    # result["violations"] = [{"rule_id": "...", "fix_suggestion": "..."}]
```

### CLI Tools

```bash
# CI pipeline: check code against rules
rulerepo-check --diff "$(git diff origin/main...HEAD)" --format github-actions

# Agent hook: inject rules before editing
rulerepo-hook preflight --file src/api/handlers/payment.py

# Agent hook: evaluate changes after editing
rulerepo-hook posthoc --file src/api/handlers/payment.py

# Import existing CLAUDE.md as rules
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python
```

---

## MCP Server (AI Agent Integration)

The Rule Repository exposes an [MCP](https://modelcontextprotocol.io) server so AI coding agents can query and enforce rules as tools.

**Tools:**
| Tool | What it does |
|---|---|
| `get_rules_for_context` | Deliver formatted rules for current file/task context (the key tool) |
| `evaluate_compliance` | Evaluate a code change against applicable rules |
| `search_rules` | Search rules by natural language query |
| `explain_rule` | Get detailed explanation with rationale and relationships |
| `find_conflicts` | Find rules that conflict with a given rule or proposed change |

**Resources:**
- `rule://{rule_id}` — single rule with full metadata
- `ruleset://{scope}` — dynamic rule set (like a CLAUDE.md section that's always up-to-date)

**Claude Code configuration:**

```json
{
  "mcpServers": {
    "rule-repository": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/apps/server", "rulerepo-mcp"],
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://rule:rule@localhost:5432/ruledb",
        "ELASTICSEARCH_URL": "http://localhost:9200",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "ruledev"
      }
    }
  }
}
```

---

## Development

### Prerequisites

- **Python 3.13+** via [uv](https://docs.astral.sh/uv/)
- **Node.js 22+** via [pnpm](https://pnpm.io/)
- **Docker** for the full stack

### Backend

```bash
cd apps/server
uv sync                                                   # install deps
uv run uvicorn rulerepo_server.main:app --reload          # dev server
uv run pytest                                             # tests
uv run ruff check . && uv run ruff format .               # lint + format
```

### Frontend

```bash
cd apps/frontend
pnpm install && pnpm dev        # dev server at :3000
pnpm lint && pnpm typecheck     # ESLint + TypeScript
```

### All tests (from repo root)

```bash
uv run python -m pytest         # 142 tests across server + SDK
```

### Docker

```bash
docker compose up --build       # start everything
docker compose down -v          # tear down + wipe data
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key |
| `DATABASE_URL` | No | `postgresql+asyncpg://rule:rule@postgres:5432/ruledb` | PostgreSQL |
| `ELASTICSEARCH_URL` | No | `http://elasticsearch:9200` | Elasticsearch |
| `NEO4J_URI` | No | `bolt://neo4j:7687` | Neo4j |
| `LLM_DEFAULT_MODEL` | No | `gemini-3-flash-preview` | Fast model for routine tasks |
| `LLM_JUDGE_MODEL` | No | `gemini-3.1-pro-preview` | Strong model for CRITICAL rules |
| `AUTH_REQUIRED` | No | `false` | Require API key auth (set `true` for production) |
| `MCP_TRANSPORT` | No | `stdio` | MCP transport: `stdio` or `streamable-http` |
| `GITHUB_WEBHOOK_SECRET` | No | — | For GitHub PR review integration |

---

## Domain Model

The central entity is a **Rule** — a natural-language normative statement:

```
DRAFT ──> REVIEW ──> APPROVED ──> EFFECTIVE ──> SUPERSEDED ──> RETIRED
  │          │                        │                           ^
  └──────────┴────────────────────────┴───────────────────────────┘
                      (can retire from any state)
```

Status transitions are validated — you can't jump from DRAFT to EFFECTIVE. RETIRED is terminal.

Rules form a **graph** through relationships: REFINES, OVERRIDES, CONFLICTS_WITH, DEPENDS_ON, DERIVES_FROM, SUCCEEDS.

---

## Key Design Decisions

- **Rules are never deleted.** They're retired via `effective_period.valid_until`. Past evaluations must remain explainable.
- **Postgres is the source of truth.** Elasticsearch and Neo4j are derived. If they disagree, Postgres wins.
- **Audit log is append-only.** A PostgreSQL trigger prevents UPDATE/DELETE. Entries are hash-chained.
- **Gemini temperature is always 1.0.** Lower values degrade reasoning quality.
- **LLM calls are cached** by `hash(inputs + model + prompt_version)`. Invalidated on rule revision.
- **PII is sanitized** before sending to Gemini and in audit log details.
- **Evaluation is tiered**: Flash for LOW/MEDIUM rules, Flash+medium-thinking for HIGH, Pro+high-thinking for CRITICAL.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS 4, React Flow |
| LLM | Gemini 3 Flash + Gemini 3.1 Pro via `google-genai` |
| Database | PostgreSQL 17 |
| Search | Elasticsearch 8.17 |
| Graph | Neo4j 5 Community |
| MCP | FastMCP (stdio + streamable HTTP) |
| SDKs | Python (httpx + Pydantic) |
| CLI | click + rich + httpx |
| Testing | pytest (142 tests), Vitest |
| Linting | ruff (Python), ESLint + Prettier (TypeScript) |

---

## Documentation

| Document | What it covers |
|---|---|
| [PROJECT.md](PROJECT.md) | Project vision, domain model, roadmap — the canonical spec |
| [CLAUDE.md](CLAUDE.md) | Operational guide for Claude Code — coding conventions, architecture rules |
| [development/](development/) | Technical docs — architecture, API reference, evaluation engine, MCP, integrations, testing |
| [docs/](docs/) | mkdocs site — getting started, architecture, SDK usage, integration guides |

---

## Contributing

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`
- Run `ruff check`, `ruff format`, `pnpm lint`, `pnpm typecheck` before pushing
- Tests for LLM features must mock Gemini
- Read `CLAUDE.md` for the full operational contract

---

## License

See [LICENSE](./LICENSE).

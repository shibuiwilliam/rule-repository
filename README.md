# Rule Repository

A platform for managing, searching, and enforcing natural-language rules using LLMs and AI agents.

Traditional rule engines force you to translate human rules into formal logic — losing nuance along the way. The Rule Repository keeps rules as written and uses Gemini to interpret, search, enforce, and improve them at runtime.

Whether the rules come from legal regulations, HR policies, engineering standards, or coding conventions, this system stores them in their original natural-language form, makes them searchable across five modalities, evaluates code changes against them, and delivers them to AI coding agents at the moment they matter.

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-started/) and Docker Compose
- A [Gemini API key](https://ai.google.dev/gemini-api/docs)

### Run the full stack

```bash
git clone <repo-url> && cd rule-repository
cp .env.example .env          # add your GEMINI_API_KEY
docker compose up --build     # starts 10 services
```

After about a minute:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | FastAPI with 14 routers |
| Swagger UI | http://localhost:8000/docs | Interactive API explorer |
| Frontend | http://localhost:3000 | Operator console (13 pages) |
| MCP Server | localhost:8001 | AI agent tool integration |
| PostgreSQL | localhost:5432 | System of record |
| Elasticsearch | localhost:9200 | Full-text and vector search |
| Neo4j | localhost:7474 | Rule relationship graph |
| Redis | localhost:6379 | Background job queue |

### Load sample data

The repository includes 16 sample rule documents — 10 coding standards and 6 company policies:

```bash
uv run python scripts/seed_data.py
```

Or drag and drop files from `sample_rules/` onto the Documents page — the frontend supports multi-file upload.

---

## What You Can Do

### Store rules in natural language
Every rule carries modality (MUST / MUST_NOT / SHOULD / MAY / INFO), severity, scope, tags, rationale, governance, source provenance, effective period, and project assignment. Rules are scoped to projects for multi-team organization.

### Evaluate code changes
The **Code-Aware Evaluation Engine** accepts diffs, understands file paths and code structure, returns per-rule verdicts with line-level locations and fix suggestions. It resolves conflicts via Neo4j (OVERRIDES, DEPENDS_ON), checks the LLM cache, and supports environment-based snapshot evaluation.

```
POST /api/v1/evaluate { "diff": "...", "scope": "engineering/python" }
→ Rule #17 DENY at payment.py:45 — "Add Pydantic model for input validation"
→ conflict_resolutions: [{ "Rule #7 overrides Rule #42 (higher severity)" }]
```

### Deliver rules to AI coding agents
The MCP server exposes 6 tools. The key one is `get_rules_for_context` — agents get formatted rules (MUST/SHOULD/MAY) before writing code. Three formats: `instructions`, `checklist`, `detailed`.

### Discover rules from projects
Give it a GitHub URL or drop files — the discovery engine analyzes CLAUDE.md, linter configs, and code patterns to propose candidate rules.

### Upload and extract from documents
Drag and drop multiple files (PDF, markdown, text). Click a document to see its content and the rules extracted from it.

### Learn from corrections
When a human corrects AI-generated code, the system captures the delta, analyzes it (new rule? ambiguous existing rule? scope gap?), and proposes improvements. Approve individually or in bulk.

### Organize by project
Rules belong to **projects**. A project selector filters everything — rules, evaluations, discovery, search. Federation provides org→team→project hierarchy with inheritance and overrides.

### Preview impact before updating
Replay historical evaluations with a modified rule to see how many verdicts would change.

### Enforce everywhere
- **GitHub PR Review** — webhook posts structured review comments
- **CI Pipeline** — `rulerepo-check` exits 0/1/2 with `--format github-actions`
- **Agent Hooks** — `rulerepo-hook preflight` / `posthoc`
- **Gateway** — webhook-driven enforcement with action dispatch
- **Alerts** — background workers detect problems

### Test rules safely
**Playground** provides sandbox evaluation and per-rule test cases (manual, auto-generated, Gemini-generated).

### Monitor and improve
Intelligence dashboard: health scoring (6 dimensions), cache hit rate, top violated rules, automated recommendations. Correction trends show the feedback flywheel in action.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Rule Management Server                          │
│                                                                        │
│  Extraction   Search(5)   Evaluation    Intelligence   Discovery      │
│  Pipeline     BM25+Vec    Engine        Health+Recs    + Import       │
│  (multi-file) +DocSearch  (conflict-    Cache Stats                    │
│                            aware)       Violations     Federation      │
│                                         Feedback Loop  Snapshots       │
│                                         + PR Capture   Alerts          │
│                            Projects     Impact Preview  Playground     │
│                                                                        │
│  PostgreSQL    Elasticsearch   Neo4j       Redis       Audit Log       │
│  (truth)       (search)        (graph)     (jobs)      (immutable)    │
│                                                                        │
│  14 routers  |  MCP Server  |  Gateway  |  GitHub Integration         │
└──────────────┼──────────────┼───────────┼─────────────────────────────┘
               │              │           │
    Rule    Agentic    MCP     CLI     GitHub    Gateway   arq-worker
    SDK      SDK      Server  Tools    App      (webhooks)  (cron)
```

**Three data stores, one source of truth.** PostgreSQL holds canonical data. Elasticsearch is a derived search index. Neo4j is a derived relationship graph. If they disagree, Postgres wins. Recovery: `scripts/reindex_elasticsearch.py` and `scripts/reconcile_graph.py`.

---

## Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                      # FastAPI backend (148 Python modules)
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/              # 14 routers
│   │   │   ├── services/            # 11 service areas
│   │   │   │   ├── evaluation/      #   diff parser, graph resolver, conflict aggregator, impact preview
│   │   │   │   ├── discovery/       #   GitHub importer, analyzers, pattern detector
│   │   │   │   ├── feedback/        #   correction capture (manual + auto PR), analyzer
│   │   │   │   ├── intelligence/    #   health scorer, analytics, recommender
│   │   │   │   ├── extraction/      #   document ingestion (Gemini)
│   │   │   │   ├── context_delivery/#   rule formatting for agents
│   │   │   │   ├── federation/      #   hierarchy resolver
│   │   │   │   ├── playground/      #   sandbox eval + test cases
│   │   │   │   └── snapshots/       #   versioned rule sets + deployment
│   │   │   ├── mcp/                 # 6 tools, 2 resources, 3 prompts
│   │   │   ├── gateway/             # normalizers, policy engine
│   │   │   ├── integrations/        # GitHub webhook, CI formatters
│   │   │   └── workers/             # arq background jobs
│   │   └── alembic/                 # 12 migrations
│   └── frontend/                    # Next.js 15, TypeScript, Tailwind CSS
│       └── app/(dashboard)/         # 13 pages
├── packages/
│   ├── rule-client/                 # Python SDK (async, typed)
│   ├── agentic-client/              # Evaluation SDK
│   └── cli/                         # rulerepo-check, rulerepo-hook, rulerepo-ingest
├── sample_rules/
│   ├── coding_rules/                # 10 engineering standard documents
│   └── company_rules/               # 6 corporate policy documents
├── scripts/                         # seed_data, reconcile_graph, reindex_elasticsearch, generate_claude_md
├── development/                     # 13 technical docs
├── docs/                            # mkdocs site (34 pages)
├── docker-compose.yml               # 10 services
├── Makefile                         # 50+ targets
├── PROJECT.md                       # Vision, domain model, roadmap
└── CLAUDE.md                        # Operational guide for Claude Code
```

---

## API (14 routers)

Swagger UI: [localhost:8000/docs](http://localhost:8000/docs)

| Router | Key Endpoints |
|---|---|
| **rules** | CRUD (with project_id scoping), retire, revisions, relationships, graph |
| **evaluate** | POST /evaluate, /evaluate/quick, /evaluate/applicable-rules |
| **search** | fulltext, vector, hybrid, documents, by-source-document |
| **intent** | Natural language query classification |
| **intelligence** | dashboard, health, analytics, recommendations |
| **discovery** | scan, GitHub import, candidates, approve/dismiss |
| **feedback** | corrections (manual + auto), approve/dismiss/bulk, stats |
| **extraction** | multi-file upload, extract, list documents, document detail + content |
| **federation** | hierarchy CRUD, effective rules, inheritance |
| **snapshots** | create, deploy, rollback, simulate |
| **playground** | sandbox eval, test cases, test runner, generator |
| **alerts** | list, acknowledge, resolve |
| **projects** | CRUD, list rules by project |
| **relationships** | create/delete rule graph edges |

Health: `/healthz` (liveness), `/readyz` (PG + ES + Neo4j).

---

## SDKs & CLI

```python
from rulerepo import RuleClient
async with RuleClient("http://localhost:8000") as client:
    results = await client.search.hybrid("overtime limit")
    rule = await client.rules.create("All PRs must be reviewed", modality="MUST")

from rulerepo_agentic import AgenticRuleClient
async with AgenticRuleClient("http://localhost:8000", scope="engineering") as client:
    result = await client.evaluate(context={...}, intent="Add endpoint", diff="...")
```

```bash
rulerepo-check --diff "$(git diff main...HEAD)" --format github-actions
rulerepo-hook preflight --file src/api/handler.py
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering
```

---

## MCP Server

| Tool | Purpose |
|---|---|
| `get_rules_for_context` | Formatted rules for current file/task |
| `evaluate_compliance` | Check a diff against rules |
| `search_rules` | Natural language search |
| `explain_rule` | Rationale, provenance, relationships |
| `find_conflicts` | Detect contradicting rules |
| `discover_rules` | Analyze codebase for implicit rules |

Resources: `rule://{id}`, `ruleset://{scope}`. Transports: stdio + streamable HTTP.

---

## Development

```bash
make help                 # 50+ targets
make up                   # start stack
make dev.server           # backend hot-reload
make dev.frontend         # frontend hot-reload
make test                 # all tests
make test.e2e             # E2E with real Gemini (starts stack)
make lint                 # ruff + mypy + eslint + tsc
make check                # format + lint + test
```

---

## Documentation

| Location | Content |
|---|---|
| [PROJECT.md](PROJECT.md) | Vision, domain model, 5-phase roadmap |
| [CLAUDE.md](CLAUDE.md) | Operational guide for Claude Code |
| [development/](development/) | 13 technical docs |
| [docs/](docs/) | mkdocs site (34 pages) |
| [Swagger UI](http://localhost:8000/docs) | Interactive API docs |

---

## Contributing

1. Read [CLAUDE.md](CLAUDE.md)
2. Branch from `main`, use Conventional Commits
3. Run `make check` before pushing
4. Mock Gemini in tests (gate live tests with `RULEREPO_LIVE_LLM=1`)

---

## License

See [LICENSE](./LICENSE).

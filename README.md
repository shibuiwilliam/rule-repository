# Rule Repository

A platform for managing, searching, and enforcing natural-language rules using LLMs and AI agents.

Traditional rule engines force you to translate human rules into formal logic — losing nuance along the way. The Rule Repository keeps rules as written and uses Gemini to interpret, search, enforce, and improve them at runtime. Built for software teams that use AI coding agents.

---

## Quick Start

```bash
git clone <repo-url> && cd rule-repository
cp .env.example .env          # add your GEMINI_API_KEY
docker compose up --build     # starts 10 services
uv run python scripts/seed_data.py  # load sample rules
```

| Service | URL | What it does |
|---|---|---|
| Backend API | http://localhost:8000 | 13 API routers (rules, evaluate, search, intent, intelligence, discovery, feedback, federation, alerts, snapshots, playground, extraction, relationships) |
| Swagger UI | http://localhost:8000/docs | Interactive API docs — try every endpoint |
| Frontend | http://localhost:3000 | 11-page operator console |
| MCP Server | localhost:8001 | AI agent tool integration (Model Context Protocol) |
| PostgreSQL | localhost:5432 | System of record |
| Elasticsearch | localhost:9200 | Full-text + vector search |
| Neo4j | localhost:7474 | Rule relationship graph |
| Redis | localhost:6379 | Background job queue |

---

## What It Does

### Store rules in natural language
Every rule has modality (MUST / MUST_NOT / SHOULD / MAY / INFO), severity, scope, tags, rationale, governance, source provenance, and effective period. The statement is always the source of truth.

### Evaluate code changes against rules
The **Code-Aware Evaluation Engine** accepts diffs, understands file paths and code structure, and returns per-rule verdicts with line-level locations and fix suggestions. It consults Neo4j for conflict resolution (OVERRIDES, DEPENDS_ON), checks the LLM cache before calling Gemini, enforces effective periods, and supports environment-based snapshot evaluation.

```
POST /api/v1/evaluate { "diff": "...", "scope": "engineering/python", "environment": "staging" }
→ Rule #17 DENY at payment.py:45 — "Add Pydantic model for input validation"
→ conflict_resolutions: [{ "Rule #7 overrides Rule #42 (higher severity)" }]
```

### Deliver rules to coding agents
The MCP server's key tool is `get_rules_for_context` — agents call it with file paths and get formatted rules (MUST/SHOULD/MAY) before writing code. Three formats: `instructions`, `checklist`, `detailed`.

### Discover rules from code
**One-click GitHub import**: give it a repo URL → fetches CLAUDE.md, linter configs, code patterns → proposes 30-50 candidate rules. Also scans local files.

### Learn from corrections
**Automatic PR capture**: when a merged PR differs from what was evaluated, the delta is auto-captured as a correction. Corrections suggest new rules or improvements.

### Preview impact before updating rules
Replay historical evaluations with a modified rule to see how many verdicts would change and which repos are affected.

### Organize rules hierarchically
**Federation**: org → team → project with inheritance and overrides. **Snapshots**: versioned, deployable rule sets tied to environments (staging, production).

### Enforce everywhere
- **GitHub PR Review** — structured review comments with per-rule verdicts
- **CI Pipeline** — `rulerepo-check` exits 0/1/2, supports `--format github-actions`
- **Agent Hooks** — `rulerepo-hook preflight` / `posthoc` for Claude Code
- **Gateway** — webhook-driven enforcement with action dispatch on DENY
- **Alerts** — configurable alert rules that fire when conditions are met

### Monitor and improve
Intelligence dashboard: health scoring (6 dimensions), cache hit rate, top violated rules, automated recommendations. **Playground** for testing evaluations interactively.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Rule Management Server                          │
│                                                                       │
│  Extraction  Search(5)  Evaluation    Intelligence  Discovery        │
│  Pipeline    BM25+Vec   Engine        Health+Recs   + GitHub Import  │
│                         (conflict-    Cache Stats                     │
│                          aware)       Violations    Federation        │
│                                       Feedback Loop Snapshots         │
│                                       + PR Capture  Alerts            │
│                                       Impact Preview Playground       │
│                                                                       │
│  PostgreSQL   Elasticsearch   Neo4j       Redis     Audit Log        │
│  (truth)      (search)        (graph)     (jobs)    (immutable)      │
│                                                                       │
│  13 routers │ MCP Server │ Gateway │ GitHub Integration              │
└─────────────┼────────────┼─────────┼────────────────────────────────┘
              │            │         │
   Rule  Agentic  MCP    CLI    GitHub   Gateway  arq-worker
   SDK    SDK    Server  Tools   App    (webhooks) (cron)
```

**Data stores**: PostgreSQL (truth), Elasticsearch (search), Neo4j (graph). Postgres always wins on disagreement.

---

## Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                      # FastAPI backend (144 Python modules)
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/              # 13 routers
│   │   │   ├── services/
│   │   │   │   ├── evaluation/      # 10 modules: diff parser, rule selector, graph resolver,
│   │   │   │   │                    #   conflict aggregator, LLM judge (cached), impact preview
│   │   │   │   ├── discovery/       # github_importer, analyzers, pattern detector
│   │   │   │   ├── feedback/        # correction capture (manual + auto PR), analyzer
│   │   │   │   ├── federation/      # hierarchy resolver with overrides
│   │   │   │   ├── intelligence/    # health scorer, analytics (cache + violations), recommender
│   │   │   │   ├── extraction/      # document ingestion (Gemini)
│   │   │   │   └── context_delivery/# rule formatting for agents
│   │   │   ├── mcp/                 # 5 tools, 2 resources, 3 prompts
│   │   │   ├── gateway/             # normalizers, policy engine, action dispatch
│   │   │   ├── integrations/        # GitHub webhook, check reporter, CI formatters
│   │   │   └── workers/             # arq background jobs (settings.py, tasks.py)
│   │   └── alembic/                 # 10 migrations
│   └── frontend/                    # Next.js 15, TypeScript, Tailwind 4, React Flow
│       └── app/(dashboard)/         # 11 pages
├── packages/
│   ├── rule-client/                 # Python SDK (async, typed)
│   ├── agentic-client/              # Evaluation client
│   └── cli/                         # rulerepo-check, rulerepo-hook, rulerepo-ingest
├── scripts/                         # seed_data, reconcile_graph, generate_claude_md
├── development/                     # 7 technical docs
├── docs/                            # mkdocs site
└── docker-compose.yml               # 10 services, 4 volumes
```

---

## API (13 routers)

Swagger UI: [localhost:8000/docs](http://localhost:8000/docs)

| Router | Key Endpoints |
|---|---|
| **rules** | CRUD, retire, revisions, relationships, graph |
| **evaluate** | POST /evaluate, /evaluate/quick, /evaluate/applicable-rules (supports `environment`) |
| **search** | fulltext, vector, hybrid, category, context |
| **intent** | Natural language query → classify → route |
| **intelligence** | dashboard (health, cache, top violations), analytics, recommendations |
| **discovery** | scan, GitHub import, candidates, approve/dismiss |
| **feedback** | corrections (manual + auto-captured), approve/dismiss, stats |
| **federation** | hierarchy CRUD, effective rules, inheritance |
| **snapshots** | versioned rule sets, deploy to environments |
| **alerts** | configurable alert rules |
| **playground** | interactive evaluation testing |
| **extraction** | document upload, extract, review candidates |
| **relationships** | create/delete rule relationships |

Health: `/healthz` (liveness), `/readyz` (PG + ES + Neo4j).

---

## SDKs & CLI

```python
# Rule Client
from rulerepo import RuleClient
async with RuleClient("http://localhost:8000") as client:
    results = await client.search.hybrid("overtime limit")
    rule = await client.rules.create("All PRs must be reviewed", modality="MUST")

# Agentic Client
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

| Tool | What it does |
|---|---|
| `get_rules_for_context` | Formatted rules for current file/task — the key tool |
| `evaluate_compliance` | Check a diff against rules, get verdicts + fixes |
| `search_rules` | Natural language search |
| `explain_rule` | Rationale, provenance, relationships |
| `find_conflicts` | Conflicting rules for a given rule or statement |

Resources: `rule://{id}`, `ruleset://{scope}`. Transports: stdio (Claude Code) + streamable HTTP.

---

## Design Decisions

| Decision | Rationale |
|---|---|
| Rules never deleted | Retired via `valid_until`. Past evaluations stay explainable. |
| Postgres is truth | ES + Neo4j derived. `reconcile_graph.py` rebuilds. |
| Audit log append-only | PG trigger blocks UPDATE/DELETE. Hash-chained. |
| Temperature always 1.0 | Lower degrades Gemini 3 reasoning. |
| LLM calls cached | Checked before every Gemini call. |
| Evaluation tiered | Flash for LOW/MEDIUM, Pro for CRITICAL. |
| Conflict-aware | Neo4j graph consulted for OVERRIDES/DEPENDS_ON. |
| Effective period enforced | Expired rules excluded from evaluation. |
| Environment-aware | Snapshot-based evaluation per deployment environment. |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy async, Alembic (10 migrations) |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS 4, React Flow |
| LLM | Gemini 3 Flash + Gemini 3.1 Pro via `google-genai` |
| Data | PostgreSQL 17, Elasticsearch 8.17, Neo4j 5, Redis 7 |
| MCP | FastMCP (mcp >= 1.9) |
| CLI | click + rich + httpx |
| Jobs | arq (async, Redis-backed) |
| Linting | ruff (Python), ESLint + Prettier (TypeScript) |

---

## Development

```bash
make dev.server          # backend hot-reload (:8000)
make dev.frontend        # frontend hot-reload (:3000)
make test                # all tests
make lint                # ruff + mypy + eslint + tsc
make check               # format + lint + test
docker compose up --build  # full stack
```

---

## Documentation

| Location | Content |
|---|---|
| [PROJECT.md](PROJECT.md) | Vision, domain model, roadmap |
| [CLAUDE.md](CLAUDE.md) | Operational contract for Claude Code |
| [development/](development/) | Architecture, API ref, evaluation engine, MCP, integrations, testing |
| [docs/](docs/) | mkdocs site — getting started, SDK guides, integration walkthroughs |

---

## Contributing

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`
- Run `make check` before pushing
- Mock Gemini in tests — never call real API in CI
- Read [CLAUDE.md](CLAUDE.md)

---

## License

See [LICENSE](./LICENSE).

# Rule Repository

A platform for managing, searching, and enforcing natural-language rules using LLMs and AI agents.

Traditional rule engines force you to translate human rules into formal logic — losing nuance along the way. The Rule Repository keeps rules as written and uses Gemini to interpret, search, enforce, and improve them at runtime.

Whether the rules come from legal regulations, HR policies, engineering standards, or coding conventions, this system stores them in their original natural-language form, makes them searchable across five modalities, evaluates code changes against them in batches, delivers them to AI coding agents at the moment they matter, and **learns from every human correction** to create better rules over time.

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-started/) and Docker Compose
- A [Gemini API key](https://ai.google.dev/gemini-api/docs)

### Run the full stack

```bash
git clone https://github.com/shibuiwilliam/rule-repository.git && cd rule-repository
cp .env.example .env          # add your GEMINI_API_KEY
make up                       # or: docker compose up --build -d
```

After about a minute:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | FastAPI with 14 API routers |
| Swagger UI | http://localhost:8000/docs | Interactive API explorer |
| Frontend | http://localhost:3000 | Compliance dashboard + 15 operator pages |
| MCP Server | localhost:8001 | AI agent tool integration |
| PostgreSQL | localhost:5432 | System of record (24 ORM models, 16 migrations) |
| Elasticsearch | localhost:9200 | Full-text and vector search |
| Neo4j | localhost:7474 | Rule relationship graph |
| Redis | localhost:6379 | Background job queue |

### Load sample data

The repository includes 23 sample rule documents — 11 coding standards, 7 company policies, and 5 sales team rules:

```bash
make seed
```

Or drag and drop files from `sample_rules/` onto the Documents page at http://localhost:3000/documents.

---

## What You Can Do

### See if your rules are working — at a glance

The **home dashboard** answers the question every team asks: *"Is compliance improving?"*

- **Compliance rate** — big number with color coding (green/yellow/red) + 7-day trend
- **Rules by status** — stacked bar showing DRAFT/APPROVED/EFFECTIVE/RETIRED distribution
- **Pending actions** — rules awaiting review, corrections to approve, active alerts
- **Top violated rules** — the 5 rules agents break most often
- **Recent corrections** — latest human fixes that feed the learning flywheel

### Organize by project

Rules belong to **projects** — a top-level organizational boundary like "Web Coding Rules" or "HR Policy Rules". A project selector in the sidebar scopes everything: rules, documents, evaluations, discovery, search. Switch projects to see a completely different rule set.

### Store rules in natural language

Every rule carries modality (MUST / MUST_NOT / SHOULD / MAY / INFO), severity, scope, tags, rationale, governance, source provenance, effective period, and a maturity level (experimental, stable, proven). The statement is always the source of truth.

### Evaluate code changes — in batches

The **Code-Aware Evaluation Engine** accepts diffs, understands file paths and code structure, and returns per-rule verdicts. The **batched evaluator** sends all selected rules to Gemini in a single API call (5-20x fewer calls, better verdicts, lower latency), with automatic fallback to per-rule evaluation if the batch fails.

```
POST /api/v1/evaluate
{
  "diff": "...",
  "scope": ["engineering/python"]
}

Response:
  overall_verdict: DENY
  rules_evaluated: 12
  rule_verdicts: [
    { rule_id: "...", verdict: "DENY", fix_suggestion: "..." },
    ...
  ]
```

Features: line-level locations, fix suggestions, structured remediations, conflict resolution via Neo4j graph (OVERRIDES, DEPENDS_ON), environment-based snapshot evaluation.

### Deliver rules to AI coding agents

The MCP server exposes six tools. The key one is `get_rules_for_context` — agents get formatted rules (MUST/SHOULD/MAY) before writing code. Works via stdio (Claude Code) or streamable HTTP (remote agents).

### Discover rules from existing projects

Drop files or give a GitHub URL — the discovery engine analyzes CLAUDE.md, linter configs, policy documents, and code patterns to propose candidate rules. Review and approve individually or in bulk.

### Upload and extract from documents

Drag and drop multiple files (PDF, markdown, text) onto the Documents page. The extraction pipeline runs the LLM to propose candidate rules from each document. Bulk extraction runs across all selected documents in sequence.

### Learn from corrections (self-improving flywheel)

When humans correct AI-generated code, the system captures the delta and analyzes it. A background worker clusters similar corrections and auto-drafts rule proposals via Gemini. Approved proposals create rules that start in shadow mode and graduate as they prove accurate. Every correction teaches the system.

### Search five ways — with project filtering

Hybrid (BM25 + vector), full-text, semantic, document search, and by-source. The search page has its own **project dropdown** — choose a specific project to narrow results or select **"All Projects"** to search across everything, independent of the sidebar project selector.

### Organize rules hierarchically

**Federation** provides org-team-project hierarchy with inheritance and overrides. **Snapshots** capture versioned, deployable rule sets tied to environments (production, staging, development).

### Test rules safely

The **Playground** supports two input modes — **Code** (diffs/snippets) and **Scenario** (narrative + structured facts for policy rules). Pick registered rules to test, or write rules manually. The **Suggest by LLM** button generates realistic test inputs (violating or compliant). Per-rule test cases with auto-generation via Gemini.

### Enforce everywhere

- **GitHub PR Review** — webhook posts structured review comments
- **CI Pipeline** — `rulerepo-check` exits 0/1/2 with `--format github-actions`
- **Agent Hooks** — `rulerepo-hook preflight` / `posthoc`
- **Gateway** — webhook-driven enforcement with action dispatch
- **Alerts** — background workers detect dormant rules, high deny rates, health decline

### Monitor and improve

Intelligence dashboard: health scoring (6 dimensions), evaluation analytics, cache hit rate, top violated rules, automated recommendations, correction trends.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Rule Management Server                        │
│                                                                     │
│  Extraction   Search(5)   Evaluation    Intelligence   Discovery   │
│  Pipeline     BM25+Vec    Engine        Health+Recs    + Import    │
│  (bulk)       +DocSearch  (batched +    Analytics       Federation │
│               +Project    conflict-     Flywheel        Snapshots  │
│               filter      aware)        Feedback Loop   Alerts     │
│                                         Dashboard       Playground │
│                                                                     │
│  PostgreSQL    Elasticsearch   Neo4j       Redis       Audit Log   │
│  (truth)       (search)        (graph)     (jobs)      (immutable) │
│                                                                     │
│  14 routers  |  MCP Server  |  Gateway  |  GitHub Integration      │
└──────────────┼──────────────┼───────────┼──────────────────────────┘
               │              │           │
    Rule    Agentic    MCP     CLI     GitHub    Gateway   arq-worker
    SDK      SDK      Server  Tools    App      (webhooks)  (5 cron)
```

**Three data stores, one source of truth.** PostgreSQL holds canonical data. Elasticsearch is a derived search index. Neo4j is a derived relationship graph. If they disagree, Postgres wins. Recovery: `scripts/reindex_elasticsearch.py` and `scripts/reconcile_graph.py`.

---

## Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                      # FastAPI backend — 150 Python modules
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/              # 14 routers (rules, search, evaluate, projects, ...)
│   │   │   ├── services/            # 11 service areas
│   │   │   │   ├── evaluation/      #   batch evaluator, diff parser, rule selector,
│   │   │   │   │                    #   graph resolver, conflict aggregator, LLM judge
│   │   │   │   ├── discovery/       #   GitHub importer, analyzers, pattern detector
│   │   │   │   ├── feedback/        #   correction capture, analyzer, auto-drafter
│   │   │   │   ├── intelligence/    #   health scorer, analytics, recommender
│   │   │   │   ├── extraction/      #   document ingestion (Gemini)
│   │   │   │   ├── context_delivery/#   rule formatting for agents
│   │   │   │   ├── federation/      #   hierarchy resolver with overrides
│   │   │   │   ├── playground/      #   sandbox eval + test cases + suggest-by-LLM
│   │   │   │   └── snapshots/       #   versioned rule sets + deployment
│   │   │   ├── mcp/                 # 6 tools, resources, prompts
│   │   │   ├── gateway/             # normalizers, policy engine
│   │   │   ├── integrations/        # GitHub webhook, CI formatters
│   │   │   └── workers/             # 5 background cron jobs
│   │   ├── alembic/                 # 16 database migrations, 24 ORM models
│   │   └── tests/                   # 20 test files (unit, integration, e2e)
│   └── frontend/                    # Next.js 15, React 19, TypeScript, Tailwind CSS
│       └── app/(dashboard)/         # 15 pages + 6 shared components
├── packages/
│   ├── rule-client/                 # Python SDK (async, typed)
│   ├── agentic-client/              # Evaluation SDK
│   └── cli/                         # rulerepo-check, rulerepo-hook, rulerepo-ingest
├── sample_rules/
│   ├── coding_rules/                # 11 engineering standard documents
│   ├── company_rules/               # 7 corporate policy documents
│   └── sales_team_rules/            # 5 sales team documents
├── scripts/                         # seed_data, reconcile_graph, reindex_elasticsearch,
│                                    #   generate_claude_md
├── infra/                           # Dockerfiles, init SQL, ES templates, Neo4j constraints
├── development/                     # 15 technical docs
├── docs/                            # mkdocs site — 43 pages across 9 sections
├── docker-compose.yml               # 11 services
├── Makefile                         # 63 targets for dev workflow
├── .pre-commit-config.yaml          # ruff, mypy, trailing-whitespace, etc.
├── PROJECT.md                       # Vision, domain model, 5-phase roadmap
└── CLAUDE.md                        # Operational guide for Claude Code
```

---

## API Reference

Swagger UI at [localhost:8000/docs](http://localhost:8000/docs). Overview:

| Router | Key Endpoints |
|---|---|
| **projects** | CRUD for organizational units |
| **rules** | CRUD, retire, revisions, relationships, graph |
| **evaluate** | `/evaluate` (full), `/evaluate/quick`, `/evaluate/applicable-rules` |
| **search** | fulltext, vector, hybrid, category, context, documents, by-source — all with `project_id` filtering |
| **intent** | Natural language query routing |
| **intelligence** | summary (home dashboard), health scores, analytics, recommendations |
| **discovery** | scan, GitHub import, candidates, approve/dismiss |
| **feedback** | corrections, approve/dismiss, stats, proposals (flywheel) |
| **extraction** | upload (multi-file + bulk extract), extract, review candidates |
| **federation** | hierarchy CRUD, add/remove rules, effective rules, diff |
| **snapshots** | versioned rule sets, deploy to environments, rollback, simulate |
| **playground** | sandbox eval (code + scenario), test cases, test runner, suggest-by-LLM |
| **alerts** | list, acknowledge, resolve |
| **relationships** | create, delete rule relationships |
| **gateway** | webhook ingestion, policy CRUD |

Health: `/healthz` (liveness), `/readyz` (PostgreSQL + Elasticsearch + Neo4j).

---

## Background Workers

Five cron jobs run via arq + Redis:

| Job | Schedule | Purpose |
|---|---|---|
| `compute_health_scores` | 2am daily | Score all rules across 6 health dimensions, generate alerts |
| `generate_recommendations` | 3am daily | Auto-suggest improvements (retire, clarify, escalate) |
| `auto_promote_rules` | 4am daily | Graduate/demote rules based on maturity criteria |
| `cluster_corrections` | 5am daily | Cluster corrections, draft rule proposals via Gemini |
| `compute_correction_stats` | Every hour | Aggregate correction feedback metrics |

---

## SDKs and CLI

### Python SDK

```python
from rulerepo import RuleClient

async with RuleClient("http://localhost:8000") as client:
    results = await client.search.hybrid("overtime limit", scope="hr/attendance")
    rule = await client.rules.create(
        "All PRs must be reviewed before merge",
        modality="MUST",
        severity="HIGH",
        scope=["engineering"],
    )
```

### Agentic Client

```python
from rulerepo_agentic import AgenticRuleClient

async with AgenticRuleClient("http://localhost:8000") as client:
    result = await client.evaluate(
        context={"employee_id": "E001", "overtime_hours": 50},
        intent="register_overtime",
        mode="preflight",
    )
```

### CLI Tools

```bash
rulerepo-check --diff "$(git diff main...HEAD)" --format github-actions
rulerepo-hook preflight --file src/api/handler.py
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python
```

---

## MCP Server

| Tool | Purpose |
|---|---|
| `get_rules_for_context` | Formatted rules for the current file/task (the key tool) |
| `evaluate_compliance` | Check a diff against rules — returns verdicts |
| `search_rules` | Natural language search |
| `explain_rule` | Rationale, provenance, relationships |
| `find_conflicts` | Detect contradicting rules |
| `discover_rules` | Analyze a codebase for implicit rules |

Resources: `rule://{id}`, `ruleset://{scope}`. Transports: stdio (Claude Code) + streamable HTTP.

---

## Sample Rules

Three sets of professionally written rule documents ready for import:

| Collection | Documents | Topics |
|---|---|---|
| **Coding Rules** | 11 | Python style, API design, database, auth, testing, error handling, git, security, performance, deployment, documentation |
| **Company Policies** | 7 | Code of conduct, info security, dev standards, remote work, expense/travel, client engagement, data governance |
| **Sales Team Rules** | 5 | Sales process/pipeline, customer engagement, compensation/commission, partner/channel sales, contract/legal compliance |

Import via CLI, the Documents page upload, or the seed script.

---

## Development

```bash
make help                 # show all 63 available targets

# Docker Compose
make up                   # docker compose up --build -d
make down                 # stop everything
make reset                # wipe volumes and rebuild

# Local development
make dev.server           # FastAPI with hot-reload on :8000
make dev.frontend         # Next.js with hot-reload on :3000

# Pre-commit
make precommit.install    # install git hooks (ruff, mypy, trailing-whitespace, etc.)
make precommit.run        # run all hooks on all files
make precommit.update     # update hook versions

# Testing
make test                 # run all tests
make test.unit            # backend unit tests only
make test.e2e             # end-to-end tests (starts stack, uses real Gemini)

# Quality
make check                # format + lint + test (run before committing)
```

### Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS |
| LLM | Gemini 3 Flash + Gemini 3.1 Pro via `google-genai` |
| Data | PostgreSQL 17, Elasticsearch 8.17, Neo4j 5, Redis 7 |
| MCP | FastMCP (mcp >= 1.9) |
| Jobs | arq (async Redis queue, 5 cron jobs) |
| Quality | ruff + mypy (Python), ESLint + Prettier (TypeScript), pre-commit hooks |

---

## Documentation

| Location | What's there |
|---|---|
| [PROJECT.md](PROJECT.md) | Vision, domain model, 5-phase roadmap (Phases 1-4 complete, Phase 5 in progress) |
| [CLAUDE.md](CLAUDE.md) | Operational guide for Claude Code — coding conventions, Gemini rules, Phase 5 implementation guidance |
| [development/](development/) | 15 technical docs — architecture, API reference, evaluation engine, database schema, phase 5 improvements, etc. |
| [docs/](docs/) | mkdocs site — 43 pages across getting started, architecture, API, SDKs, integrations, intelligence |
| [Swagger UI](http://localhost:8000/docs) | Interactive API documentation (when stack is running) |

---

## Contributing

1. Read [CLAUDE.md](CLAUDE.md) — it's the operational contract
2. Run `make precommit.install` to set up git hooks
3. Branch from `main`, use Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`
4. Run `make check` before pushing
5. Mock Gemini in tests — never call the real API in CI

---

## License

See [LICENSE](./LICENSE).

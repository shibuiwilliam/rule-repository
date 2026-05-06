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
| Backend API | http://localhost:8000 | FastAPI with 18 API routers |
| Swagger UI | http://localhost:8000/docs | Interactive API explorer |
| Frontend | http://localhost:3000 | Compliance dashboard + 23 operator pages |
| MCP Server | localhost:8001 | AI agent tool integration (12 tools) |
| PostgreSQL | localhost:5432 | System of record (35 models, 22 migrations) |
| Elasticsearch | localhost:9200 | Full-text and vector search |
| Neo4j | localhost:7474 | Rule relationship graph |
| Redis | localhost:6379 | Background job queue (6 cron jobs) |

### Load sample data

The repository includes 23 sample rule documents and 5 rule templates (57 pre-built rules):

```bash
make seed
```

Or drag and drop files from `sample_rules/` onto the Documents page, or import a template:

```bash
curl -X POST http://localhost:8000/api/v1/rules/import \
  -H "Content-Type: application/json" \
  -d @sample_rules/templates/python-fastapi.yaml
```

---

## What You Can Do

### See if your rules are working — at a glance

The **home dashboard** answers: *"Is compliance improving?"*

- **Compliance rate** with color coding (green/yellow/red) + 7-day trend
- **Rules by status** — stacked bar (DRAFT/APPROVED/EFFECTIVE/RETIRED)
- **Pending actions** — rules awaiting review, corrections to approve, active alerts
- **Top violated rules** — the 5 rules agents break most often
- **Recent corrections** — latest human fixes feeding the flywheel

### Organize by project

Rules belong to **projects**. A project selector in the sidebar scopes everything: rules, documents, evaluations, discovery, search. Switch projects for a completely different rule set.

### Store rules in natural language

Every rule carries modality (MUST / MUST_NOT / SHOULD / MAY / INFO), severity, scope, tags, rationale, document context, preconditions, exceptions, following examples, violation examples, governance, source provenance, effective period, and maturity level (experimental, stable, proven). The statement is always the source of truth.

### Evaluate code changes — in batches

The **Code-Aware Evaluation Engine** accepts diffs, understands file structure, and returns per-rule verdicts. The **batched evaluator** sends all selected rules to Gemini in a single API call (5-20x fewer calls, better verdicts, lower latency), with automatic fallback to per-rule evaluation.

```
POST /api/v1/evaluate
{ "diff": "...", "scope": ["engineering/python"] }

→ overall_verdict: DENY, rules_evaluated: 12
  rule_verdicts: [{ rule_id, verdict, fix_suggestion, remediations }]
```

Features: line-level locations, structured remediations, conflict resolution via Neo4j graph, environment-based snapshot evaluation, shadow mode for experimental rules.

### Get rules delivered to agents automatically

The **session context API** resolves file paths to scopes and returns formatted rules instantly:

```
GET /api/v1/rules/context?files=src/api/handler.py,tests/test_handler.py
→ 20 rules matched, scopes: [engineering/python, engineering/api, engineering/testing]
```

The MCP server exposes 12 tools for deeper integration, including agent registration, personalized rules, verdict challenges, and proposal management. CLI hooks (`rulerepo-hook preflight/posthoc`) inject rules before file writes and evaluate after.

### Discover rules from existing projects

Drop files or give a GitHub URL — the discovery engine analyzes CLAUDE.md, linter configs, policy documents, and code patterns to propose rules. Review and approve individually or in bulk.

### Upload and extract from documents

Drag and drop multiple files (PDF, markdown, text). The extraction pipeline runs Gemini to propose candidate rules. Bulk extraction across all selected documents. Each extracted rule captures **context** (surrounding document text, section hierarchy, regulatory authority), **preconditions** (when the rule applies), **exceptions** (when it doesn't), and **following/violation examples** (concrete examples of compliant and non-compliant behavior from the source document). All of these are passed to the LLM evaluator for more accurate verdicts.

### Learn from corrections (self-improving flywheel)

When humans correct AI-generated code, the system captures the delta and analyzes it. A background worker clusters similar corrections and auto-drafts rule proposals via Gemini. Approved proposals start in shadow mode and graduate automatically. Every correction teaches the system.

### Search five ways — with project filtering

Hybrid (BM25 + vector), full-text, semantic, document search, and by-source. The search page has its own **project dropdown** with an **"All Projects"** option, independent of the sidebar selector.

### Measure rule effectiveness

The **effectiveness score** answers *"Is this rule actually helping?"*:
- **Precision**: % of DENY verdicts that were correct (not false positives)
- **Prevention rate**: did corrections decrease after this rule was activated?
- **Agent adoption**: % of evaluations that pass on the first attempt

### Get a weekly report

The **weekly digest** runs every Monday and delivers compliance trends, top violations, rules needing attention, and pending actions via webhook (Slack, email, etc.).

### Compare teams

The **team comparison dashboard** shows per-project rule count and compliance rate, sorted by performance.

### Test rules safely

The **Playground** supports **Code** and **Scenario** input modes. Pick registered rules or write them manually. **Suggest by LLM** generates realistic test inputs. Per-rule test cases with auto-generation.

### Enforce everywhere

- **GitHub PR Review** — webhook posts structured review comments
- **CI Pipeline** — `rulerepo-check` exits 0/1/2 with `--format github-actions`
- **Agent Hooks** — `rulerepo-hook preflight` / `posthoc` with `--agent-id`
- **Gateway** — webhook-driven enforcement with action dispatch
- **Alerts** — background workers detect dormant rules, high deny rates, health decline

### Propose rule changes collaboratively

The **Governance Proposals** system brings structured change management to rules. Create proposals (add, modify, retire), assign reviewers, collect multi-approver votes, and track threaded comments with inline suggestions. The system runs automated conflict analysis and impact preview before enactment. 14 API endpoints, a 3-step wizard in the frontend, and a notification inbox keep everyone in the loop.

### Let agents self-govern

**Autonomous Agent Governance** gives each AI agent a profile with trust levels (untrusted, limited, standard, elevated, autonomous). The system delivers personalized rules — suppressing rules the agent has already mastered, weighting rules it historically violates. Agents can challenge verdicts they disagree with and request exceptions with justification. Multi-agent governance sessions let multiple agents share verdicts on the same change.

### Review activities at two speeds

**Activity Review** offers two-tier compliance checking: a **rough review** for fast triage across all rules, and a **detailed review** for deep LLM evaluation of the most relevant rules. Combined endpoint at `/api/v1/evaluate/review`.

### Organize rules hierarchically

**Federation** provides org-team-project hierarchy with inheritance and overrides. **Snapshots** capture versioned, deployable rule sets tied to environments.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Rule Management Server                        │
│                                                                     │
│  Extraction   Search(5)   Evaluation    Intelligence   Discovery   │
│  Pipeline     BM25+Vec    Engine        Health+Recs    + Import    │
│  (bulk +      +Project    (batched +    Effectiveness   Federation │
│   context)    filter      conflict-     Digest+Compare  Snapshots  │
│                           aware +       Flywheel        Alerts     │
│               Templates   remediation   Agent Tracking  Playground │
│                           + review)                                 │
│  Proposals    Agent Gov                                            │
│  (lifecycle,  (trust,                                              │
│   voting,     challenge,                                           │
│   comments)   sessions)                                            │
│                                                                     │
│  PostgreSQL    Elasticsearch   Neo4j       Redis       Audit Log   │
│  (truth)       (search)        (graph)     (jobs)      (immutable) │
│                                                                     │
│  17 routers  |  MCP Server (12 tools)  |  Gateway  |  GitHub App  │
└──────────────┼─────────────────────────┼───────────┼───────────────┘
               │                         │           │
    Rule    Agentic    MCP     CLI     GitHub    Gateway   arq-worker
    SDK      SDK      Server  Tools    App      (webhooks)  (6 cron)
```

**Three data stores, one source of truth.** PostgreSQL holds canonical data. Elasticsearch is a derived search index. Neo4j is a derived relationship graph. If they disagree, Postgres wins.

---

## Repository Layout

```
rule-repository/
├── apps/
│   ├── server/                      # FastAPI backend
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/              # 17 routers (incl. proposals, agent-governance,
│   │   │   │                        #   review)
│   │   │   ├── services/            # 12 service areas (evaluation, discovery,
│   │   │   │                        #   feedback, intelligence, extraction,
│   │   │   │                        #   context_delivery, federation, playground,
│   │   │   │                        #   snapshots, proposals, agent_governance,
│   │   │   │                        #   + top-level search/intent/rule)
│   │   │   ├── mcp/                 # MCP server (12 tools, resources, prompts)
│   │   │   ├── gateway/             # normalizers, policy engine
│   │   │   ├── integrations/        # GitHub webhook, CI formatters
│   │   │   └── workers/             # 6 background cron jobs
│   │   ├── alembic/                 # 22 database migrations, 35 ORM models
│   │   └── tests/                   # 212 passing tests (unit, integration, e2e)
│   └── frontend/                    # Next.js 15, React 19, TypeScript, Tailwind
│       └── app/(dashboard)/         # 22 pages (incl. proposals, agents,
│                                    #   notifications)
├── packages/
│   ├── rule-client/                 # Python SDK (async, typed)
│   ├── agentic-client/              # Evaluation SDK
│   └── cli/                         # rulerepo-check, rulerepo-hook, rulerepo-ingest,
│                                    #   rulerepo-export
├── sample_rules/
│   ├── coding_rules/                # 11 engineering standard documents
│   ├── company_rules/               # 7 corporate policy documents
│   ├── sales_team_rules/            # 5 sales team documents
│   └── templates/                   # 5 YAML templates (57 pre-built rules)
├── scripts/                         # seed_data, reconcile_graph, reindex_elasticsearch,
│                                    #   generate_claude_md
├── infra/                           # Dockerfiles, init SQL, ES templates, Neo4j constraints
├── development/                     # 15 technical docs
├── docs/                            # mkdocs site — 43 pages across 9 sections
├── docker-compose.yml               # 8 services + init containers
├── Makefile                         # 63 targets
├── .pre-commit-config.yaml          # ruff, mypy, trailing-whitespace, etc.
├── PROJECT.md                       # Vision, domain model, 6-phase roadmap
└── CLAUDE.md                        # Operational guide for Claude Code
```

---

## API Reference

Swagger UI at [localhost:8000/docs](http://localhost:8000/docs).

| Router | Key Endpoints |
|---|---|
| **rules** | CRUD, retire, revisions, relationships, graph, `/context` (session), `/import` (bulk) |
| **evaluate** | `/evaluate` (full), `/evaluate/quick`, `/evaluate/applicable-rules`, `/evaluate/review` (two-tier: rough + detailed) |
| **search** | fulltext, vector, hybrid, category, context, documents, by-source — all with project filtering |
| **intelligence** | `/summary`, `/digest`, `/effectiveness/{id}`, `/comparison`, health, analytics, recommendations, `/agents` |
| **discovery** | scan, GitHub import, candidates, approve/dismiss |
| **feedback** | corrections, approve/dismiss, stats, proposals (flywheel) |
| **extraction** | upload (multi-file + bulk extract), extract, review candidates |
| **playground** | sandbox eval (code + scenario), test cases, test runner, suggest-by-LLM |
| **federation** | hierarchy CRUD, add/remove rules, effective rules, diff |
| **snapshots** | versioned rule sets, deploy, rollback, simulate |
| **projects** | CRUD for organizational units |
| **alerts** | list, acknowledge, resolve |
| **relationships** | create, delete rule relationships |
| **proposals** | create, vote, comment (with suggestions), enact, conflict analysis, impact preview, notifications |
| **agent-governance** | agent profiles, trust levels, personalized rules, verdict challenges, exception requests, governance sessions |
| **gateway** | webhook ingestion, policy CRUD |
| **intent** | Natural language query routing |

Health: `/healthz` (liveness), `/readyz` (all stores).

---

## Background Workers

Six cron jobs via arq + Redis:

| Job | Schedule | Purpose |
|---|---|---|
| `compute_health_scores` | 2am daily | Score rules across 6 health dimensions, generate alerts |
| `generate_recommendations` | 3am daily | Auto-suggest improvements (retire, clarify, escalate) |
| `auto_promote_rules` | 4am daily | Graduate/demote rules based on maturity criteria |
| `cluster_corrections` | 5am daily | Cluster corrections, draft rule proposals via Gemini |
| `compute_correction_stats` | Hourly | Aggregate correction feedback metrics |
| `send_weekly_digest` | Monday 9am | Generate and deliver weekly governance digest |

---

## Rule Templates

Five pre-built rule sets (57 rules total) ready for import:

| Template | Rules | Focus |
|---|---|---|
| `python-fastapi` | 15 | Type hints, Pydantic, async, logging, migrations, CORS |
| `typescript-react` | 12 | Strict mode, hooks, components, state, error boundaries |
| `security-owasp` | 10 | OWASP Top 10: injection, auth, CSRF, rate limiting |
| `api-design` | 10 | Versioning, pagination, error responses, status codes |
| `testing-standards` | 10 | Coverage, isolation, mocking, naming, CI |

---

## SDKs and CLI

### Python SDK

```python
from rulerepo import RuleClient

async with RuleClient("http://localhost:8000") as client:
    results = await client.search.hybrid("overtime limit", scope="hr/attendance")
```

### Agentic Client

```python
from rulerepo_agentic import AgenticRuleClient

async with AgenticRuleClient("http://localhost:8000") as client:
    result = await client.evaluate(
        context={"employee_id": "E001", "overtime_hours": 50},
        intent="register_overtime", mode="preflight",
    )
```

### CLI Tools

```bash
rulerepo-check --diff "$(git diff main...HEAD)" --format github-actions
rulerepo-hook preflight --file src/api/handler.py --agent-id claude-code
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python
rulerepo-export --project backend-api --output rules.yaml
```

---

## Development

```bash
make help                 # show all 63 targets

make up                   # start full stack
make down                 # stop
make reset                # wipe volumes and rebuild

make dev.server           # FastAPI with hot-reload on :8000
make dev.frontend         # Next.js with hot-reload on :3000

make precommit.install    # install git hooks (ruff, mypy, etc.)
make test                 # run all tests
make check                # format + lint + test (run before committing)
```

### Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS |
| LLM | Gemini 3 Flash + Gemini 3.1 Pro via `google-genai` |
| Data | PostgreSQL 17, Elasticsearch 8.17, Neo4j 5, Redis 7 |
| MCP | FastMCP (mcp >= 1.9), 12 tools |
| Jobs | arq (6 cron jobs) |
| Quality | ruff + mypy, ESLint + Prettier, pre-commit hooks |

---

## Documentation

| Location | Content |
|---|---|
| [PROJECT.md](PROJECT.md) | Vision, domain model, 6-phase roadmap |
| [CLAUDE.md](CLAUDE.md) | Operational guide — conventions, Gemini rules, implementation notes |
| [development/](development/) | 15 technical docs — architecture, API reference, evaluation engine, database schema, etc. |
| [docs/](docs/) | mkdocs site — 43 pages across 9 sections |
| [Swagger UI](http://localhost:8000/docs) | Interactive API docs (when stack is running) |

---

## Contributing

1. Read [CLAUDE.md](CLAUDE.md)
2. Run `make precommit.install`
3. Branch from `main`, use Conventional Commits
4. Run `make check` before pushing
5. Mock Gemini in tests

---

## License

See [LICENSE](./LICENSE).

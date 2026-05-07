# Rule Repository

A platform for managing, searching, and enforcing natural-language rules using LLMs and AI agents.

Traditional rule engines force you to translate human rules into formal logic -- losing nuance along the way. The Rule Repository keeps rules as written and uses LLMs to interpret, search, enforce, and improve them at runtime.

Whether the rules come from **labor regulations, contract standards, expense policies, anti-corruption laws, data privacy mandates, advertising restrictions**, engineering guidelines, or coding conventions, this system stores them in their original natural-language form, makes them searchable across multiple modalities, evaluates actions against them, delivers them to both human operators and AI agents at the moment they matter, and **learns from every correction** to create better rules over time.

---

## What You Can Do

### Enforce HR and labor compliance

Load the `hr-attendance-jp` template (25 rules grounded in the Labor Standards Act) and evaluate overtime registrations, leave requests, and scheduling decisions against statutory limits -- monthly overtime caps, 36-Agreement requirements, mandatory leave usage, maternity protections, and record-keeping obligations.

### Review contracts against your standards

The `contract-nda-standard` template checks NDAs for missing definitions, asymmetric obligations, overbroad residuals clauses, and missing governing-law provisions. Use the contract extraction pipeline to break uploaded contracts into clause-level units for granular review.

### Control expenses and prevent fraud

The `expense-claim-jp` template validates expense submissions against approval thresholds, receipt requirements, entertainment documentation rules, qualified invoice compliance, and anti-splitting controls.

### Prevent bribery and corruption

The `bribery-anti-corruption` template covers FCPA, UK Bribery Act, and JP Unfair Competition Prevention Act -- gift thresholds, facilitation payments, third-party due diligence, government contract reviews, and whistleblowing obligations.

### Protect personal data

The `data-privacy-jp` template enforces APPI requirements: purpose specification, consent management, third-party transfer controls, breach notification obligations, and individual rights (disclosure, correction, deletion, cessation).

### Regulate advertising claims

The `advertising-yakukiho` template catches prohibited pharmaceutical efficacy claims, missing disclaimers, unauthorized health-food claims, and endorsement violations under Japan's Pharmaceutical and Medical Device Act.

### Enforce engineering standards

Seven engineering templates cover Python/FastAPI conventions, TypeScript/React patterns, OWASP security rules, API design standards, testing practices, documentation standards, and NDA review -- evaluated against code diffs in CI pipelines.

### Evaluate code changes -- in batches

The **Code-Aware Evaluation Engine** accepts diffs, understands file structure, and returns per-rule verdicts. The batched evaluator sends all selected rules to Gemini in a single API call (5-20x fewer calls), with automatic fallback to per-rule evaluation.

```
POST /api/v1/evaluate
{ "diff": "...", "scope": ["engineering/python"] }

-> overall_verdict: DENY, rules_evaluated: 12
   rule_verdicts: [{ rule_id, verdict, fix_suggestion, remediations }]
```

### Get rules delivered to AI agents automatically

The **session context API** resolves file paths to scopes and returns formatted rules. The MCP server exposes 12 tools for deeper integration. CLI hooks inject rules before file writes and evaluate after.

### Discover rules from existing documents

Drop files or give a GitHub URL -- the discovery engine analyzes CLAUDE.md, linter configs, policy documents, code patterns, and business sources (Confluence, Notion, e-Gov, EUR-Lex) to propose rules. Upload PDFs (regulations, contracts) and the extraction pipeline proposes candidate rules with article-level source references.

### Learn from corrections (self-improving flywheel)

When humans correct AI-generated output, the system captures the delta, clusters similar corrections, and auto-drafts rule proposals via Gemini. Approved proposals start in shadow mode and graduate automatically. Every correction teaches the system.

### Two-tier activity review

Run a rough triage across all rules to identify which ones are relevant, then follow up with a detailed LLM evaluation that produces per-rule verdicts with fix suggestions. Separates noise from signal.

### Conversational rule tutor

Ask questions about your rules in natural language and get LLM-powered explanations, examples, and guidance through the Tutor page.

---

## Rule Templates

Thirteen pre-built rule sets covering 7 domains:

| Template | Rules | Domain |
|----------|-------|--------|
| `hr-attendance-jp` | 25 | HR / Labor Law (Japan) |
| `contract-nda-standard` | 15 | Legal / Contracts |
| `expense-claim-jp` | 20 | Finance / Expenses (Japan) |
| `bribery-anti-corruption` | 18 | Compliance / Anti-Corruption |
| `data-privacy-jp` | 18 | Compliance / Privacy (Japan) |
| `advertising-yakukiho` | 20 | Compliance / Advertising (Japan) |
| `python-fastapi` | 15 | Engineering / Python |
| `typescript-react` | 12 | Engineering / TypeScript |
| `security-owasp` | 10 | Engineering / Security |
| `api-design` | 10 | Engineering / API Design |
| `testing-standards` | 10 | Engineering / Testing |
| `documentation-standards` | -- | Engineering / Documentation |
| `nda-template` | -- | Legal / NDA Review |

**Important:** All business-domain templates are marked `expert_reviewed: false (reference only)`. They must be reviewed by qualified domain counsel before use for actual regulatory compliance.

---

## Sample Rule Documents

| Directory | Documents | Content |
|-----------|-----------|---------|
| `hr_rules/` | 3 | Work regulations, 36-Agreement template, leave policy |
| `contract_rules/` | 3 | MSA guidelines, NDA review checklist, procurement guidelines |
| `finance_rules/` | 3 | Expense policy, revenue recognition, invoice processing |
| `compliance_rules/` | 3 | Anti-bribery policy, AML guidelines, privacy policy |
| `coding_rules/` | 10 | Python style, API design, testing, security, deployment |
| `company_rules/` | 6 | Code of conduct, infosec, development standards, remote work |
| `sales_team_rules/` | 5 | Sales process, customer engagement, compensation, contracts |
| `legal_rules/` | 1 | Labor standards basics |
| `communication_rules/` | 1 | Messaging policy |

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
make seed                     # load sample rules + all templates
```

After about a minute:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | FastAPI with 18 API routers |
| Swagger UI | http://localhost:8000/docs | Interactive API explorer |
| Frontend | http://localhost:3000 | Compliance dashboard + operator pages |
| MCP Server | localhost:8001 | AI agent tool integration (12 tools) |
| PostgreSQL | localhost:5432 | System of record |
| Elasticsearch | localhost:9200 | Full-text and vector search |
| Neo4j | localhost:7474 | Rule relationship graph |
| Redis | localhost:6379 | Background job queue |
| Jaeger | localhost:16686 | Distributed tracing UI |
| Prometheus | localhost:9090 | Metrics collection |

---

## Scope Naming

Rules are organized by scope using the pattern `<domain>/<area>[/<region>][/<sub>]`. See [docs/scope-naming.md](docs/scope-naming.md) for the full convention and examples across engineering, HR, legal, finance, compliance, sales, marketing, infosec, and ESG domains.

---

## Additional Capabilities

### See if your rules are working -- at a glance

The **home dashboard** shows compliance rate with trends, rules by status, pending actions, top violated rules, recent corrections, and critical alert banners.

### Organize by project

Rules belong to **projects**. A project selector scopes everything: rules, documents, evaluations, discovery, search.

### Search multiple ways -- with project filtering

Hybrid (BM25 + vector), full-text, semantic, temporal, citation, subject-aware, conflict-aware, and document search.

### Measure rule effectiveness

**Effectiveness score**: precision (false positive rate), prevention rate (did corrections decrease?), and agent adoption (first-attempt pass rate).

### Test rules safely

The **Playground** supports Code and Scenario input modes. Generate test inputs via LLM. Per-rule test cases with auto-generation.

### Enforce everywhere

- **GitHub PR Review** -- webhook posts structured review comments
- **CI Pipeline** -- `rulerepo-check` exits 0/1/2 with `--format github-actions`
- **Agent Hooks** -- `rulerepo-hook preflight` / `posthoc` with `--agent-id`
- **Gateway** -- webhook-driven enforcement (GitHub, Slack, Teams, Email) with policy dispatch
- **Alerts** -- background workers detect dormant rules, high deny rates, health decline, verdict drift

### Propose rule changes collaboratively

Governance proposals with multi-approver voting, threaded comments, conflict analysis, and impact preview.

### Let agents self-govern

Agent profiles with trust levels, personalized rules, verdict challenges, and exception requests.

### Organize rules hierarchically

**Federation** provides org-team-project hierarchy with inheritance and overrides. **Snapshots** capture versioned, deployable rule sets.

### Proactive alerts and digest

Six background workers (arq + Redis) run daily health scoring, recommendation generation, correction clustering, rule auto-promotion, verdict drift monitoring, and a weekly governance digest.

---

## Architecture

```
+----------------------------------------------------------------------+
|                       Rule Management Server                         |
|                                                                      |
|  Extraction   Search(8+)  Evaluation    Intelligence   Discovery     |
|  Pipeline     BM25+Vec    Engine        Health+Recs    + Import      |
|  (bulk +      +Temporal   (batched +    Effectiveness   Federation   |
|   contract    +Citation   conflict-     Digest+Compare  Snapshots    |
|   clause)     +Subject    aware +       Flywheel        Alerts       |
|               +Conflict   remediation   Agent Tracking  Playground   |
|                           + review)                                  |
|  Proposals    Agent Gov                                              |
|  (lifecycle,  (trust,     Provenance    Conflict        Gateway      |
|   voting,     challenge,  Lineage       Scanner         (5 sources   |
|   comments)   sessions)   (Why API)     (daily)          + policy)   |
|                                                                      |
|  PostgreSQL    Elasticsearch   Neo4j       Redis       Audit Log     |
|  (truth)       (search)        (graph)     (jobs)      (immutable)   |
|                                                                      |
|  18 routers  |  MCP Server (12 tools)  |  Gateway  |  GitHub App    |
+----------------------------------------------------------------------+
               |                         |           |
    Rule    Agentic    MCP     CLI     GitHub    Gateway   arq-worker
    SDK      SDK      Server  Tools    App      (webhooks)  (cron)
```

**Three data stores, one source of truth.** PostgreSQL holds canonical data. Elasticsearch is a derived search index. Neo4j is a derived relationship graph. If they disagree, Postgres wins.

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
rulerepo check --diff "$(git diff main...HEAD)" --format github-actions
rulerepo hook preflight --file src/api/handler.py --agent-id claude-code
rulerepo ingest --source pdf --file ./labor-standards-act.pdf --scope hr/attendance/jp
rulerepo export --project backend-api --output rules.yaml
rulerepo context generate --server http://localhost:8000 --project my-project
rulerepo doctor                        # health check
rulerepo audit verify                  # verify audit chain integrity
```

---

## Frontend Pages

The operator console at `http://localhost:3000` provides 23+ pages organized by workflow:

| Section | Pages |
|---------|-------|
| **Manage** | Rules, New Rule, Rule Detail, Proposals, Search, Documents, Discover, Federations, Playground, Snapshots, Tutor |
| **Observe** | Intelligence, Feedback, Notifications, Agents, Audit |
| **Enforce** | Review, Gateway, Integrations |
| **Settings** | Projects |

A **persona switcher** (All / Compliance / Engineering / AI Operator) filters the navigation to show the most relevant pages for each role.

---

## Development

```bash
make help                 # show all targets
make up                   # start full stack
make seed                 # load sample rules + templates
make check                # format + lint + test (run before committing)
make dev.server           # FastAPI with hot-reload
make dev.frontend         # Next.js with hot-reload
```

### Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS |
| LLM | Gemini 3 Flash + Gemini 3.1 Pro via `google-genai` |
| Data | PostgreSQL 17, Elasticsearch 8.17, Neo4j 5, Redis 7 |
| MCP | FastMCP (mcp >= 1.9), 12 tools |
| Observability | OpenTelemetry, Prometheus, Jaeger |
| Quality | ruff + mypy, ESLint + Prettier, pre-commit hooks |
| Package Management | uv (Python), pnpm (Node.js) |

### Running tests

```bash
make test                 # all tests
make test.server          # backend only
make test.frontend        # frontend only
make test.client          # SDK tests
make test.unit            # unit tests only
make test.integration     # integration tests only
make test.cov             # with coverage report
```

---

## Documentation

| Location | Content |
|---|---|
| [PROJECT.md](PROJECT.md) | Vision, domain model, roadmap |
| [CLAUDE.md](CLAUDE.md) | Operational guide -- conventions, Gemini rules, implementation notes |
| [docs/scope-naming.md](docs/scope-naming.md) | Scope naming convention with domain examples |
| [docs/](docs/) | Full documentation site (architecture, API reference, SDKs, integrations) |
| [development/](development/) | Technical development docs (database schema, evaluation engine, testing) |
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

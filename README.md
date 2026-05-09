# Rule Repository

A cross-organization platform for managing natural-language rules. Store, search, evaluate, and enforce rules across legal, HR, finance, engineering, security, sales, communications, and governance -- powered by LLMs.

Traditional rule engines force you to translate human rules into formal logic, losing nuance along the way. The Rule Repository keeps rules in their original natural language and uses LLMs to interpret, search, enforce, and improve them at runtime.

---

## Table of Contents

- [Quick Start](#quick-start)
- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Domain Modules](#domain-modules)
- [Deployment Tiers](#deployment-tiers)
- [Rule Templates](#rule-templates)
- [Evaluation Engine](#evaluation-engine)
- [LLM Provider Abstraction](#llm-provider-abstraction)
- [MCP Server](#mcp-server)
- [Frontend](#frontend)
- [Eval Harness](#eval-harness)
- [Compliance and Privacy](#compliance-and-privacy)
- [SDKs and CLI](#sdks-and-cli)
- [Development](#development)
- [License](#license)

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-started/) and Docker Compose v2
- A [Gemini API key](https://ai.google.dev/gemini-api/docs) (optional -- the stack runs without one, but LLM features will return placeholder verdicts)

### Start the full stack (Tier 3)

```bash
git clone https://github.com/shibuiwilliam/rule-repository.git && cd rule-repository
cp .env.example .env          # add GEMINI_API_KEY if you have one
make up                       # docker compose up --build -d
```

After about a minute:

| Service | URL | What it does |
|---|---|---|
| Backend API | http://localhost:8000 | FastAPI server with 34 API routers |
| Swagger UI | http://localhost:8000/docs | Interactive API explorer |
| Frontend | http://localhost:3000 | Operator console with 44 pages |
| PostgreSQL | localhost:5432 | Canonical data store with Row-Level Security |
| Elasticsearch | localhost:9200 | Full-text + vector hybrid search |
| Neo4j | localhost:7474 | Rule relationship graph |
| Redis | localhost:6379 | Background job queue (arq) |
| MCP Server | localhost:8001 | AI agent tool integration (12 tools) |

### Start with Postgres only (Tier 1)

If you want to skip the full stack and get running quickly:

```bash
make up.tier1                 # server + frontend + postgres only
```

Tier 1 uses Postgres FTS for search, adjacency tables for graph queries, and in-process scheduling. No Elasticsearch, Neo4j, or Redis required.

### Try it

```bash
# Search for rules
curl -X POST http://localhost:8000/api/v1/search/fulltext \
  -H "Content-Type: application/json" \
  -d '{"query": "overtime limit"}'

# Evaluate a code change
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"diff": "- pass\n+ password = os.environ[\"SECRET\"]", "scope": "engineering/python"}'

# Ask a question about rules
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the overtime limits for employees?"}'

# Check onboarding status
curl http://localhost:8000/api/v1/onboarding/status
```

### Stop

```bash
make down                     # stop containers, keep data
docker compose down -v        # stop and delete all volumes
```

---

## What It Does

The Rule Repository stores rules as natural-language statements and evaluates artifacts against them using LLMs. Rules can come from any domain:

- **HR / Labor**: Overtime limits, leave policies, harassment prevention, evaluation fairness
- **Legal**: Contract clause review, NDA standards, IP protection, regulatory compliance
- **Finance**: Expense policies, journal entry controls, invoice compliance, purchase orders
- **Engineering**: Code conventions, security (OWASP), API design, testing standards
- **IT Security**: IaC plan review, access control, encryption requirements
- **Sales**: Advertising compliance, discount authority, quote accuracy
- **Communications**: Confidentiality policies, external communication standards
- **Governance**: Board minute compliance, disclosure requirements, ESG reporting

Each rule carries metadata: modality (MUST / MUST_NOT / SHOULD / MAY), severity (LOW through CRITICAL), scope, effective period, rationale, and examples of compliance and violation.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Rule Repository Server                  │
│                                                           │
│  ┌─────────────────────┐  ┌────────────────────────────┐ │
│  │  Domain-Neutral Core │  │  Domain Modules (8)        │ │
│  │                      │  │                            │ │
│  │  Rule CRUD + Search  │  │  engineering  legal  hr    │ │
│  │  Evaluation Engine   │  │  finance  it_security      │ │
│  │  Fact Store          │  │  sales  communications     │ │
│  │  Tenant + Auth       │  │  governance                │ │
│  │  Audit + Compliance  │  │                            │ │
│  │  Proposals + Gov.    │  │  Each: context assembler,  │ │
│  │  Intelligence        │  │  evaluator, rule selector, │ │
│  │  Risk Register       │  │  discovery analyzer,       │ │
│  │  Attestation         │  │  domain-specific prompts   │ │
│  └─────────────────────┘  └────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────┐  ┌────────────────────────────┐ │
│  │  LLM Abstraction    │  │  Integration Surface       │ │
│  │                      │  │                            │ │
│  │  Router with         │  │  34 REST API routers       │ │
│  │  primary → fallback  │  │  MCP Server (12 tools)     │ │
│  │  Gemini, Anthropic,  │  │  Gateway (webhooks)        │ │
│  │  OpenAI, self-hosted │  │  GitHub App                │ │
│  └─────────────────────┘  └────────────────────────────┘ │
│                                                           │
│   PostgreSQL 17    Elasticsearch 8    Neo4j 5    Redis 7  │
│   (canonical+RLS)  (search index)     (graph)    (jobs)   │
└───────────────────────────────────────────────────────────┘
```

**Key design principles:**

- **Postgres is the source of truth.** Elasticsearch and Neo4j are derived projections. If they disagree, Postgres wins and derivatives are rebuilt.
- **Core never imports from domain modules.** Domain modules register evaluators, analyzers, and prompts via the `DomainModule` protocol. The core dispatches by artifact type.
- **All LLM calls go through `adapters/llm/router.py`.** The router supports primary/fallback chains and per-scope provider overrides. No business logic calls a provider directly.
- **Multi-tenant by construction.** Every entity carries `tenant_id`. Postgres Row-Level Security enforces isolation at the data layer.

---

## Domain Modules

Eight domain modules, each implementing the `DomainModule` protocol:

| Module | Artifact Types | What it evaluates |
|---|---|---|
| **engineering** | `code_diff`, `code_file` | Code changes against coding standards, security rules, API conventions |
| **legal** | `contract_clause`, `contract_document` | Contract clauses against compliance rules, NDA standards, IP protections |
| **hr** | `attendance_record`, `leave_request`, `evaluation_comment` | HR transactions against labor law, leave policies, bias prevention |
| **finance** | `journal_entry`, `expense_request`, `po_request`, `invoice` | Financial transactions against segregation of duties, approval thresholds, tax compliance |
| **it_security** | `iac_plan`, `access_request` | Infrastructure plans and access requests against least-privilege, encryption, MFA policies |
| **sales** | `ad_copy`, `discount_request`, `quote` | Marketing materials and pricing against advertising law, authority limits |
| **communications** | `email_message`, `chat_message` | Communications against confidentiality, external comms, and data leak policies |
| **governance** | `disclosure_document`, `board_minute` | Corporate filings and board meetings against disclosure and governance requirements |

Each module provides:
- **Context assembler** -- transforms the raw artifact into LLM-ready text
- **Evaluator** -- domain-specific system prompt routed through the LLM provider
- **Rule selector** -- filters the corpus by artifact type before ranking
- **Discovery analyzer** -- finds candidate rules from domain-specific documents
- **Templates** -- ready-to-use rule sets

Adding a new domain module means implementing the `DomainModule` protocol and placing the module under `services/domains/<name>/`. The module auto-registers at startup.

---

## Deployment Tiers

The system supports three deployment tiers, controlled by environment variables:

| | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| **Compose file** | `infra/compose/tier1.yml` | `infra/compose/tier2.yml` | `docker-compose.yml` |
| **Make target** | `make up.tier1` | `make up.tier2` | `make up` |
| **PostgreSQL** | Yes | Yes | Yes |
| **Elasticsearch** | No (Postgres FTS) | Yes | Yes |
| **Neo4j** | No (adjacency tables) | No | Yes |
| **Redis + arq** | No (in-process) | Yes | Yes |
| **MCP Server** | No | No | Yes |
| **Best for** | Pilots, local dev | Standard production | Full capability |

The server detects available services at startup via `ELASTICSEARCH_ENABLED`, `NEO4J_ENABLED`, `REDIS_ENABLED`, and `MCP_ENABLED` flags. Application code uses the same interfaces regardless of tier -- adapter selection is transparent.

---

## Rule Templates

27 ready-to-use rule templates covering 270 rules across 8 domains:

| Domain | Templates | Rules |
|---|---|---|
| Engineering | `python-fastapi`, `typescript-react`, `security-owasp`, `api-design`, `testing-standards`, `documentation-standards` | 67 |
| Legal | `contract-nda-standard`, `nda-template`, `legal-contract-review`, `legal-ip-protection`, `legal-regulatory-compliance` | 39 |
| HR | `hr-attendance-jp`, `hr-leave-management`, `hr-evaluation-fairness`, `hr-harassment-prevention`, `hr-overtime-compliance` | 49 |
| Finance | `expense-policy-standard`, `finance-journal-entry`, `finance-invoice-compliance`, `finance-purchase-order`, `finance-revenue-recognition` | 44 |
| Compliance | `bribery-anti-corruption`, `data-privacy-jp`, `advertising-yakukiho` | 56 |
| IT Security | `security-access-control`, `security-iac-terraform` | 12 |
| Governance | `meta-rules-self-governance` | 10 |

Load templates with `make seed` or through the onboarding wizard at `/onboarding`.

> **Note:** Business-domain templates are reference implementations. They should be reviewed by qualified domain counsel before use in production compliance workflows.

---

## Evaluation Engine

The evaluation pipeline:

1. **Context assembly** -- the domain module's context assembler transforms the artifact
2. **Fact resolution** -- the Fact Store resolves external facts (e.g., employee grade, 36-agreement status)
3. **Rule selection** -- 7-stage filter pipeline: scope → subject type → artifact type → dimensions → severity → relevance scoring → agent boosting
4. **LLM evaluation** -- the domain evaluator sends the artifact + rules to the LLM with a domain-specific system prompt
5. **Verdict aggregation** -- individual rule verdicts are aggregated into ALLOW / DENY / NEEDS_CONFIRMATION
6. **Audit persistence** -- model ID, prompt version, inputs, outputs, and latency are logged to the append-only audit chain

Additional evaluation features:
- **Multi-judge consensus** for CRITICAL severity rules (second LLM provider confirms)
- **Confidence calibration** via conformal prediction
- **Verdict drift detection** alerts when the same rule+input produces different verdicts over time
- **Prompt injection defense** wraps all user content in delimiters and screens for known injection patterns
- **Cost guardrails** per-tenant monthly budget with 80% warning and 100% hard cap (HTTP 429)

---

## LLM Provider Abstraction

All LLM calls go through `adapters/llm/router.py`, which implements a primary-to-fallback chain:

| Provider | Status | Use case |
|---|---|---|
| **Gemini** (`google-genai`) | Implemented | Default primary provider |
| **Anthropic** | Stub (ready for API key) | Fallback or consensus second judge |
| **OpenAI** | Stub (ready for API key) | Fallback |
| **Self-hosted** (Ollama/vLLM) | Stub (ready for endpoint) | RESTRICTED sensitivity rules |

Configuration:
```bash
LLM_PROVIDER_PRIMARY=gemini
LLM_PROVIDER_FALLBACK=anthropic,openai
LLM_TENANT_OVERRIDES={"hr-confidential": "local"}
```

Each provider implements the `LLMProvider` protocol: `generate`, `generate_structured`, `embed`, `count_tokens`, plus cost properties. The router records structured logs for every call.

---

## MCP Server

The MCP (Model Context Protocol) server exposes 12 tools for AI agent integration:

| Tool | Purpose |
|---|---|
| `search_rules` | Find rules by natural-language query with scope/severity filters |
| `explain_rule` | Detailed explanation with rationale, provenance, and history |
| `find_conflicts` | Detect conflicts with existing rules |
| `evaluate_compliance` | Evaluate changes against applicable rules |
| `discover_rules` | Propose rules from code, configs, or documents |
| `get_rules_for_context` | Get rules for current coding context |
| `create_proposal` | Submit a rule change proposal |
| `get_proposal_status` | Check proposal approval status |
| `register_agent` | Register an agent with the governance system |
| `get_personalized_rules` | Get rules tailored to an agent's trust level |
| `challenge_verdict` | Challenge a verdict with evidence |
| `request_exception` | Request a one-time exception to a rule |

```bash
# stdio mode (for Claude Code, Cursor, etc.)
uv run rulerepo-mcp

# HTTP mode (for remote agents)
MCP_TRANSPORT=streamable-http uv run rulerepo-mcp
```

---

## Frontend

A Next.js 15 + React 19 + Tailwind CSS frontend with 44 pages organized into persona-based portals:

| Portal | Route prefix | Key pages |
|---|---|---|
| **Dashboard** | `/dashboard` | Rules, search, proposals, playground, agents, intelligence, audit |
| **HR** | `/hr` | Attendance, leave management, event detail |
| **Legal** | `/legal` | Contract review, clause library |
| **Finance** | `/finance` | Transaction screening |
| **Compliance** | `/compliance` | Bundle progress (J-SOX, GDPR) |
| **Security** | `/security` | Classification overview |
| **Marketing** | `/marketing` | Creative review |
| **Admin** | `/admin` | Tenant management, user provisioning |
| **Ask** | `/ask` | Conversational rule assistant |
| **Onboarding** | `/onboarding` | 3-step wizard: select domain → choose templates → scan sources |

The frontend supports English and Japanese via `next-intl`.

---

## Eval Harness

The eval harness validates LLM-driven features against curated golden datasets:

```bash
make eval                     # run all domains
make eval.domain DOMAIN=legal # run one domain
make eval.json                # output JSON report
```

**Golden datasets:** 90 test cases across 8 domains:

| Domain | Cases | Coverage |
|---|---|---|
| Engineering | 20 | Credentials, SQL injection, XSS, error handling, type hints, API design |
| Legal | 10 | Indemnification, governing law, data protection, NDA clauses |
| HR | 10 | Overtime limits, leave balance, evaluation bias, harassment |
| Finance | 10 | Segregation of duties, approval thresholds, tax compliance |
| IT Security | 10 | Public S3, IAM wildcards, encryption, MFA, access requests |
| Sales | 10 | Health claims, disclaimers, discount authority, pricing |
| Communications | 10 | Confidentiality, external comms, data leaks |
| Governance | 10 | Disclosure completeness, quorum, conflict of interest |

A CI workflow (`.github/workflows/eval.yml`) runs the harness on PRs that touch prompts or evaluators and fails if precision drops more than 5%.

---

## Compliance and Privacy

- **PII scrubbing**: Middleware on the evaluate/ask/extract/gateway endpoints detects PII fields and redacts them before they reach the LLM. Redacted values are stored encrypted in a shadow store for authorized restoration.
- **Prompt injection defense**: All LLM-bound user content is wrapped in stable delimiters and screened against 20 known injection patterns. Detected injections force `NEEDS_CONFIRMATION`.
- **Audit trail**: Append-only, hash-chained audit log in Postgres. Each entry links to the previous via SHA-256. WORM storage mirroring available when configured.
- **Retention policies**: Per-scope retention periods (J-SOX 7y, HIPAA 6y, GDPR 6y, employment 10y) with legal hold support.
- **Attestation campaigns**: Create campaigns requiring users to acknowledge specific rules, with completion tracking and reminders.
- **Classification levels**: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED -- enforced via Postgres RLS.
- **OIDC authentication**: Generic OIDC provider integration with tenant extraction from JWT claims.

---

## SDKs and CLI

### Python SDK

```python
from rulerepo import RuleClient

async with RuleClient("http://localhost:8000") as client:
    results = await client.search.hybrid("overtime limit", scope="hr/attendance")
```

### CLI

```bash
rulerepo check --diff "$(git diff main...HEAD)" --format github-actions
rulerepo hook preflight --file src/api/handler.py --agent-id claude-code
rulerepo ingest --source pdf --file ./policy.pdf --scope hr/attendance/jp
rulerepo export --project backend-api --output rules.yaml
```

### Packages

| Package | Path | Purpose |
|---|---|---|
| `rule-client` | `packages/rule-client/` | Python SDK for rule CRUD and search |
| `agentic-client` | `packages/agentic-client/` | Python SDK wrapping evaluation for AI agents |
| `cli` | `packages/cli/` | CLI tools (check, hook, ingest, export, context) |
| `connectors` | `packages/connectors/` | Business system connectors (SmartHR, freee) |

---

## Development

### Commands

```bash
make help                     # list all 71 make targets
make up                       # start Tier 3 (full stack)
make up.tier1                 # start Tier 1 (Postgres only)
make seed                     # load sample rules + templates
make check                    # format + lint + test
make eval                     # run eval harness
make dev.server               # FastAPI with hot-reload
make dev.frontend             # Next.js with hot-reload
```

### Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS |
| LLM | Gemini via `google-genai` (pluggable to Anthropic, OpenAI, self-hosted) |
| Data | PostgreSQL 17 (RLS), Elasticsearch 8, Neo4j 5, Redis 7 |
| MCP | FastMCP (mcp >= 1.9) |
| Observability | structlog (JSON), structured audit log |
| Quality | ruff + mypy, ESLint + Prettier, eval harness (90 golden cases) |
| Packages | uv (Python), pnpm (frontend) |

### Repository layout

```
rule-repository/
├── apps/
│   ├── server/                        # FastAPI backend (465 Python files)
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/                # 34 REST API routers
│   │   │   ├── core/                  # Config, auth, PII, tenancy, metrics, telemetry
│   │   │   ├── domain/               # Pure domain models (24 files)
│   │   │   ├── services/
│   │   │   │   ├── domains/           # 8 domain modules (engineering through governance)
│   │   │   │   ├── evaluation/        # Evaluation engine, rule selector, consensus
│   │   │   │   ├── intelligence/      # Health scoring, drift detection, coverage heatmap
│   │   │   │   ├── core/audit_export/ # WORM writer, retention, exporter
│   │   │   │   └── ...               # 20+ service modules
│   │   │   ├── adapters/             # Postgres, ES, Neo4j, Gemini, LLM router
│   │   │   ├── mcp/                  # MCP server (12 tools)
│   │   │   ├── gateway/              # Webhook enforcement
│   │   │   └── workers/              # Background jobs (arq)
│   │   ├── eval_harness/             # 90 golden test cases across 8 domains
│   │   └── tests/                    # 65 test files (746 tests)
│   └── frontend/                     # Next.js 15 (44 pages, 10 components)
├── packages/                         # SDK, CLI, connectors
├── sample_rules/                     # 37 sample rule documents + 27 templates (270 rules)
├── infra/                            # Docker, Postgres init + RLS, ES templates
├── scripts/                          # seed_data, reconcile_graph, verify_audit_chain
├── docs/                             # Documentation site
├── PROJECT.md                        # Vision and domain model
├── CLAUDE.md                         # Operational guide
├── IMPROVEMENT.md                    # Gap analysis and improvement registry (40 items, all merged)
└── docker-compose.yml                # Full Tier 3 stack (12 services)
```

### Tests

```bash
make test                     # all tests
make test.server              # backend only
make test.unit                # unit tests
make test.integration         # integration tests
make test.e2e                 # end-to-end tests
make test.cov                 # with coverage report
```

### Quality gates

```bash
make format.check             # check formatting (CI mode)
make lint                     # ruff + mypy + ESLint
make check                    # format + lint + test (run before committing)
make ci                       # full CI pipeline: install + check
```

---

## Contributing

1. Read [CLAUDE.md](CLAUDE.md) -- it's the operational contract for this project
2. Run `make precommit.install` to set up pre-commit hooks
3. Branch from `main`, use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`)
4. Run `make check` before pushing
5. Mock the LLM in unit tests -- never call real providers
6. If your change touches prompts or evaluators, include `make eval` output in the PR

---

## License

See [LICENSE](./LICENSE).

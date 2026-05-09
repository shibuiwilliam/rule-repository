# Rule Repository

An organization-wide platform for managing rules in natural language -- laws, contracts, HR regulations, expense policies, communication standards, engineering conventions, and everything in between. Store them once, search them instantly, enforce them everywhere.

Traditional rule engines force you to translate human-written rules into code or formal logic. The translation is expensive, lossy, and drifts from the original intent over time. The Rule Repository takes a different approach: keep every rule exactly as written, and let LLMs interpret, search, and enforce them at runtime.

A legal counsel reviewing an NDA, an HR manager checking overtime compliance, a finance officer screening an expense claim, and an engineer running a pre-commit check all use the same platform -- each through a console designed for their workflow.

---

## Table of Contents

- [Quick Start](#quick-start)
- [What You Can Do](#what-you-can-do)
- [How It Works](#how-it-works)
- [Surfaces and Domain Packs](#surfaces-and-domain-packs)
- [Architecture](#architecture)
- [Deployment Tiers](#deployment-tiers)
- [MCP Server](#mcp-server)
- [CLI Tools](#cli-tools)
- [Frontend](#frontend)
- [Evaluation Engine](#evaluation-engine)
- [Norm Lineage](#norm-lineage)
- [Rule Templates](#rule-templates)
- [Compliance and Privacy](#compliance-and-privacy)
- [Eval Harness](#eval-harness)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-started/) and Docker Compose v2
- A [Gemini API key](https://ai.google.dev/gemini-api/docs) (optional -- the stack runs without one, but LLM features will return placeholder verdicts)

### Start the full stack

```bash
git clone https://github.com/shibuiwilliam/rule-repository.git && cd rule-repository
cp .env.example .env          # add GEMINI_API_KEY if you have one
make up                       # docker compose up --build -d
make seed                     # load sample rules across all domains
```

After about a minute:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | FastAPI server (36 API routers) |
| Swagger UI | http://localhost:8000/docs | Interactive API explorer |
| Frontend | http://localhost:3000 | Persona-specific consoles (55 pages) |
| PostgreSQL | localhost:5432 | Source of truth with Row-Level Security |
| Elasticsearch | localhost:9200 | Full-text + vector hybrid search |
| Neo4j | localhost:7474 | Rule relationship graph + norm lineage |
| Redis | localhost:6379 | Background job queue (arq) |
| MCP Server | localhost:8001 | AI agent tool integration (18 tools) |

### Start with Postgres only (Tier 1)

For quick exploration without the full infrastructure:

```bash
make up.tier1                 # server + frontend + postgres only
```

Tier 1 uses Postgres FTS for search, adjacency tables for graph queries, and in-process scheduling. No Elasticsearch, Neo4j, or Redis required.

### Try it

```bash
# Search for rules across any domain
curl -X POST http://localhost:8000/api/v1/search/fulltext \
  -H "Content-Type: application/json" \
  -d '{"query": "overtime limit"}'

# Review a contract clause against legal rules
curl -X POST http://localhost:8000/api/v1/evaluate/contract \
  -H "Content-Type: application/json" \
  -d '{
    "subject": {
      "surface": "contract",
      "identifier": "nda-draft-1",
      "payload": {
        "clause_text": "The receiving party may share Confidential Information with any affiliate.",
        "clause_type": "confidentiality",
        "parties": ["Acme Corp", "Beta Inc"]
      },
      "facts": {},
      "locale": "en"
    },
    "mode": "posthoc"
  }'

# Check an HR action against labor regulations
curl -X POST http://localhost:8000/api/v1/evaluate/human_action \
  -H "Content-Type: application/json" \
  -d '{
    "subject": {
      "surface": "human_action",
      "identifier": "overtime-check",
      "payload": {
        "action": "register_overtime",
        "actor_id": "E001",
        "facts": {"hours": 50, "month": "2025-04"}
      },
      "facts": {"hours": 50},
      "locale": "en"
    },
    "mode": "posthoc"
  }'

# Evaluate a code change (backwards-compatible endpoint)
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"diff": "- pass\n+ password = os.environ[\"SECRET\"]", "scope": "engineering/python"}'

# Ask a question in natural language
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the overtime limits for employees?"}'
```

### Stop

```bash
make down                     # stop containers, keep data
docker compose down -v        # stop and delete all volumes
```

---

## What You Can Do

The Rule Repository stores rules as natural-language statements and evaluates any kind of work artifact against them using LLMs. Rules can come from any domain:

- **Legal**: Review contract clauses against NDA/MSA templates, detect missing protections, track regulatory changes
- **HR / Labor**: Check overtime against 36-agreement caps, validate leave requests, monitor attendance compliance
- **Finance**: Screen expense claims, enforce approval thresholds, validate tax deduction eligibility
- **Communications**: Flag harassment, detect confidential data in chat channels, ensure product-claim accuracy
- **Engineering**: Enforce coding standards, catch security issues (OWASP), validate API design
- **IT Security**: Review IaC plans, check access control, verify encryption requirements
- **Sales**: Validate advertising claims, enforce discount authority, check quote accuracy
- **Governance**: Verify disclosure completeness, track board minute compliance, monitor ESG reporting

Each rule carries structured metadata: modality (MUST / MUST_NOT / SHOULD / MAY / INFO), severity (LOW through CRITICAL), scope, effective period, norm tier, locale, rationale, and examples of both compliance and violation.

---

## How It Works

1. **Store rules in natural language.** Import them from PDFs, Word documents, markdown files, or create them directly. Each rule keeps its original wording, source reference, and full revision history.

2. **Evaluate anything against those rules.** Send a *Subject* -- a code diff, a contract clause, an HR event, a financial transaction, a chat message, or any text -- and the system selects the relevant rules, sends them to an LLM alongside the subject, and returns per-rule verdicts.

3. **Track norm lineage.** Rules don't exist in isolation. A department overtime policy *derives from* the Labor Standards Act. When the law changes, every downstream rule is automatically flagged for review.

4. **Act on the results.** Integrate via REST API, MCP tools for AI agents, or CLI commands in CI/CD. Each persona (Legal, HR, Finance, Engineering, Compliance) has a dedicated console.

---

## Surfaces and Domain Packs

### Surfaces

A **Surface** defines a type of thing being evaluated. The evaluation engine is surface-agnostic -- it does not know or care whether it is evaluating code or a contract. Each surface has its own adapter that translates domain-specific input into a uniform Subject.

| Surface | What it evaluates | Example input |
|---|---|---|
| **Code** | Diffs, file changes, repository state | `git diff` output |
| **Contract** | Clauses, redlines, contract metadata | NDA clause text + parties |
| **Human Action** | HR events, attendance, leave requests | Overtime registration |
| **Transaction** | Expenses, invoices, journal entries | Expense claim with amount |
| **Document** | Policies, reports, marketing copy | Internal policy section |
| **Message** | Emails, chat messages, chat logs | Chat message content |
| **Generic** | Anything else | Free-form text + facts |

Each surface provides: a Subject dataclass, a SurfaceAdapter (parses input, resolves scopes, provides prompt hints), a PII field list, and a default audit retention period.

### Domain Packs

A **Domain Pack** bundles rules, prompt hints, samples, and frontend route declarations for one business domain. Adding a new domain is an additive operation -- no changes to the evaluation core.

| Pack | Surface | Persona | Rules |
|---|---|---|---|
| **Code** | Code | Engineering | 7 engineering standards |
| **Contract** | Contract, Document | Legal | 30 clause templates (NDA, MSA, SOW) |
| **HR Attendance** | Human Action | HR | 25 labor regulation rules |
| **Communication** | Message | Compliance | 20 communication policies |
| **Expense** | Transaction | Finance | 15 fiscal policy rules |

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Rule Repository Server                      │
│                                                                 │
│  ┌──────────────────┐  ┌────────────────────────────────────┐  │
│  │ Domain-Neutral    │  │ Surfaces (7)                       │  │
│  │ Core              │  │                                    │  │
│  │                   │  │ Code  Contract  Human Action       │  │
│  │ Rule CRUD+Search  │  │ Transaction  Document  Message     │  │
│  │ Evaluation Engine │  │ Generic                            │  │
│  │ Norm Lineage      │  │                                    │  │
│  │ Audit + Compliance│  │ Each: adapter, subject dataclass,  │  │
│  │ Intelligence      │  │ prompt hints, PII config           │  │
│  │ Proposals + Gov.  │  ├────────────────────────────────────┤  │
│  │ Fact Store        │  │ Domain Packs (5)                   │  │
│  │ Risk Register     │  │                                    │  │
│  │ Attestation       │  │ Code  Contract  HR Attendance      │  │
│  │ Multi-tenant      │  │ Communication  Expense             │  │
│  └──────────────────┘  └────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────┐  ┌────────────────────────────────────┐  │
│  │ LLM Abstraction  │  │ Integration Layer                  │  │
│  │                   │  │                                    │  │
│  │ Primary/fallback  │  │ 36 REST API routers                │  │
│  │ Gemini, Anthropic │  │ MCP Server (18 tools)              │  │
│  │ OpenAI, self-host │  │ Gateway (webhooks)                 │  │
│  └──────────────────┘  │ GitHub integration                  │  │
│                         └────────────────────────────────────┘  │
│                                                                 │
│  PostgreSQL 17     Elasticsearch 8     Neo4j 5     Redis 7     │
│  (source of truth) (search index)      (graph)     (jobs)      │
└─────────────────────────────────────────────────────────────────┘
```

**Design principles:**

- **Postgres is the source of truth.** Elasticsearch and Neo4j are derived projections. If they disagree, Postgres wins and projections are rebuilt.
- **The evaluation core is surface-agnostic.** No surface-specific code lives in `services/evaluation/core/`. An import-boundary test enforces this.
- **All LLM calls go through a single router** with primary/fallback chains and per-scope provider overrides. No business logic calls a provider directly.
- **Multi-tenant by construction.** Every entity carries `tenant_id`. Postgres Row-Level Security enforces isolation at the data layer.
- **Norm Lineage and Organizational Federation are orthogonal.** A rule sits on two independent axes: its norm tier (Law to Operational Rule) and its organizational owner (Org to Team to Project). They are modeled, queried, and rendered separately.

---

## Deployment Tiers

| | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| **Make target** | `make up.tier1` | `make up.tier2` | `make up` |
| **PostgreSQL** | Yes | Yes | Yes |
| **Elasticsearch** | No (Postgres FTS) | Yes | Yes |
| **Neo4j** | No (adjacency tables) | No | Yes |
| **Redis + arq** | No (in-process) | Yes | Yes |
| **MCP Server** | No | No | Yes |
| **Best for** | Pilots, local dev | Standard production | Full capability |

The server detects available services at startup and adapts automatically. Application code uses the same interfaces regardless of tier.

---

## MCP Server

The MCP (Model Context Protocol) server lets AI agents interact with the rule repository. It exposes 18 tools:

| Tool | Purpose |
|---|---|
| `search_rules` | Find rules by natural-language query with scope/severity filters |
| `explain_rule` | Detailed explanation with rationale, provenance, and relationships |
| `find_conflicts` | Detect conflicts between rules |
| `evaluate_compliance` | Evaluate a code change against applicable rules |
| `evaluate_subject` | Evaluate any subject (contract, HR event, etc.) against rules |
| `discover_rules` | Propose rules from code, configs, or documents |
| `get_rules_for_context` | Get rules relevant to a coding context |
| `list_available_surfaces` | List all registered evaluation surfaces |
| `lookup_norm_lineage` | Walk the norm hierarchy upstream or downstream |
| `find_clause_conflicts` | Detect conflicts in contract clauses |
| `check_action` | Check whether a human action is compliant |
| `review_communication` | Review a message for policy compliance |
| `create_proposal` | Submit a rule change proposal |
| `get_proposal_status` | Check proposal approval status |
| `register_agent` | Register an agent with the governance system |
| `get_personalized_rules` | Get rules tailored to an agent's trust level |
| `challenge_verdict` | Challenge a verdict with evidence |
| `request_exception` | Request a one-time exception to a rule |

```bash
# stdio mode (for Claude Code, Cursor, Windsurf, etc.)
uv run rulerepo-mcp

# HTTP mode (for remote agents)
MCP_TRANSPORT=streamable-http uv run rulerepo-mcp
```

---

## CLI Tools

The unified `rulerepo` CLI consolidates all commands. Legacy standalone entry points (`rulerepo-check`, etc.) are preserved for backwards compatibility.

```bash
# Evaluate a code change in CI
rulerepo check --diff "$(git diff main...HEAD)" --format github-actions

# Review a contract document
rulerepo review-contract --file ./contracts/draft.docx --output redline.html

# Check an HR action against labor regulations
rulerepo check-action --action register_overtime --actor user:E001 --json '{"hours":50}'

# Pre-commit hook for AI agents
rulerepo hook preflight --file src/api/handler.py --agent-id claude-code

# Ingest rules from a document
rulerepo ingest --source pdf --file ./policy.pdf --scope hr/attendance/jp

# Export rules to YAML
rulerepo export --project backend-api --output rules.yaml
```

---

## Frontend

A Next.js 15 + React 19 + Tailwind CSS frontend with 55 pages organized into persona-specific consoles. Each persona sees a dashboard aligned to their workflow, not a generic engineering view.

| Console | Route | Key pages |
|---|---|---|
| **Engineering** | `/dashboard` | Rules, search, proposals, playground, agents, intelligence, audit |
| **Legal** | `/legal` | Contract review, clause library, redlines, norm lineage |
| **HR** | `/hr` | Violations, attendance, leave, lifecycle, policies |
| **Finance** | `/finance` | Transactions, expense policies, audit reports, controls |
| **Compliance** | `/compliance` | Bundles, audit packets, exception tracking, regulatory feed |
| **Security** | `/security` | Classification overview |
| **Marketing** | `/marketing` | Creative review |
| **Admin** | `/admin` | Tenant management, user provisioning |

Additional portals: `/ask` (conversational rule assistant), `/onboarding` (3-step wizard: select domain, choose templates, scan sources).

The frontend supports English and Japanese via `next-intl`, with a locale switcher in every console.

---

## Evaluation Engine

The evaluation pipeline works the same regardless of the surface:

1. **Surface adapter** -- transforms domain-specific input (diff, contract clause, HR event, etc.) into a uniform Subject
2. **Rule selection** -- multi-stage filter pipeline: scope, subject type, artifact type, dimensions, severity, relevance scoring
3. **Fact resolution** -- the Fact Store resolves external facts (employee grade, 36-agreement status, contract value)
4. **LLM evaluation** -- the selected rules and the subject are sent to the LLM with surface-specific prompt hints. Cross-locale fallback selects translated rule statements when available, with structured logging when it falls back to the canonical locale
5. **Verdict aggregation** -- per-rule verdicts are aggregated into ALLOW / DENY / NEEDS_CONFIRMATION / ALLOW_WITH_CONDITIONS / REQUIRES_DISCLOSURE
6. **Audit persistence** -- model ID, prompt version, inputs, outputs, latency, surface, actor, and locale are logged to the append-only, hash-chained audit log

Additional features:
- **Multi-judge consensus** for CRITICAL-severity rules (a second LLM provider confirms)
- **Confidence calibration** via conformal prediction
- **Verdict drift detection** alerts when the same rule + input produces different verdicts over time
- **Prompt injection defense** wraps user content in delimiters and screens for known injection patterns
- **Cost guardrails** with per-tenant monthly budget, 80% warning, and 100% hard cap

---

## Norm Lineage

Every rule has a **norm tier** that places it in a regulatory hierarchy:

```
LAW  -->  REGULATION  -->  GUIDELINE  -->  CORPORATE_POLICY  -->  DEPARTMENT_RULE  -->  OPERATIONAL_RULE
```

Rules are linked via `DERIVES_FROM` relationships. Walking the chain answers questions like *"Which law is this overtime policy derived from?"* or *"If this regulation changes, which internal rules are affected?"*

- **Upstream walk**: from an operational rule back to its source law
- **Downstream walk**: from a law to all derived internal rules
- **Amendment propagation**: when a LAW or REGULATION rule changes, a background worker flags every transitive downstream rule with `pending_norm_change_review`
- **Bilingual drift detection**: a daily worker compares EN/JA rule translations and flags semantic drift above threshold

The norm lineage is **orthogonal** to the organizational federation (Org / Team / Project). A single rule can simultaneously derive from the Labor Standards Act (norm axis) and be owned by the HR department (org axis). The two hierarchies are queried separately and rendered in separate UI components.

---

## Rule Templates

27 ready-to-use templates covering 270+ rules across 7 domains:

| Domain | Templates | Example topics |
|---|---|---|
| Engineering | 6 | Python/FastAPI, TypeScript/React, OWASP security, API design, testing, documentation |
| Legal | 5 | NDA review, contract clauses, IP protection, regulatory compliance |
| HR | 5 | Attendance (JP), leave management, evaluation fairness, harassment prevention, overtime |
| Finance | 5 | Expense policy, journal entries, invoice compliance, purchase orders, revenue recognition |
| Compliance | 3 | Anti-corruption, data privacy (JP), advertising regulations |
| IT Security | 2 | Access control, IaC/Terraform |
| Governance | 1 | Self-governance meta-rules |

Load templates with `make seed` or through the onboarding wizard at `/onboarding`.

Japanese-language rules are included for labor law (Labor Standards Act), privacy (APPI), civil code, childcare/family care leave, and tax regulations.

> **Note:** Business-domain templates are reference implementations. Review them with qualified domain counsel before use in production compliance workflows.

---

## Compliance and Privacy

- **PII scrubbing**: Each surface declares its PII-sensitive fields. The evaluation pipeline redacts them before they reach the LLM. Redacted values are stored encrypted for authorized restoration.
- **Surface-aware retention**: Audit records are retained per surface (e.g., 1 year for code evaluations, 10 years for contract evaluations). Per-scope overrides are supported.
- **Prompt injection defense**: All LLM-bound user content is wrapped in stable delimiters and screened against known injection patterns. Detected injections force a `NEEDS_CONFIRMATION` verdict.
- **Audit trail**: Append-only, hash-chained audit log in Postgres. Each entry links to the previous via SHA-256. WORM storage mirroring available when configured.
- **Attestation campaigns**: Create campaigns requiring users to acknowledge specific rules, with completion tracking and reminders.
- **Classification levels**: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED -- enforced via Postgres Row-Level Security.

---

## Eval Harness

The eval harness validates LLM-driven features against curated golden datasets:

```bash
make eval                     # run all domains
make eval.domain DOMAIN=legal # run one domain
make eval.json                # output JSON report
```

90 golden test cases across 8 domains (engineering, legal, HR, finance, IT security, sales, communications, governance). A CI workflow runs the harness on PRs that touch prompts or evaluators and fails if precision drops more than 5%.

---

## Development

### Commands

```bash
make help                     # list all make targets
make up                       # start full stack (Tier 3)
make up.tier1                 # start with Postgres only
make seed                     # load sample rules + templates
make check                    # format + lint + test (run before committing)
make eval                     # run eval harness
make dev.server               # FastAPI with hot-reload
make dev.frontend             # Next.js with hot-reload
make test                     # all tests
make test.unit                # unit tests only
make test.cov                 # with coverage report
```

### Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS, next-intl |
| LLM | Gemini via `google-genai` (pluggable: Anthropic, OpenAI, self-hosted) |
| Data | PostgreSQL 17 (RLS), Elasticsearch 8, Neo4j 5, Redis 7 (arq) |
| MCP | FastMCP (mcp >= 1.9) |
| Quality | ruff + mypy, ESLint + Prettier, eval harness (90 golden cases) |
| Packages | uv (Python), pnpm (frontend) |

### Repository layout

```
rule-repository/
├── apps/
│   ├── server/                        # FastAPI backend
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/                # 36 REST API routers
│   │   │   ├── domain/                # Pure domain models (Rule, Surface, Actor, NormTier)
│   │   │   ├── services/
│   │   │   │   ├── evaluation/        # Surface-agnostic evaluation engine
│   │   │   │   │   ├── core/          # Universal pipeline (no surface imports)
│   │   │   │   │   └── surfaces/      # 7 per-surface adapters
│   │   │   │   ├── domains/           # 8 domain modules
│   │   │   │   ├── intelligence/      # Health scoring, drift detection, analytics
│   │   │   │   ├── norm_lineage/      # Upstream/downstream lineage walker
│   │   │   │   ├── extraction/        # Document ingestion, bilingual pairing, redline diff
│   │   │   │   ├── discovery/         # Rule discovery from documents and code
│   │   │   │   ├── feedback/          # Correction-to-rule flywheel
│   │   │   │   └── ...               # 25+ more service modules
│   │   │   ├── domain_packs/          # Code, Contract, HR, Communication, Expense
│   │   │   ├── adapters/              # Postgres, ES, Neo4j, Gemini, LLM router
│   │   │   ├── mcp/                   # MCP server (18 tools)
│   │   │   └── workers/               # 9 background job workers
│   │   ├── eval_harness/              # 90 golden test cases
│   │   └── tests/                     # 65 test files
│   └── frontend/                      # Next.js 15 (55 pages, 12 components)
├── packages/
│   ├── rule-client/                   # Python SDK
│   ├── agentic-client/                # Python agentic SDK
│   └── cli/                           # CLI tools (8 commands)
├── sample_rules/                      # Sample rules + 27 templates (270+ rules)
├── infra/                             # Docker, Postgres init, ES templates
├── scripts/                           # Seeding, graph reconciliation, audit verification
├── PROJECT.md                         # Vision, domain model, roadmap
├── CLAUDE.md                          # Operational guide for contributors
└── docker-compose.yml                 # Full stack (Tier 3)
```

### Python SDKs

```python
from rulerepo import RuleClient

async with RuleClient("http://localhost:8000") as client:
    results = await client.search.hybrid("overtime limit", scope="hr/attendance")
```

| Package | Path | Purpose |
|---|---|---|
| `rule-client` | `packages/rule-client/` | Python SDK for rule CRUD and search |
| `agentic-client` | `packages/agentic-client/` | Python SDK wrapping evaluation for AI agents |
| `cli` | `packages/cli/` | CLI tools (check, hook, ingest, export, review-contract, check-action) |

---

## Contributing

1. Read [CLAUDE.md](CLAUDE.md) -- it is the operational contract for this project
2. Run `make precommit.install` to set up pre-commit hooks
3. Branch from `main`, use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`)
4. Run `make check` before pushing
5. Mock the LLM in unit tests -- never call real providers
6. If your change touches prompts or evaluators, include `make eval` output in the PR
7. New surfaces go in `services/evaluation/surfaces/<name>/`. New domain packs go in `domain_packs/<name>/`. Neither requires changes to the evaluation core.

---

## License

See [LICENSE](./LICENSE).

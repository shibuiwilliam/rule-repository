# Rule Repository

**Cross-organization norm management platform** -- store, search, evaluate, and enforce natural-language rules across legal, HR, finance, engineering, marketing, and beyond, powered by LLMs and AI agents.

Traditional rule engines force you to translate human rules into formal logic, losing nuance along the way. The Rule Repository keeps rules exactly as written -- in natural language -- and uses LLMs to interpret, search, enforce, and improve them at runtime.

Whether the rules come from **labor regulations, contract standards, expense policies, anti-corruption laws, data privacy mandates, advertising restrictions**, engineering guidelines, or coding conventions, this system stores them in their original form, makes them searchable across multiple modalities, evaluates actions against them, delivers them to both human operators and AI agents at the moment they matter, and **learns from every correction** to create better rules over time.

---

## Table of Contents

- [What You Can Do](#what-you-can-do)
- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Domain Plugins](#domain-plugins)
- [Persona Portals](#persona-portals)
- [Rule Templates](#rule-templates)
- [Evaluation Engine](#evaluation-engine)
- [Fact Store](#fact-store)
- [Connector Hub](#connector-hub)
- [MCP Server and AI Agent Integration](#mcp-server-and-ai-agent-integration)
- [SDKs and CLI](#sdks-and-cli)
- [Eval Harness](#eval-harness)
- [Compliance and Privacy](#compliance-and-privacy)
- [Additional Capabilities](#additional-capabilities)
- [Development](#development)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## What You Can Do

### Enforce HR and labor compliance

Load the `hr-attendance-jp` template (25 rules grounded in the Labor Standards Act) and evaluate overtime registrations, leave requests, and scheduling decisions against statutory limits -- monthly overtime caps, 36-Agreement requirements, mandatory leave usage, maternity protections, and record-keeping obligations. The HR plugin's form evaluator handles employee context automatically via the Fact Store.

### Review contracts against your standards

The `contract-nda-standard` template checks NDAs for missing definitions, asymmetric obligations, overbroad residuals clauses, and missing governing-law provisions. The legal plugin's clause extractor breaks uploaded contracts into clause-level units for granular review, with remediation suggestions that are never auto-applied (contract changes require human judgment).

### Control expenses and prevent fraud

The `expense-policy-standard` template validates expense submissions against approval thresholds, receipt requirements, entertainment documentation rules, qualified invoice compliance, and anti-splitting controls. The finance plugin's transaction evaluator integrates with ERP connectors for real-time preflight checks.

### Prevent bribery and corruption

The `bribery-anti-corruption` template covers FCPA, UK Bribery Act, and JP Unfair Competition Prevention Act -- gift thresholds, facilitation payments, third-party due diligence, government contract reviews, and whistleblowing obligations.

### Protect personal data

The `data-privacy-jp` template enforces APPI requirements: purpose specification, consent management, third-party transfer controls, breach notification obligations, and individual rights (disclosure, correction, deletion, cessation). PII is automatically redacted before reaching the LLM.

### Regulate advertising claims

The `advertising-yakukiho` template catches prohibited pharmaceutical efficacy claims, missing disclaimers, unauthorized health-food claims, and endorsement violations under Japan's Pharmaceutical and Medical Device Act. The marketing plugin evaluates creative assets with channel-aware rule selection.

### Enforce engineering standards

Seven engineering templates cover Python/FastAPI conventions, TypeScript/React patterns, OWASP security rules, API design standards, testing practices, and documentation standards -- evaluated against code diffs in CI pipelines, agent hooks, and GitHub PR reviews.

### Discover rules from existing documents

Drop files or give a GitHub URL -- the discovery engine analyzes CLAUDE.md, linter configs, policy documents, code patterns, and business sources (Confluence, Notion, e-Gov, EUR-Lex) to propose rules. Upload PDFs (regulations, contracts) and the extraction pipeline proposes candidate rules with article-level source references.

### Learn from corrections

When humans correct AI-generated output, the system captures the delta, clusters similar corrections, and auto-drafts rule proposals via Gemini. Approved proposals start in shadow mode and graduate automatically. Every correction teaches the system.

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-started/) and Docker Compose (v2)
- A [Gemini API key](https://ai.google.dev/gemini-api/docs) (optional -- the stack starts without one, but LLM features will be unavailable)

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
| Backend API | http://localhost:8000 | FastAPI with 25 API routers |
| Swagger UI | http://localhost:8000/docs | Interactive API explorer |
| Frontend | http://localhost:3000 | Persona-driven operator console (43 pages) |
| MCP Server | localhost:8001 | AI agent tool integration (12 tools) |
| PostgreSQL | localhost:5432 | System of record with Row-Level Security |
| Elasticsearch | localhost:9200 | Full-text + vector hybrid search |
| Neo4j | localhost:7474 | Rule relationship graph |
| Redis | localhost:6379 | Background job queue |
| Jaeger | localhost:16686 | Distributed tracing UI |
| Prometheus | localhost:9090 | Metrics collection |

### Try it out

**Search for rules:**

```bash
curl -X POST http://localhost:8000/api/v1/search/fulltext \
  -H "Content-Type: application/json" \
  -d '{"query": "overtime limit"}'
```

**Evaluate an HR event:**

```bash
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"subject_kind": "event", "facts": {"employee_id": "E001", "overtime_hours": 50}}'
```

**Evaluate a code change:**

```bash
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"diff": "...", "intent": "Add new API endpoint", "scope": "engineering/python"}'
```

**Upload a document for rule extraction:**

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@path/to/policy.pdf"
```

**Resolve external facts:**

```bash
curl -X POST http://localhost:8000/api/v1/facts/resolve \
  -H "Content-Type: application/json" \
  -d '{"facts": ["employee_grade", "36_agreement_status"], "context": {"employee_id": "E001", "month": "2026-04"}}'
```

### Tear down

```bash
docker compose down       # stop containers, keep data
docker compose down -v    # stop containers and delete all volumes
```

---

## Architecture

```
+-----------------------------------------------------------------------+
|                        Rule Management Server                          |
|                                                                        |
|  +-------------------------------+  +-------------------------------+  |
|  |       Domain-Neutral Core     |  |       Domain Plugins          |  |
|  |                               |  |                               |  |
|  |  Storage + Search + Audit     |  |  Engineering  (code eval)     |  |
|  |  Evaluation Orchestrator      |  |  HR / Labor   (form eval)     |  |
|  |  Fact Store                   |  |  Legal        (doc eval)      |  |
|  |  Tenant / Identity / ABAC     |  |  Finance      (txn eval)     |  |
|  |  Proposals + Governance       |  |  Marketing    (content eval)  |  |
|  |  Intelligence + Alerts        |  |                               |  |
|  |  Eval Harness                 |  |  Each plugin: evaluators,     |  |
|  |  Compliance + PII             |  |  extractors, prompts,         |  |
|  |  Operability + Metrics        |  |  golden datasets              |  |
|  +-------------------------------+  +-------------------------------+  |
|                                                                        |
|  +-------------------------------+  +-------------------------------+  |
|  |       Connector Hub           |  |      Integration Surface      |  |
|  |  SmartHR  Salesforce  freee   |  |  25 REST routers              |  |
|  |  EventSource + Sink protocols |  |  MCP Server (12 tools)        |  |
|  |  Per-tenant configuration     |  |  Gateway (webhook enforce)    |  |
|  +-------------------------------+  |  GitHub App + CI              |  |
|                                     +-------------------------------+  |
|                                                                        |
|   PostgreSQL 17   Elasticsearch 8   Neo4j 5   Redis 7   Prometheus     |
|   (truth + RLS)   (search + DLS)   (graph)    (jobs)   (metrics)       |
+------------------------------------------------------------------------+
              |               |             |              |
     Rule SDK + Agentic SDK + MCP + CLI + Gateway + arq-worker
```

### Design principles

**Three data stores, one source of truth.** PostgreSQL holds canonical data with Row-Level Security for tenant isolation and classification-based access control. Elasticsearch is a derived search index with document-level security. Neo4j is a derived relationship graph. If they disagree, Postgres wins and derivatives are rebuilt.

**Domain-neutral core, domain-specific plugins.** The evaluation orchestrator, rule selector, and verdict aggregator know nothing about code diffs, contract clauses, or HR forms. Each domain is a plugin that registers evaluators, extractors, feedback sources, and prompts. The core never imports from any plugin.

**Multi-tenant by construction.** Every business object carries a `tenant_id`. Cross-tenant access is impossible through PostgreSQL RLS policies, not application-level checks. `tenant_id` is derived from the authenticated principal, never from the request body.

**Classification-enforced access.** Every rule, document, evaluation, and audit entry carries a classification level (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`). PostgreSQL RLS, Elasticsearch filters, and MCP clearance enforce boundaries at every layer.

**LLM verdicts are decision support, not decision automation.** High-severity verdicts route to humans. Every verdict is reproducible -- model, prompt version, inputs, and outputs are logged in an append-only, hash-chained audit log.

---

## Domain Plugins

The plugin architecture separates domain-specific logic from the core platform. Each plugin is self-contained and registers its capabilities at server startup.

| Plugin | Evaluator | Subject Kinds | Key Capabilities |
|---|---|---|---|
| **Engineering** | `CodeChangeEvaluator` | `code_diff` | Diff parsing, language detection, scope resolution, structured remediations |
| **HR / Labor** | `FormEvaluator` | `event` | Overtime/leave/attendance evaluation, HRIS integration, sequence and calendar modes |
| **Legal** | `DocumentEvaluator` | `clause_set`, `document` | Clause-level extraction, contract comparison, non-auto-applicable remediations |
| **Finance** | `TransactionEvaluator` | `transaction` | Expense/journal entry compliance, approval routing, period-aware rules |
| **Marketing** | `ContentEvaluator` | `creative` | Channel-aware rule selection, Keihyohou/Yakkihou compliance |

Each plugin ships with: evaluators, extractors, prompt templates, and a golden dataset for the eval harness. Plugins import from the core; the core never imports from plugins; plugins never import from each other.

---

## Persona Portals

The frontend serves different roles through dedicated portals, each with its own navigation and feature set.

| Portal | Route | Key Pages |
|---|---|---|
| **Engineering** | `/dashboard` | Rules, search, proposals, playground, agents, code evaluation, intelligence |
| **HR** | `/hr` | Attendance compliance, leave management, employee risk scores, HRIS status |
| **Legal** | `/legal` | Contract review queue, clause library, regulatory horizon, citations |
| **Compliance** | `/compliance` | Bundle progress (J-SOX, GDPR, EU AI Act), audit packets, exception tracking |
| **Security** | `/security` | Data classification overview, encryption keys, eval harness scores, access logs |
| **Finance** | `/finance` | Transaction screening, expense compliance, approval routing |
| **Marketing** | `/marketing` | Creative review queue, channel compliance, claim verification |
| **Admin** | `/admin` | Tenant management, user/group provisioning, connector configuration, billing |

A **persona switcher** in the top bar lets users with multiple roles navigate between portals. The frontend supports English and Japanese via `next-intl`.

---

## Rule Templates

Fourteen pre-built rule sets covering 7+ domains:

| Template | Rules | Domain |
|---|---|---|
| `hr-attendance-jp` | 25 | HR / Labor Law (Japan) |
| `contract-nda-standard` | 15 | Legal / Contracts |
| `expense-policy-standard` | 20 | Finance / Expenses (Japan) |
| `bribery-anti-corruption` | 18 | Compliance / Anti-Corruption |
| `data-privacy-jp` | 18 | Compliance / Privacy (Japan) |
| `advertising-yakukiho` | 20 | Compliance / Advertising (Japan) |
| `python-fastapi` | 15 | Engineering / Python |
| `typescript-react` | 12 | Engineering / TypeScript |
| `security-owasp` | 10 | Engineering / Security |
| `api-design` | 10 | Engineering / API Design |
| `testing-standards` | 10 | Engineering / Testing |
| `documentation-standards` | 10 | Engineering / Documentation |
| `meta-rules-self-governance` | -- | Governance / Meta-Rules |
| `nda-template` | -- | Legal / NDA Review |

Each template rule includes: `statement`, `modality`, `severity`, `classification`, `subject_kinds`, `scope`, `jurisdiction`, `rationale`, `tags`, and `violation_examples`.

> **Important:** All business-domain templates are marked `expert_reviewed: false (reference only)`. They must be reviewed by qualified domain counsel before use for actual regulatory compliance.

---

## Evaluation Engine

The evaluation engine is split into a domain-neutral orchestrator and pluggable evaluators dispatched by subject kind.

**Pipeline:** Tenant Resolution -> Context Assembly -> Fact Resolution -> Rule Selection -> Evaluator Dispatch -> Verdict Aggregation -> Audit Persistence

**Eight subject kinds** with dedicated adapters:

| Subject Kind | Input | Use Case |
|---|---|---|
| `CODE_DIFF` | Unified diff | Code review, CI checks |
| `CLAUSE_SET` | Parsed contract clauses | Contract review |
| `EVENT` | HR/business event | Overtime, leave, attendance |
| `TRANSACTION` | Journal entry, expense | Financial compliance |
| `CREATIVE` | Ad copy, campaign asset | Marketing compliance |
| `DECISION` | Decision record | Governance review |
| `IDENTITY` | Person/entity profile | Screening, KYC |
| `DOCUMENT` | Full document | Policy review |

**Tiered model selection** routes by severity: Flash model for routine evaluations, Pro model for CRITICAL rules, consensus voting (3 independent evaluations) for `statutory` + `CRITICAL` combinations.

```bash
# Evaluate with the default subject kind (code_diff)
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"diff": "...", "scope": "engineering/python"}'

# Evaluate an HR event
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"subject_kind": "event", "facts": {"employee_id": "E001", "overtime_hours": 50, "month": "2026-04"}}'
```

---

## Fact Store

The Fact Store resolves external facts that rules depend on but that no input artifact contains.

**Example:** the rule "Overtime above 45 hours requires a valid 36-agreement" needs to know whether the 36-agreement exists in the labor management system. The Fact Store resolves `36_agreement_status(employee_id, month)` at evaluation time and injects it into the evaluation context.

**Built-in providers:**

| Provider | Facts Resolved | Source |
|---|---|---|
| `EmployeeAttributesProvider` | `employee_grade`, `employee_department`, `employment_type`, `36_agreement_status` | HRIS sync table |
| `OFACSanctionsProvider` | `ofac_match`, `sanctions_screening_status` | OFAC SDN list |
| `InternalMasterDataProvider` | `product_category`, `vendor_status`, `cost_center_budget` | Tenant master data |
| `RegulatoryFeedProvider` | `regulation_status`, `regulation_effective_date` | e-Gov / regulatory feeds |

Facts are cached with provider-declared TTLs and scoped by tenant. New providers implement the `FactProvider` protocol and register at startup.

---

## Connector Hub

Bidirectional integration with business systems through `EventSource` (pull events into evaluation) and `Sink` (push verdicts and alerts back) protocols.

**Reference connectors:**

| Connector | Type | Integration |
|---|---|---|
| **SmartHR** | HRIS | Attendance, overtime, leave events; evaluation results as comments |
| **Salesforce** | CRM | Opportunity updates, contract submissions; compliance alerts |
| **freee** | ERP | Journal entries, expense claims; approval status flags |

Each connector is a separately versioned package under `packages/connectors/`. Per-tenant configuration with credential management through a pluggable secrets backend (Vault, AWS SM, GCP SM).

---

## MCP Server and AI Agent Integration

The MCP server exposes 12 tools for AI agent integration via the Model Context Protocol:

| Tool | Purpose |
|---|---|
| `search_rules` | Find rules by natural language query, scope, modality, severity |
| `explain_rule` | Deep explanation with rationale, provenance, relationships, history |
| `find_conflicts` | Detect potential conflicts with existing rules |
| `evaluate_compliance` | Evaluate code changes or actions against applicable rules |
| `discover_rules` | Propose rules from file contents or repository analysis |
| `get_rules_for_context` | Get formatted rules for a specific file/scope context |
| `create_proposal` | Submit a rule change proposal |
| `get_proposal_status` | Check proposal approval status |
| `register_agent` | Register an agent with trust level and clearance |
| `get_personalized_rules` | Get rules tailored to an agent's trust level and history |
| `challenge_verdict` | Challenge a verdict with supporting evidence |
| `request_exception` | Request a one-time exception to a rule |

```bash
# stdio mode (for Claude Code local integration)
uv run rulerepo-mcp

# HTTP mode (for remote agents)
MCP_TRANSPORT=streamable-http uv run rulerepo-mcp
```

---

## SDKs and CLI

### Python SDK

```python
from rulerepo import RuleClient

async with RuleClient("http://localhost:8000") as client:
    results = await client.search.hybrid("overtime limit", scope="hr/attendance")
    rule = await client.rules.get(rule_id)
```

### Agentic Client

```python
from rulerepo_agentic import AgenticRuleClient

async with AgenticRuleClient("http://localhost:8000") as client:
    result = await client.evaluate(
        context={"employee_id": "E001", "overtime_hours": 50},
        intent="register_overtime", mode="preflight",
    )
    if result.verdict == "DENY":
        for v in result.violations:
            print(v.rule_statement, v.reason, v.suggested_fix)
```

### CLI Tools

```bash
# Evaluate code changes in CI
rulerepo check --diff "$(git diff main...HEAD)" --format github-actions

# Agent hooks (inject rules before edits, evaluate after)
rulerepo hook preflight --file src/api/handler.py --agent-id claude-code
rulerepo hook posthoc --file src/api/handler.py

# Import rules from documents
rulerepo ingest --source pdf --file ./labor-standards-act.pdf --scope hr/attendance/jp

# Export rules
rulerepo export --project backend-api --output rules.yaml

# Generate CLAUDE.md context from rules
rulerepo context generate --server http://localhost:8000 --project my-project

# Verify audit chain integrity
rulerepo audit verify
```

---

## Eval Harness

The eval harness measures verdict quality across domains using golden datasets -- expert-labeled test cases with expected verdicts and reasoning.

```bash
# Run the full harness
uv run python -m eval.runner --dataset-dir apps/server/eval/datasets

# Run for a single domain
uv run python -m eval.runner --domain hr --output-format table

# Filter by difficulty
uv run python -m eval.runner --domain legal --tag-filter "hard"
```

**Golden datasets included:**

| Domain | Cases | Coverage |
|---|---|---|
| Engineering | 50 | Naming, security (SQLi, XSS), error handling, type hints, API design, logging |
| HR / Labor | 50 | Overtime limits, paid leave, 36-agreement, maternity, harassment, termination |
| Legal | 50 | NDA clauses, liability, indemnification, governing law, data protection, IP |
| Content | 50 | Misleading claims, price display, testimonials, health claims, ad disclosures |

**Quality gates:** new plugins require F1 >= 0.80 on their golden dataset. Prompt changes require no regression > 2 percentage points. A drift detector compares consecutive runs and alerts on threshold violations.

---

## Compliance and Privacy

### PII redaction

All evaluation contexts pass through `core/pii/redactor.py` before reaching the LLM. Subject adapters declare which fields contain PII, and the redactor replaces them with traceable placeholders. Original values are encrypted in a shadow store and can be restored for authorized access.

### Right to erasure

`DELETE /api/v1/data-subjects/{subject_id}` performs GDPR Article 17 erasure -- deletes PII from the shadow store, replaces identifiers in evaluations with tombstone markers, and preserves the audit hash chain integrity.

### Classification and access control

Four classification levels (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`) enforced through PostgreSQL RLS, Elasticsearch document-level security, and MCP agent clearance. Every query runs within a user context that sets classification and department boundaries.

### Audit trail

Append-only, hash-chained audit log in PostgreSQL. Each entry links to the previous via SHA-256 hash. Daily anchoring to Sigstore Rekor transparency log. WORM storage mirroring for `RESTRICTED` and `CONFIDENTIAL` entries. Regulator export formats: J-SOX, SOX, FSA, GDPR.

### Approval policies

Declarative DSL for approval requirements per rule category:

```yaml
- match: { legal_force: statutory }
  requires:
    - role: legal_director
      count: 1
      sla_hours: 72
  mandatory_consultation: [dpo]
```

Segregation of duties enforced: proposer != approver != enactor.

---

## Additional Capabilities

### Multi-tenancy

Full tenant isolation with OIDC/SAML SSO, SCIM 2.0 user/group provisioning, and ABAC policy engine. Per-tenant settings for data residency, LLM region, encryption keys, LLM budget, and active plugins.

### Observability

OpenTelemetry instrumentation across all service calls, LLM invocations, and database queries. Prometheus-compatible `/metrics` endpoint. Per-tenant cost tracking with budget enforcement. Jaeger distributed tracing.

### Search

Eight search modalities: hybrid (BM25 + kNN), full-text, semantic, temporal, citation, subject-aware, conflict-aware, and document search -- all with classification-based filtering.

### Intelligence

Health scoring, effectiveness measurement (precision, prevention rate, agent adoption), weekly governance digests, correction clustering, and rule recommendations.

### Proposals and governance

Collaborative rule change proposals with multi-approver voting, threaded comments, conflict analysis, and change impact simulation against historical evaluations.

### Agent governance

Agent profiles with progressive trust levels, personalized rule delivery, verdict challenges, and exception requests. Agents earn trust through evaluation history.

### Federation and snapshots

Org-team-project hierarchy with rule inheritance and overrides. Versioned snapshots for atomic deployment of rule sets with rollback capability.

### Background workers

arq + Redis workers handle: health scoring, correction analysis, rule auto-promotion, verdict drift monitoring, conflict scanning, policy review cycles, locale consistency checks, and weekly digest generation.

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
| Data | PostgreSQL 17 (RLS), Elasticsearch 8.17, Neo4j 5, Redis 7 |
| MCP | FastMCP (mcp >= 1.9), 12 tools |
| Connectors | SmartHR, Salesforce, freee (reference implementations) |
| Observability | OpenTelemetry, Prometheus, Jaeger |
| Quality | ruff + mypy, ESLint + Prettier, eval harness, 56 test files |
| Package Management | uv (Python), pnpm (Node.js) |

### Running tests

```bash
make test                 # all tests
make test.server          # backend only
make test.frontend        # frontend only
make test.unit            # unit tests only
make test.integration     # integration tests only
make test.cov             # with coverage report
make test.e2e             # end-to-end tests
```

### Quality gates

```bash
make lint                 # ruff + mypy + ESLint + tsc
make format               # ruff format + ruff check --fix
make format.check         # check without modifying (CI mode)
make ci                   # full CI pipeline: install + check
```

### Repository layout

```
rule-repository/
├── apps/
│   ├── server/                    # FastAPI backend (Python 3.13, uv)
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/            # 25 REST routers
│   │   │   ├── core/              # config, auth, PII, tenancy, ABAC, metrics
│   │   │   ├── domain/            # Pure domain types (15 modules)
│   │   │   ├── plugins/           # Domain plugins (engineering, hr, legal, finance, marketing)
│   │   │   ├── services/          # 22 service modules
│   │   │   ├── adapters/          # postgres, elasticsearch, neo4j, gemini, LLM providers
│   │   │   ├── subjects/          # Subject adapters (code, contract, HR, expense)
│   │   │   ├── mcp/               # MCP server (12 tools)
│   │   │   ├── gateway/           # Webhook enforcement
│   │   │   └── workers/           # arq background jobs
│   │   ├── eval/                  # Eval harness (runner, reporters, golden datasets)
│   │   └── tests/                 # 56 test files
│   └── frontend/                  # Next.js 15 + React 19 + Tailwind (43 pages)
├── packages/
│   ├── rule-client/               # Python SDK
│   ├── agentic-client/            # Agentic Python SDK
│   ├── cli/                       # CLI tools
│   └── connectors/                # SmartHR, Salesforce, freee
├── sample_rules/                  # 35+ sample rule documents + 14 templates
├── infra/                         # Docker, Postgres init + RLS, ES templates, Neo4j constraints
├── scripts/                       # seed_data, reconcile_graph, verify_audit_chain
├── docs/                          # Full documentation site
├── PROJECT.md                     # Vision, domain model, roadmap
├── CLAUDE.md                      # Operational guide for contributors
└── docker-compose.yml             # Full stack orchestration (12 services)
```

---

## Documentation

| Location | Content |
|---|---|
| [PROJECT.md](PROJECT.md) | Vision, domain model, architecture, roadmap |
| [CLAUDE.md](CLAUDE.md) | Operational guide -- conventions, Gemini rules, plugin patterns |
| [IMPROVEMENT.md](IMPROVEMENT.md) | Strategic gap analysis and improvement plan |
| [docs/](docs/) | Full documentation site: architecture, API, SDKs, integrations |
| [docs/scope-naming.md](docs/scope-naming.md) | Scope naming convention with domain examples |
| [development/adr/](development/adr/) | Architecture Decision Records |
| [Swagger UI](http://localhost:8000/docs) | Interactive API docs (when stack is running) |

---

## Contributing

1. Read [CLAUDE.md](CLAUDE.md) -- it's the working contract for this project
2. Run `make precommit.install`
3. Branch from `main`, use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`)
4. Run `make check` before pushing
5. Mock Gemini in unit tests (never call the real LLM)
6. If your change touches prompts or models, include an eval harness regression run in the PR description

---

## License

See [LICENSE](./LICENSE).

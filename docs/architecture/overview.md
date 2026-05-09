# Architecture Overview

## Deployable Components

The Rule Repository consists of twelve services (plus setup containers and observability), all orchestrated locally via Docker Compose. The backend exposes 22 API routers backed by 20+ service directories. Rules are scoped to projects and departments for multi-team, cross-organizational governance.

| Component | Technology | Port | Role |
|---|---|---|---|
| **Backend API** | Python 3.13 / FastAPI | 8000 | System of record. REST, Evaluate, Intent, Gateway, and Integration APIs (22 routers). |
| **MCP Server** | Python / FastMCP | 8001 | Exposes rule search, evaluation, governance, and context delivery to AI agents via the Model Context Protocol (12+ tools). |
| **Frontend** | TypeScript / Next.js 15 / Tailwind | 3000 | Operator console with 30+ pages for browsing, searching, uploading documents, reviewing evaluations, governance proposals, agent management, department-specific surfaces, and more. Persona-aware navigation with English/Japanese i18n. |
| **PostgreSQL** | PostgreSQL 17 | 5432 | Relational store with Row-Level Security for classification-based access control. Stores rules, revisions, relationships, documents, audit log, policies, evaluations, proposals, agent profiles, snapshots, federations, departments, capacities, and cache. |
| **Elasticsearch** | Elasticsearch 8.17 | 9200 | Full-text (BM25) and vector (768-dim cosine) search index for rules and documents, with document-level security filtering. |
| **Neo4j** | Neo4j 5 Community | 7474 / 7687 | Directed graph of rule relationships (REFINES, OVERRIDES, CONFLICTS_WITH, DEPENDS_ON, DERIVES_FROM, SUCCEEDS, LOCALIZES). |
| **Redis** | Redis 7 Alpine | 6379 | Job queue and result backend for background workers. |
| **arq-worker** | Python 3.13 / arq | -- | Background worker running 9+ scheduled cron jobs (health scoring, recommendations, rule promotion, correction clustering, verdict drift, weekly digest, conflict scanning, policy review cycle, archival). |
| **Jaeger** | Jaeger 1.62 | 16686 | Distributed tracing via OpenTelemetry (OTLP gRPC on 4317, OTLP HTTP on 4318). |
| **Prometheus** | Prometheus v3.4 | 9090 | Metrics collection from the backend `/metrics` endpoint. |

## Data Store Roles

- **PostgreSQL** is the system of record. All rule data, revisions, evaluations, proposals, agent profiles, departments, classifications, and audit records live here. Row-Level Security enforces classification-based access control on rules, documents, evaluations, and audit log tables.
- **Elasticsearch** is a derived search index. It is rebuilt from PostgreSQL on rule changes. Also indexes documents for document search. Document-level security filters enforce classification at query time.
- **Neo4j** is a derived relationship graph. PostgreSQL wins if they disagree; the `reconcile_graph.py` script can rebuild Neo4j from scratch.

## Layering Rule

The backend follows a strict layering discipline:

```
api/  -->  services/  -->  domain/
                      -->  adapters/
```

- `api/` (routers) depends on `services/` only.
- `services/` depends on `domain/` (pure business objects) and `adapters/` (Postgres, Elasticsearch, Neo4j, Gemini, LLM providers).
- `domain/` depends on nothing else in the project.
- `mcp/`, `gateway/`, `integrations/` are parallel to `api/` -- they call services directly.
- No layer imports upward.

## Subject Polymorphism

The evaluation engine is domain-agnostic. Eight subject kinds are supported:

| Subject Kind | Domain | Example |
|---|---|---|
| `CODE_DIFF` | Engineering | Code changes, diffs, file edits |
| `CLAUSE_SET` | Legal | Contract clauses, NDA terms |
| `EVENT` | HR / Operations | Overtime registrations, leave requests |
| `TRANSACTION` | Finance | Expense submissions, purchase orders |
| `CREATIVE` | Marketing | Ad copy, promotional materials |
| `DECISION` | Management | Approval decisions, policy exceptions |
| `IDENTITY` | Compliance | KYC checks, sanctions screening |
| `DOCUMENT` | General | Policy documents, handbooks |

Each subject kind has its own adapter, prompt templates, and aggregation logic under `services/evaluation/subjects/`. The orchestrator (`services/evaluation/service.py`) calls `subject_registry.resolve(subject_kind)` and never branches on the kind directly.

## Department-Aware Governance

Rules belong to departments (Legal, HR, Finance, Sales, Marketing, IT, Operations, R&D, Executive, Custom). The `DepartmentService` resolves:

- **Owners** -- who is responsible for a rule
- **Approvers** -- who must approve proposals (severity-based thresholds)
- **Audiences** -- who gets notifications for a capacity (OWNER, REVIEWER, SUBSCRIBER, AUDITOR)

Proposals, intelligence digests, marketplace publishing, and audit read access all route through department resolvers.

## Classification and Access Control

Every rule, document, evaluation, and audit entry carries a classification:

| Classification | Access |
|---|---|
| `PUBLIC` | All authenticated users |
| `INTERNAL` | Organization members |
| `CONFIDENTIAL` | Department members + approved subscribers |
| `RESTRICTED` | Named individuals or AUDITORs only |

Access is enforced at three layers:
1. **PostgreSQL RLS** -- `with_user_context()` sets session-local variables before every query
2. **Elasticsearch** -- `classification_filter(user)` is injected into all search queries
3. **MCP** -- agents register with a clearance level; rule delivery is filtered accordingly

## Key Data Flows

### Rule Creation

1. Client sends `POST /api/v1/rules` with a rule statement and metadata.
2. The rule service persists the rule to PostgreSQL, indexes it in Elasticsearch, and creates the corresponding Neo4j node.
3. An audit log entry records the creation event.

### Document Extraction

1. Client uploads a document via `POST /api/v1/documents/upload`.
2. Client triggers extraction via `POST /api/v1/documents/{id}/extract`.
3. The extraction pipeline (Gemini-powered) proposes candidate rules. For contracts, the pipeline segments clauses, classifies them, and resolves cross-references.
4. A human reviews, edits, and approves candidates, which become rules through the standard creation flow.

### Evaluation

1. Client sends a diff, file list, business event, or free-form facts to `POST /api/v1/evaluate`, optionally specifying `subject_kind`.
2. The subject registry resolves the appropriate adapter for the subject kind (defaults to `CODE_DIFF`).
3. The evaluation engine selects relevant rules (metadata filtering + effective_period enforcement + semantic ranking). When `agent_id` is provided, historically-violated rules are boosted.
4. The graph resolver fetches Neo4j relationships (OVERRIDES, CONFLICTS_WITH, DEPENDS_ON) between selected rules and builds an evaluation plan.
5. The **batched evaluator** sends all selected rules to Gemini in a single API call with structured JSON output requesting per-rule verdicts. For DENY + CRITICAL rules, a Pro model confirmation pass re-evaluates those specific rules. If the batch call fails, the system falls back to per-rule concurrent evaluation.
6. Each evaluation result is persisted to the `evaluations` table for analytics.
7. The conflict-aware aggregator applies overrides, resolves conflicts (severity > modality > specificity tiebreak), and skips rules whose prerequisite was denied.
8. The response includes violations, warnings, code locations, fix suggestions, structured remediations, and `conflict_resolutions[]` explaining any relationship-based decisions.
9. The full evaluation is logged to the audit trail.

See [Batched Evaluation](batch-evaluation.md) for the detailed architecture.

### Two-Tier Activity Review

1. Client sends an activity description to `POST /api/v1/evaluate/review/rough`.
2. The rough tier evaluates all rules for relevance and returns a shortlist.
3. Client sends the shortlist to `POST /api/v1/evaluate/review/detailed` for full LLM evaluation with fix suggestions.

### Context Delivery (MCP)

1. An AI agent connects to the MCP server (stdio or streamable-HTTP transport).
2. The agent calls `get_rules_for_context` with its current working context (file paths, format preference, optional federation node).
3. The MCP server resolves scopes from file paths, selects applicable rules filtered by the agent's clearance level, and returns them in a format optimized for LLM consumption (instructions, checklist, or detailed).

### Rule Discovery

1. Client submits project artifacts to `POST /api/v1/discover/scan` -- or uses **one-click GitHub import** via `POST /api/v1/discover/import` with a repository URL.
2. For GitHub import: the importer fetches CLAUDE.md, pyproject.toml, eslint config, tsconfig, and other key files via the GitHub Contents API.
3. Source analyzers (CLAUDE.md, linter config, code patterns, policy documents, Confluence, Notion, Google Drive, SharePoint, e-Gov, EUR-Lex) extract candidate rules; the pattern detector deduplicates and scores them.
4. Gemini refines candidates into well-formed rule statements with suggested metadata.
5. Candidates enter a human review queue for approval or dismissal.

### Correction Feedback

1. A correction is submitted manually via `POST /api/v1/feedback/corrections`, or **captured automatically** when a PR is merged that differs from what was evaluated.
2. For auto-capture: the PR merge webhook compares the evaluated diff (stored in audit log) against the final merged diff, and submits the delta as a correction.
3. Gemini analyzes the correction and classifies it (new_rule, improve_existing, adjust_scope).
4. Approved corrections create or update rules, closing the feedback loop.
5. The daily correction clustering job auto-drafts rule proposals from similar correction patterns.

### Rule Impact Preview

1. Before updating a rule, call `POST /api/v1/rules/{id}/impact-preview` with proposed changes.
2. The system replays historical evaluations involving that rule with the modified version.
3. Returns how many verdicts would change, affected repositories, and a risk assessment.

### Federation

1. Rules are organized into a hierarchy of federation nodes (organization, team, project).
2. When rules are requested for a node, the federation resolver walks the ancestor chain and applies overrides.
3. The effective rule set reflects inherited rules plus local customizations.

### Webhook Enforcement (Gateway)

1. An external system (GitHub, Slack, Teams, Email, or generic) sends a webhook to `POST /api/v1/gateway/ingest/{source}`.
2. The gateway normalizes the event using source-specific normalizers, matches it against enabled enforcement policies, and runs the evaluation engine.
3. Results are recorded and optionally trigger response actions.

### Governance Proposals

1. A user creates a proposal (create, amend, retire, merge, split, override) via `POST /api/v1/proposals`.
2. The proposal is submitted for review, triggering conflict analysis and impact preview. Approvers are resolved from the owning department based on severity.
3. Approvers vote; the system auto-transitions on all-approve or any-reject.
4. Enacted proposals are applied by the enactor (creates rules, updates fields, retires originals, etc.).

### Agent Governance

1. An agent registers via MCP or API with capabilities, type, and clearance level.
2. The system tracks compliance rate, builds a mastery profile, and adjusts trust level.
3. Personalized rule delivery suppresses mastered rules and boosts weak areas.
4. Agents can challenge verdicts or request exceptions, which create audit trails and may trigger rule improvements.

### Playground Evaluation

1. Client sends a rule definition and sample code/scenario to `POST /api/v1/playground/evaluate`.
2. The sandbox pipeline runs the same Gemini evaluation but skips audit logging, LLM caching, and persistence.
3. Returns a verdict, confidence, reasoning, and fix suggestion. Supports counterexample generation.

### Snapshots and Environments

1. An operator creates a snapshot (`POST /api/v1/snapshots`) capturing the current live rule corpus.
2. The snapshot is deployed to an environment (development, staging, production) via `POST /api/v1/snapshots/{id}/deploy`.
3. Evaluation and MCP requests that specify an `environment` parameter resolve rules from the deployed snapshot rather than the live corpus.
4. Impact simulation (`POST /api/v1/snapshots/{id}/simulate`) replays historical evaluations to predict verdict changes before promotion.

### Proactive Alerts

1. Background workers (health refresh cron) and the evaluation pipeline detect conditions such as dormant rules, high deny rates, health declines, verdict drift, effectiveness decline, and conflicts.
2. Alerts are created in the alerts table and surfaced via `GET /api/v1/alerts` and the dashboard banner.
3. Operators acknowledge or resolve alerts through the API or the dashboard alerts panel.

### Compliance-Grade Audit

1. Every evaluation, rule change, proposal action, and evidence attachment is recorded in the append-only, hash-chained audit log.
2. For `RESTRICTED` and `CONFIDENTIAL` entries, the audit service queues WORM storage mirroring (S3 Object Lock, Azure Immutable Blob, or GCS Bucket Lock).
3. Hash chain heads are periodically anchored to Sigstore Rekor (or configured timestamp authority).
4. PII fields marked at Subject construction time are redacted before logging.
5. Legal holds prevent deletion or modification of matching entries.
6. Regulator export adapters produce J-SOX, SOX, FSA, and GDPR-compliant artifacts.

## Plugin Architecture

The backend uses a plugin system for domain-specific logic. Each plugin registers evaluators, extractors, and feedback handlers under `plugins/`:

| Plugin | Directory | Evaluators | Extractors | Feedback |
|---|---|---|---|---|
| **Engineering** | `plugins/engineering/` | `code_change.py` | `claude_md.py`, `linter_config.py` | `pr_capture.py` |
| **Legal** | `plugins/legal/` | `document_evaluator.py` | `clause_extractor.py` | -- |
| **HR** | `plugins/hr/` | `form_evaluator.py` | `handbook.py` | -- |
| **Finance** | `plugins/finance/` | `transaction_evaluator.py` | -- | -- |
| **Marketing** | `plugins/marketing/` | `content_evaluator.py` | -- | -- |

Plugins are registered via `plugins/_registry.py` and extend the base protocol in `plugins/base.py`. The domain-neutral core never imports from any plugin; plugins consume core services.

### Phase 8 Domain Engines

Two specialized evaluation engines were added in Phase 8:

- **Contract Clause Engine** (`POST /api/v1/evaluate/contract`): parses contracts (DOCX/PDF/text) via `adapters/contract_parser.py`, compares clauses via `adapters/contract_compare.py`, aggregates clause-level verdicts via `services/evaluation/clause_aggregator.py`. Supports self-conformance, cross-contract, regulatory compliance, and risk scoring modes. See [ADR 004](../../development/adr/0004-contract-clause-engine.md).
- **Event Engine** (`POST /api/v1/evaluate/event`): evaluates business events (overtime, leave, attendance) with three temporal modes -- single, sequence (monthly), and calendar (annual). Domain types in `domain/event_sequence.py`. See [ADR 005](../../development/adr/0005-event-engine-temporal-modes.md).

## Domain Module Architecture

The system supports 8 domain modules under `services/domains/`, each with evaluators, context assemblers, discovery analyzers, and evaluation prompts:

| Domain | Module | Evaluates |
|---|---|---|
| **Engineering** | `domains/engineering/` | Code changes, diffs, linter configs |
| **Legal** | `domains/legal/` | Contracts, clauses, regulatory documents |
| **HR** | `domains/hr/` | Attendance, overtime, leave, forms |
| **Finance** | `domains/finance/` | Invoices, journal entries, POs, expenses |
| **IT Security** | `domains/it_security/` | IaC configs, vulnerability reports, access requests |
| **Sales** | `domains/sales/` | Discount approvals, quotes, ad copy |
| **Communications** | `domains/communications/` | Emails, Slack/Teams messages |
| **Governance** | `domains/governance/` | Disclosures, board minutes, ESG reports |

All domain evaluators extend `BaseDomainEvaluator` which handles LLM routing, prompt loading, and structured output. The domain-neutral core (`services/evaluation/service.py`) dispatches to domain modules through the domain registry.

## Tier 1 Infrastructure (Postgres-Only)

The system supports three deployment tiers:

- **Tier 1** (Postgres only): Postgres FTS replaces Elasticsearch, adjacency tables replace Neo4j, APScheduler replaces Redis. For dev machines, CI, and minimal deployments.
- **Tier 2** (Postgres + Elasticsearch): Adds vector/hybrid search. No graph or background queue.
- **Tier 3** (Full stack): Postgres + Elasticsearch + Neo4j + Redis. Production default.

Feature flags: `ELASTICSEARCH_ENABLED`, `NEO4J_ENABLED`, `REDIS_ENABLED`.

## Pluggable LLM Providers

The LLM layer supports multiple providers via `adapters/llm/router.py`:

| Provider | Status | Notes |
|---|---|---|
| Gemini (Google) | Primary | Default provider |
| Anthropic Claude | Available | Via `adapters/llm/anthropic.py` |
| OpenAI | Available | Via `adapters/llm/openai.py` |
| Self-hosted | Available | Via `adapters/llm/local.py` |

The router provides fallback chains, circuit breaker pattern, and per-tenant provider overrides.

## Further Reading

See [Data Stores](data-stores.md) for schema details, [Evaluation Engine](evaluation-engine.md) for the evaluation pipeline, [Batched Evaluation](batch-evaluation.md) for multi-rule optimization, [Rule Discovery](discovery.md) for automated rule extraction, [Rule Playground](playground.md) for sandbox testing, [Snapshots](snapshots.md) for versioned deployments, [Federation](federation.md) for hierarchical rule composition, [Maturity Model](maturity-model.md) for progressive enforcement, and [Remediation](remediation.md) for structured fix suggestions.

# Architecture

## System Overview

The Rule Repository is a monorepo with 10+ services orchestrated via Docker Compose:

| Component | Tech | Port | Purpose |
|---|---|---|---|
| Backend API | Python 3.13 + FastAPI | 8000 | REST, Evaluate, Intent, Gateway, Intelligence, Discovery, Feedback, Federation, Playground, Alerts, Snapshots APIs |
| MCP Server | Python 3.13 + FastMCP | 8001 | AI agent tool integration (MCP protocol, 6 tools) |
| Frontend | TypeScript + Next.js 15 | 3000 | Operator console (11 pages) |
| PostgreSQL | 17-alpine | 5432 | System of record (rules, revisions, audit log, 21 ORM models) |
| Elasticsearch | 8.17 | 9200 | Full-text + vector search |
| Neo4j | 5-community | 7474/7687 | Rule relationship graph |
| Redis | 7-alpine | 6379 | Job queue for arq background worker |
| arq worker | Python 3.13 + arq | -- | Background cron jobs (health scores, recommendations, correction stats) + alert generation |
| es-setup | curlimages/curl | -- | One-shot: creates ES index templates on startup |
| neo4j-setup | neo4j:5-community | -- | One-shot: applies Cypher constraints on startup |

---

## Server Module Map

```
src/rulerepo_server/
├── main.py                         # FastAPI app factory, router registration
├── api/
│   └── v1/                         # 13 API routers
│       ├── rules.py                #   CRUD, retire, revisions, relationships, graph
│       ├── search.py               #   fulltext, vector, hybrid, category, context
│       ├── evaluation.py           #   evaluate, quick, applicable-rules, get by ID
│       ├── extraction.py           #   document upload, extract, review
│       ├── intent.py               #   NL intent classification + routing
│       ├── intelligence.py         #   dashboard, health scores, analytics, recommendations
│       ├── relationships.py        #   create/delete rule relationships
│       ├── discovery.py            #   scan, candidates, approve/dismiss
│       ├── feedback.py             #   corrections, approve/dismiss, stats
│       ├── federation.py           #   federation CRUD, rules, effective-rules, diff
│       ├── playground.py           #   sandbox eval, test case CRUD, run, generate
│       ├── projects.py            #   project CRUD (create, list, get, update)
│       ├── alerts.py               #   list, get, acknowledge, resolve alerts
│       └── snapshots.py            #   snapshot CRUD, deploy, rollback, simulate, deployments
├── core/
│   ├── config.py                   # Settings (Pydantic BaseSettings)
│   ├── logging.py                  # structlog JSON logger
│   ├── errors.py                   # Exception hierarchy
│   ├── deps.py                     # FastAPI dependency providers
│   ├── llm.py                      # LLM model config (model IDs, thinking levels)
│   └── middleware.py               # RequestIdMiddleware
├── domain/                         # Pure domain models (no deps on project)
│   ├── rule.py                     # Rule, RuleRelationship, RuleRevision, EffectivePeriod
│   ├── evaluation.py               # EvaluationContext, FileChange, RuleVerdict, EvaluationResult
│   └── ...
├── services/
│   ├── rule_service.py             # Rule CRUD orchestration
│   ├── search.py                   # Search coordination (ES + PG hydration)
│   ├── intent.py                   # Intent classification via Gemini
│   ├── intent_prompts/             # Prompt templates for intent service
│   ├── evaluation/                 # 5-stage evaluation pipeline
│   │   ├── service.py              #   EvaluationService (orchestrator, accepts environment param)
│   │   ├── context_assembler.py    #   Stage 1: normalize inputs
│   │   ├── rule_selector.py        #   Stage 2: narrow rule corpus (supports environment + federation)
│   │   ├── graph_resolver.py       #   Stage 3: resolve Neo4j relationships (OVERRIDES/DEPENDS_ON)
│   │   ├── evaluation_core.py      #   Stage 4: LLM-as-Judge per rule (with LLM cache)
│   │   ├── conflict_aggregator.py  #   Stage 5a: conflict-aware aggregation
│   │   ├── verdict_aggregator.py   #   Stage 5b: simple aggregation (fallback)
│   │   ├── diff_parser.py          #   Unified diff parser (no deps, state machine)
│   │   ├── impact_preview.py       #   Rule change impact analysis (replay past evaluations)
│   │   └── prompts/                #   Evaluation prompt templates
│   ├── extraction/                 # Document ingestion + rule extraction
│   ├── intelligence/               # Health scoring, analytics (cache stats, top violations), recommendations
│   ├── context_delivery/           # Rule formatting for agent context injection
│   │   └── service.py              #   ContextDeliveryService
│   ├── discovery/                  # Automatic rule discovery from codebases
│   │   ├── service.py              #   DiscoveryService (scan orchestrator)
│   │   ├── github_importer.py      #   GitHub repo import (fetch files via Contents API)
│   │   ├── pattern_detector.py     #   Deduplication and scoring
│   │   ├── candidate_generator.py  #   Candidate rule generation
│   │   └── analyzers/              #   Source-specific analyzers
│   │       ├── base.py             #     DiscoveryContext, RawPattern
│   │       ├── claude_md.py        #     CLAUDE.md rule extraction
│   │       ├── code_patterns.py    #     Code convention detection
│   │       ├── linter_config.py    #     Linter config parsing
│   │       └── policy_document.py  #     Policy document rule extraction
│   ├── feedback/                   # Correction feedback loop
│   │   ├── service.py              #   FeedbackService (submit, approve, dismiss)
│   │   ├── capture.py              #   Correction capture (manual)
│   │   ├── pr_capture.py           #   Auto-capture corrections from merged PRs
│   │   └── correction_analyzer.py  #   Semantic delta analysis (new_rule/improve/adjust_scope)
│   ├── federation/                 # Cross-project rule federation
│   │   ├── service.py              #   FederationService
│   │   └── resolver.py             #   Effective rule resolution (ancestor walk + overrides)
│   ├── playground/                 # Rule sandbox testing framework
│   │   ├── service.py              #   PlaygroundService (sandbox eval, test case CRUD)
│   │   ├── test_generator.py       #   LLM-powered test case generation via Gemini
│   │   ├── test_runner.py          #   Run test suites against rules
│   │   └── prompts/                #   Prompt templates for playground
│   └── snapshots/                  # Rule set snapshots and deployments
│       ├── service.py              #   SnapshotService (create, deploy, rollback)
│       ├── serializer.py           #   Serialize/deserialize rule snapshots
│       └── simulator.py            #   Deployment impact simulation
├── adapters/
│   ├── postgres/
│   │   ├── session.py              # AsyncSession factory
│   │   ├── models.py               # 21 SQLAlchemy ORM models
│   │   ├── rule_repo.py            # PostgresRuleRepository
│   │   ├── audit_repo.py           # AuditLogRepository (append-only, hash-chained)
│   │   └── cache_repo.py           # LLM response cache
│   ├── elasticsearch/              # ES rule index, search client
│   ├── neo4j/                      # Graph driver, relationship operations
│   ├── gemini/                     # google-genai client wrapper
│   └── files/                      # Local file storage for uploads
├── mcp/
│   ├── server.py                   # FastMCP app factory
│   ├── tools.py                    # 6 MCP tools
│   ├── resources.py                # rule:// and ruleset:// resources
│   └── prompts.py                  # MCP prompt workflows
├── gateway/
│   └── router.py                   # Webhook ingestion, policy engine, normalizers
├── integrations/
│   └── github/                     # GitHub webhook receiver, signature verification
│       ├── router.py
│       ├── signature.py
│       └── review_formatter.py
├── workers/
│   ├── settings.py                 # arq WorkerSettings: 3 cron jobs with real implementations
│   └── tasks.py                    # On-demand task stubs (placeholder)
└── schemas/                        # Pydantic request/response models
    ├── rule.py
    ├── common.py
    ├── search.py
    ├── evaluation.py
    ├── extraction.py
    ├── intent.py
    ├── intelligence.py
    ├── discovery.py
    ├── feedback.py
    ├── federation.py
    ├── playground.py
    ├── alerts.py
    └── snapshots.py
```

### ORM Models (22 total in `adapters/postgres/models.py`)

| Model | Table | Purpose |
|---|---|---|
| `ProjectModel` | `projects` | Top-level organizational boundary |
| `RuleModel` | `rules` | Core rule storage (scoped by project_id) |
| `RuleRevisionModel` | `rule_revisions` | Rule change history |
| `RuleRelationshipModel` | `rule_relationships` | Directed relationships between rules |
| `AuditLogModel` | `audit_log` | Append-only audit trail with hash chaining |
| `DocumentModel` | `documents` | Uploaded source documents |
| `ExtractionModel` | `extractions` | LLM extraction results |
| `ApiKeyModel` | `api_keys` | API key management |
| `LLMCacheModel` | `llm_cache` | Cached LLM responses |
| `EnforcementPolicyModel` | `enforcement_policies` | Gateway webhook policies |
| `GatewayEvaluationModel` | `gateway_evaluations` | Gateway evaluation records |
| `DiscoveryScanModel` | `discovery_scans` | Rule discovery scan records |
| `DiscoveryCandidateModel` | `discovery_candidates` | Candidate rules from scans |
| `CorrectionModel` | `corrections` | Human correction feedback entries |
| `RuleFederationModel` | `rule_federations` | Federation hierarchy nodes |
| `RuleFederationMembershipModel` | `rule_federation_memberships` | Rule-to-federation assignments |
| `RuleTestCaseModel` | `rule_test_cases` | Playground test cases attached to rules |
| `AlertModel` | `alerts` | Alerts raised by intelligence workers |
| `RuleHealthScoreModel` | `rule_health_scores` | Persisted health score snapshots |
| `RuleRecommendationModel` | `rule_recommendations` | Improvement recommendations |
| `RuleSetSnapshotModel` | `rule_set_snapshots` | Immutable rule set snapshots |
| `RuleSetDeploymentModel` | `rule_set_deployments` | Snapshot-to-environment deployment tracking |

---

## Layering Rule

```
api/ --> services/ --> domain/ + adapters/
```

- `domain/` depends on **nothing else** in the project
- `services/` depends on `domain/` and `adapters/`
- `api/` depends on `services/`
- `mcp/`, `gateway/`, `integrations/` are parallel to `api/` -- they call services directly

Do not import upward. This layering is non-negotiable.

---

## Data Flows

### Rule Creation
```
User/API --> RuleService --> [Postgres INSERT] + [ES index] + [Neo4j node] + [Audit log]
```

### Code Evaluation (with environment support)
```
Diff/Files --> ContextAssembler --> RuleSelector(PG+ES, or snapshot if environment set) --> EvaluationCore(Gemini) --> VerdictAggregator --> AuditLog
```

When the `environment` parameter is provided, `RuleSelector` looks up the active deployment for that environment, deserializes its snapshot, and uses the snapshotted rules instead of querying the live corpus.

### Agent Context Delivery
```
Agent calls get_rules_for_context --> ContextDeliveryService --> ScopeRegistry(in-memory) --> RuleFormatter --> formatted text
```

### Webhook Enforcement
```
GitHub/Slack --> Gateway normalizer --> PolicyEngine match --> EvaluationService --> Actions (webhook/comment)
```

### Rule Discovery
```
File contents --> DiscoveryService.start_scan --> Analyzers (claude_md, linter_config, code_patterns) --> PatternDetector (dedup+score) --> CandidateGenerator --> DiscoveryCandidateModel (pending) --> approve/dismiss
```

### Correction Feedback
```
Human correction --> FeedbackService.submit_correction --> CorrectionAnalyzer (semantic delta) --> CorrectionModel --> approve (optional rule creation) / dismiss
```

### Federation Resolution
```
get_effective_rules(federation_id) --> FederationService --> Resolver walks ancestor chain --> Applies overrides --> Merged effective rule set
```

### Playground Sandbox Evaluation
```
Rule statement + sample input --> PlaygroundService.evaluate_sandbox --> Gemini LLM-as-Judge --> Verdict (no persistence, no audit log)
```

Test case flow:
```
Create/Generate test cases --> PlaygroundService or TestGenerator(Gemini) --> RuleTestCaseModel --> TestRunner evaluates each case --> TestRunResult (pass/fail per case)
```

### Snapshot Deploy
```
Create snapshot (captures current rules matching scope filter) --> RuleSetSnapshotModel --> Deploy to environment --> RuleSetDeploymentModel --> Evaluation uses snapshot rules when environment param set
```

### Alert Generation
```
Background worker (compute_health_scores) --> Rule health < 40 --> AlertModel (health_decline)
Background worker (compute_health_scores) --> Rule activity == 0 --> AlertModel (dormant_rule)
Background worker (generate_recommendations) --> Deny rate > 50% --> AlertModel (high_deny_rate)
```

---

## Data Stores

| Store | Role | Source of Truth? |
|---|---|---|
| PostgreSQL | Rules, revisions, audit log, documents, extractions, policies, discovery, feedback, federations, test cases, alerts, health scores, recommendations, snapshots, deployments | **Yes** |
| Elasticsearch | Search index (BM25 + dense_vector) | No -- derived from PG |
| Neo4j | Relationship graph (REFINES, OVERRIDES, etc.) | No -- derived from PG |
| Redis | arq job queue for background workers | No -- transient |

If Neo4j and Postgres disagree, **Postgres wins**. Use `scripts/reconcile_graph.py` to rebuild.

---

## Alembic Migrations

12 migrations in `apps/server/alembic/versions/`:

| Migration | Description |
|---|---|
| `001_initial_schema` | Rules, revisions, relationships, audit log, documents, extractions, api_keys |
| `002_add_llm_cache` | LLM response cache table |
| `003_add_intelligence_tables` | Health scores, recommendations, drift alerts |
| `004_add_gateway_tables` | Enforcement policies and gateway evaluations |
| `005_add_discovery_tables` | Scans and candidates for automatic rule discovery |
| `006_add_feedback_tables` | Corrections and clarity_score for correction feedback loop |
| `007_add_federation_tables` | Cross-project rule federation |
| `008_add_playground_tables` | Rule test cases for the playground testing framework |
| `009_add_alerts_table` | General-purpose alerts raised by intelligence workers |
| `010_add_snapshot_tables` | Rule set snapshots and deployments |
| `011_add_document_content_text` | Document content text storage for extraction |
| `012_add_projects` | Projects table + project_id FK on 7 resource tables |

---

## LLM Strategy

| Use Case | Model | Thinking Level |
|---|---|---|
| Search ranking, classification, extraction | `gemini-3-flash-preview` | `low` |
| Rule evaluation (LOW/MEDIUM severity) | `gemini-3-flash-preview` | `low`-`medium` |
| Rule evaluation (CRITICAL severity) | `gemini-3.1-pro-preview` | `high` |
| Rule extraction QC, conflict detection | `gemini-3.1-pro-preview` | `high` |

Temperature is always 1.0 (default). Never change it -- degrades Gemini 3 reasoning.

---

## Async Patterns

The API layer is fully async. All database calls use `sqlalchemy[asyncio]` with `asyncpg`. Elasticsearch uses the async client. Neo4j uses the official async driver. Gemini calls use the `google-genai` SDK.

Evaluation dispatches all per-rule LLM calls concurrently via `asyncio.gather()`. Failed tasks are logged and skipped; the aggregator works with whatever verdicts succeeded.

---

## Middleware Stack

The FastAPI application applies three middleware layers (outermost first):

1. **RequestIdMiddleware** -- generates or propagates `X-Request-ID` header for request tracing
2. **GZipMiddleware** -- compresses responses larger than 1000 bytes
3. **CORSMiddleware** -- configures cross-origin access, exposes `X-Request-ID`

---

## Health Checks

| Endpoint | Type | Description |
|---|---|---|
| `GET /healthz` | Liveness | Always returns `{"status": "ok"}` if the process is running |
| `GET /readyz` | Readiness | Checks PostgreSQL, Elasticsearch, Neo4j connectivity |
| `GET /api/v1/health` | API-level | Returns `{"status": "ok", "version": "v1"}` |

---

## Frontend Pages

The Next.js frontend has 12 pages under the `(dashboard)` route group:

| Route | Purpose |
|---|---|
| `/rules` | Browse and manage rules |
| `/search` | Full-text and filtered search |
| `/documents` | Upload documents, trigger extraction, review candidates |
| `/discover` | Rule discovery scans and candidate review |
| `/federations` | Cross-project federation management |
| `/feedback` | Correction feedback loop |
| `/intelligence` | Health scores, analytics, recommendations dashboard |
| `/gateway` | Webhook policies and gateway evaluations |
| `/integrations` | GitHub webhook setup |
| `/playground` | Sandbox rule evaluation and test case management |
| `/snapshots` | Rule set snapshots and deployment management |
| `/projects` | Project management (create, list, switch) |

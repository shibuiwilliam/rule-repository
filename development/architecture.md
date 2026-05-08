# Architecture

## System Overview

The Rule Repository is a monorepo with 12 services orchestrated via Docker Compose:

| Component | Tech | Port | Purpose |
|---|---|---|---|
| Backend API | Python 3.13 + FastAPI | 8000 | REST, Evaluate, Intent, Gateway, Intelligence, Discovery, Feedback, Federation, Playground, Alerts, Snapshots, Departments, Classification, Audit APIs |
| MCP Server | Python 3.13 + FastMCP | 8001 | AI agent tool integration (MCP protocol, 12+ tools) |
| Frontend | TypeScript + Next.js 15 | 3000 | Compliance dashboard + 30+ operator pages, persona-aware, English/Japanese i18n |
| PostgreSQL | 17-alpine | 5432 | System of record (rules, revisions, audit log, evaluations, departments, classifications, 35+ ORM models) with Row-Level Security |
| Elasticsearch | 8.17 | 9200 | Full-text + vector search with document-level security |
| Neo4j | 5-community | 7474/7687 | Rule relationship graph |
| Redis | 7-alpine | 6379 | Job queue for arq background worker |
| arq worker | Python 3.13 + arq | -- | Background cron jobs (health scores, recommendations, correction stats, rule promotion, verdict drift, conflict scanning, policy review cycle, weekly digest) + alert generation |
| Jaeger | 1.62 | 16686 | Distributed tracing via OpenTelemetry |
| Prometheus | v3.4 | 9090 | Metrics collection |
| es-setup | curlimages/curl | -- | One-shot: creates ES index templates on startup |
| neo4j-setup | neo4j:5-community | -- | One-shot: applies Cypher constraints on startup |

---

## Server Module Map

```
src/rulerepo_server/
├── main.py                         # FastAPI app factory, router registration
├── api/
│   └── v1/                         # 22 API routers
│       ├── rules.py                #   CRUD, retire, revisions, relationships, graph
│       ├── search.py               #   fulltext, vector, hybrid, category, context
│       ├── evaluation.py           #   evaluate, quick, applicable-rules, get by ID
│       ├── contract.py             #   contract clause evaluation
│       ├── event.py                #   business event evaluation
│       ├── extraction.py           #   document upload, extract, review
│       ├── intent.py               #   NL intent classification + routing
│       ├── intelligence.py         #   summary, dashboard, health scores, analytics, recommendations
│       ├── relationships.py        #   create/delete rule relationships
│       ├── discovery.py            #   scan, candidates, approve/dismiss
│       ├── feedback.py             #   corrections, approve/dismiss, stats
│       ├── federation.py           #   federation CRUD, rules, effective-rules, diff
│       ├── departments.py          #   department CRUD, capacity management
│       ├── playground.py           #   sandbox eval, test case CRUD, run, generate
│       ├── projects.py             #   project CRUD (create, list, get, update)
│       ├── alerts.py               #   list, get, acknowledge, resolve alerts
│       ├── snapshots.py            #   snapshot CRUD, deploy, rollback, simulate, deployments
│       ├── proposals.py            #   governance proposal lifecycle
│       ├── agent_governance.py     #   agent profiles, trust levels, personalized rules, mastery, exceptions, negotiations, sessions
│       ├── review.py               #   two-tier activity review (rough triage + detailed evaluation)
│       ├── audit.py                #   audit log entries with filters and hash-chain verification
│       └── marketplace.py          #   rule package CRUD, publishing, subscriptions, conflict resolution
├── core/
│   ├── config.py                   # Settings (Pydantic BaseSettings)
│   ├── logging.py                  # structlog JSON logger
│   ├── errors.py                   # Exception hierarchy
│   ├── deps.py                     # FastAPI dependency providers
│   ├── llm.py                      # LLM model config (model IDs, thinking levels)
│   ├── auth.py                     # Authentication & authorization (API key, roles)
│   ├── middleware.py               # RequestIdMiddleware
│   ├── telemetry.py                # OpenTelemetry instrumentation
│   ├── db_context.py               # with_user_context() for RLS session setup
│   ├── pii/                        # PII redaction
│   │   ├── redactor.py             #   PII masking in logs and outputs
│   │   └── tokenizer.py            #   Tokenization for sensitive data
│   └── tenancy/                    # Multi-tenant context
│       ├── context.py              #   TenantContext using contextvars
│       └── middleware.py            #   Request-scoped tenancy middleware
├── domain/                         # Pure domain models (no deps on project)
│   ├── rule.py                     # Rule, RuleRelationship, RuleRevision, EffectivePeriod
│   ├── subject.py                  # SubjectKind enum (8 kinds), Subject protocol
│   ├── department.py               # Department, DepartmentType, Capacity, RuleOwnership
│   ├── classification.py           # Classification enum (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED)
│   ├── evaluation.py               # EvaluationContext, FileChange, RuleVerdict, Remediation
│   ├── verdict.py                  # Verdict enum and helpers
│   ├── audit.py                    # AuditEntry, hash chaining
│   ├── contract.py                 # Contract domain model
│   ├── event_sequence.py           # Event sequence for workflows
│   ├── proposal.py                 # Proposal, ProposalStatus, ProposalVote
│   ├── agent.py                    # AgentProfile, TrustLevel, AgentSession
│   ├── revision.py                 # Revision tracking
│   └── federation.py               # Federation domain objects
├── services/
│   ├── rule_service.py             # Rule CRUD orchestration (PG + ES + Neo4j)
│   ├── search.py                   # Search coordination (ES + PG hydration + classification filter)
│   ├── intent.py                   # Intent classification via Gemini
│   ├── intent_prompts/             # Prompt templates for intent service
│   ├── project_service.py          # Project/workspace management
│   ├── evaluation/                 # Subject-polymorphic evaluation pipeline
│   │   ├── service.py              #   EvaluationService (subject-agnostic orchestrator)
│   │   ├── batch_evaluator.py      #   Batched multi-rule evaluation (single LLM call)
│   │   ├── evaluation_core.py      #   LLM-as-Judge per rule (subject-agnostic)
│   │   ├── context_assembler.py    #   Stage 1: normalize inputs
│   │   ├── rule_selector.py        #   Stage 2: narrow rule corpus
│   │   ├── graph_resolver.py       #   Stage 3: resolve Neo4j relationships
│   │   ├── conflict_aggregator.py  #   Stage 5a: conflict-aware aggregation
│   │   ├── verdict_aggregator.py   #   Stage 5b: simple aggregation (fallback)
│   │   ├── clause_aggregator.py    #   Clause-level verdict aggregation
│   │   ├── consensus.py            #   Multi-model consensus evaluation
│   │   ├── cost_tracker.py         #   LLM token consumption tracking
│   │   ├── idempotency.py          #   Deterministic evaluation results
│   │   ├── impact_preview.py       #   Rule change impact analysis
│   │   ├── diff_parser.py          #   Unified diff parser
│   │   ├── activity_review.py      #   Two-tier activity review
│   │   ├── subject_registry.py     #   @register(SubjectKind.X) dispatch
│   │   ├── subjects/               #   Per-domain Subject adapters
│   │   │   ├── code_diff_subject.py
│   │   │   ├── clause_set_subject.py
│   │   │   ├── event_subject.py
│   │   │   ├── transaction_subject.py
│   │   │   ├── creative_subject.py
│   │   │   ├── decision_subject.py
│   │   │   ├── identity_subject.py
│   │   │   └── document_subject.py
│   │   ├── adapters/               #   Input mode adapters
│   │   │   ├── registry.py
│   │   │   ├── business_event/
│   │   │   ├── code/
│   │   │   ├── communication/
│   │   │   ├── document_diff/
│   │   │   └── documentation/
│   │   └── prompts/                #   Evaluation prompt templates
│   ├── extraction/                 # Document ingestion + rule extraction
│   │   ├── pipeline.py             #   Main extraction orchestrator
│   │   ├── legal_pipeline.py       #   Legal document-specific pipeline
│   │   ├── pdf_sanitizer.py        #   PDF content cleaning
│   │   └── contract/               #   Contract-specific extraction
│   │       ├── clause_classifier.py
│   │       ├── clause_segmenter.py
│   │       └── reference_resolver.py
│   ├── intelligence/               # Health scoring, analytics, recommendations
│   │   ├── service.py
│   │   ├── health_scorer.py
│   │   ├── analytics.py
│   │   ├── effectiveness.py
│   │   ├── agent_analytics.py
│   │   ├── recommender.py
│   │   └── digest.py               #   Weekly digest (department-aware)
│   ├── context_delivery/           # Rule formatting for agent context
│   │   ├── service.py
│   │   ├── scope_registry.py
│   │   └── formatter.py
│   ├── discovery/                  # Automatic rule discovery
│   │   ├── service.py
│   │   ├── github_importer.py
│   │   ├── pattern_detector.py
│   │   ├── candidate_generator.py
│   │   ├── analyzers/              #   Source-specific analyzers
│   │   │   ├── claude_md.py
│   │   │   ├── code_patterns.py
│   │   │   ├── linter_config.py
│   │   │   └── policy_document.py
│   │   ├── connectors/             #   External source connectors
│   │   │   ├── confluence.py
│   │   │   ├── notion.py
│   │   │   ├── google_drive.py
│   │   │   ├── sharepoint.py
│   │   │   ├── egov.py
│   │   │   └── eurlex.py
│   │   └── sources/                #   Specialized source handlers
│   │       ├── contract_docx.py
│   │       ├── policy_handbook.py
│   │       └── regulation_pdf.py
│   ├── feedback/                   # Correction feedback loop
│   │   ├── service.py
│   │   ├── capture.py
│   │   ├── pr_capture.py
│   │   ├── correction_analyzer.py
│   │   └── auto_drafter.py         #   Subject-aware auto-drafting
│   ├── departments/                # Department/Capacity service
│   │   └── service.py              #   resolve_owner, resolve_approvers, resolve_audience
│   ├── classification/             # Classification enforcement
│   │   └── es_filter.py            #   Elasticsearch classification filter
│   ├── federation/                 # Cross-project rule federation
│   │   ├── service.py
│   │   └── resolver.py
│   ├── playground/                 # Rule sandbox testing
│   │   ├── service.py
│   │   ├── test_generator.py
│   │   ├── test_runner.py
│   │   └── counterexample_generator.py
│   ├── provenance/                 # Rule provenance
│   │   └── lineage_resolver.py
│   ├── snapshots/                  # Rule set snapshots
│   │   ├── service.py
│   │   ├── serializer.py
│   │   └── simulator.py
│   ├── proposals/                  # Governance proposals
│   │   ├── service.py
│   │   └── enactor.py
│   └── agent_governance/           # Agent trust and governance
│       └── service.py
├── adapters/
│   ├── postgres/
│   │   ├── session.py              # AsyncSession factory
│   │   ├── models.py               # 35+ SQLAlchemy ORM models
│   │   ├── rule_repo.py            # PostgresRuleRepository
│   │   ├── audit_repo.py           # AuditLogRepository (append-only, hash-chained)
│   │   └── cache_repo.py           # LLM response cache
│   ├── elasticsearch/              # ES rule/document index, search client
│   ├── neo4j/                      # Graph driver, relationship operations
│   ├── gemini/                     # google-genai client wrapper
│   │   ├── client.py
│   │   ├── documents.py
│   │   └── embeddings.py
│   ├── llm/                        # Pluggable LLM providers
│   │   ├── base.py                 #   LLMProvider Protocol
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   └── local.py
│   ├── files/                      # Local file storage for uploads
│   ├── contract_parser.py          # Contract parsing and structure extraction
│   └── contract_compare.py         # Contract diff and comparison
├── mcp/
│   ├── server.py                   # FastMCP app factory
│   ├── tools.py                    # 12+ MCP tools (clearance-filtered)
│   ├── resources.py                # rule:// and ruleset:// resources
│   └── prompts.py                  # MCP prompt workflows
├── gateway/
│   ├── router.py                   # Webhook ingestion, policy engine
│   ├── policy_engine.py
│   ├── schemas.py
│   ├── actions/webhook_out.py
│   └── normalizers/                # Event normalization
│       ├── github.py
│       ├── slack.py
│       ├── teams.py
│       ├── email.py
│       └── generic.py
├── integrations/
│   └── github/                     # GitHub webhook receiver
│       ├── router.py
│       ├── signature.py
│       └── review_formatter.py
├── workers/
│   ├── settings.py                 # arq WorkerSettings: 9+ cron jobs
│   ├── tasks.py                    # On-demand async tasks
│   ├── policy_review_cycle.py      # Policy review alerting
│   ├── conflict_scanner.py         # Background conflict detection
│   ├── verdict_drift.py            # Verdict drift monitoring
│   ├── polyglot_validator.py       # Multi-language validation
│   └── archival.py                 # Rule archival and retention
└── schemas/                        # Pydantic request/response models
    ├── rule.py, common.py, search.py, evaluation.py, extraction.py
    ├── intent.py, intelligence.py, discovery.py, feedback.py
    ├── federation.py, playground.py, alerts.py, snapshots.py
    ├── proposals.py, agent_governance.py, contract.py
    ├── department.py, event.py, review.py, audit.py, project.py
```

### ORM Models (35+ total in `adapters/postgres/models.py`)

| Model | Table | Purpose |
|---|---|---|
| `TenantModel` | `tenants` | Multi-tenant isolation |
| `ProjectModel` | `projects` | Top-level organizational boundary |
| `RuleModel` | `rules` | Core rule storage (scoped by project_id, with classification + subject_kinds) |
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
| `EvaluationRecordModel` | `evaluations` | Persistent per-rule evaluation records |
| `DraftRuleProposalModel` | `draft_rule_proposals` | Correction-to-rule flywheel proposals |
| `ProposalModel` | `proposals` | Governance proposal lifecycle |
| `ProposalCommentModel` | `proposal_comments` | Comments on governance proposals |
| `NotificationModel` | `notifications` | User notifications for proposals and actions |
| `AgentProfileModel` | `agent_profiles` | Registered agent identities and trust levels |
| `AgentExceptionRequestModel` | `agent_exception_requests` | Agent requests for rule exceptions |
| `AgentNegotiationModel` | `agent_negotiations` | Agent-initiated rule negotiations |
| `GovernanceSessionModel` | `governance_sessions` | Agent governance session tracking |

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

## Subject Polymorphism

The evaluation engine is subject-agnostic. Eight subject kinds are dispatched via `@register(SubjectKind.X)` decorators:

| SubjectKind | Adapter | Domain |
|---|---|---|
| `CODE_DIFF` | `code_diff_subject.py` | Engineering (code changes) |
| `CLAUSE_SET` | `clause_set_subject.py` | Legal (contract clauses) |
| `EVENT` | `event_subject.py` | HR / Operations (business events) |
| `TRANSACTION` | `transaction_subject.py` | Finance (expenses, purchases) |
| `CREATIVE` | `creative_subject.py` | Marketing (ad copy, creatives) |
| `DECISION` | `decision_subject.py` | Management (approvals, exceptions) |
| `IDENTITY` | `identity_subject.py` | Compliance (KYC, screening) |
| `DOCUMENT` | `document_subject.py` | General (policy documents) |

The orchestrator (`service.py`, `evaluation_core.py`) never branches on `subject.kind`. All domain logic lives in the adapters.

---

## Data Flows

### Rule Creation
```
User/API --> RuleService --> [Postgres INSERT] + [ES index] + [Neo4j node] + [Audit log]
```

### Code Evaluation (with environment support)
```
Diff/Files --> ContextAssembler --> RuleSelector(PG+ES, or snapshot if environment set) --> SubjectRegistry.resolve(kind) --> EvaluationCore(Gemini) --> VerdictAggregator --> AuditLog
```

When the `environment` parameter is provided, `RuleSelector` looks up the active deployment for that environment, deserializes its snapshot, and uses the snapshotted rules instead of querying the live corpus.

### Agent Context Delivery
```
Agent calls get_rules_for_context --> ContextDeliveryService --> ScopeRegistry(in-memory) --> ClassificationFilter --> RuleFormatter --> formatted text
```

### Webhook Enforcement
```
GitHub/Slack --> Gateway normalizer --> PolicyEngine match --> EvaluationService --> Actions (webhook/comment)
```

### Rule Discovery
```
File contents --> DiscoveryService.start_scan --> Analyzers (claude_md, linter_config, code_patterns, policy_document, connectors) --> PatternDetector (dedup+score) --> CandidateGenerator --> DiscoveryCandidateModel (pending) --> approve/dismiss
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

### Snapshot Deploy
```
Create snapshot (captures current rules matching scope filter) --> RuleSetSnapshotModel --> Deploy to environment --> RuleSetDeploymentModel --> Evaluation uses snapshot rules when environment param set
```

### Alert Generation
```
Background worker (compute_health_scores) --> Rule health < 40 --> AlertModel (health_decline)
Background worker (compute_health_scores) --> Rule activity == 0 --> AlertModel (dormant_rule)
Background worker (generate_recommendations) --> Deny rate > 50% --> AlertModel (high_deny_rate)
Background worker (conflict_scanner) --> Conflict detected --> AlertModel (conflict)
Background worker (policy_review_cycle) --> Rule overdue for review --> AlertModel (review_due)
```

---

## Data Stores

| Store | Role | Source of Truth? |
|---|---|---|
| PostgreSQL | Rules, revisions, audit log, documents, extractions, policies, evaluations, departments, classifications, proposals, agent profiles, snapshots, federations, and cache | **Yes** |
| Elasticsearch | Search index (BM25 + dense_vector) with document-level security | No -- derived from PG |
| Neo4j | Relationship graph (REFINES, OVERRIDES, CONFLICTS_WITH, DEPENDS_ON, DERIVES_FROM, SUCCEEDS, LOCALIZES) | No -- derived from PG |
| Redis | arq job queue for background workers | No -- transient |

If Neo4j and Postgres disagree, **Postgres wins**. Use `scripts/reconcile_graph.py` to rebuild.

---

## Alembic Migrations

26 migrations in `apps/server/alembic/versions/` (001-026, skipping 020):

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
| `013_update_corrections_table` | Additional columns on corrections table |
| `014_add_evaluations_table` | Persistent per-rule evaluation records |
| `015_add_maturity_level` | Rule maturity model: maturity_level + accuracy tracking |
| `016_add_draft_proposals` | Draft rule proposals for correction-to-rule flywheel |
| `017_add_agent_id_to_evaluations` | Agent identity tracking on evaluation records |
| `018_add_proposals` | Governance proposals, proposal comments, and notifications tables |
| `019_add_agent_governance` | Agent profiles, exception requests, negotiations, governance sessions |
| `021_add_rule_context` | Context column on rules for document provenance |
| `022_add_rule_examples` | Following/violation examples on rules for evaluation accuracy |
| `023_add_sensitivity_and_context_encrypted` | Sensitivity classification and encrypted context fields |
| `024_add_tenant_cost_polyglot` | Multi-tenancy, cost tracking, and polyglot validation fields |
| `025_add_regulatory_severity` | Regulatory severity field for compliance-domain rules |
| `026_add_subject_jurisdiction_fields` | Subject type and jurisdiction fields (Phase 7) |

---

## LLM Strategy

| Use Case | Model | Thinking Level |
|---|---|---|
| Search ranking, classification, extraction | `gemini-3-flash-preview` | `low` |
| Rule evaluation (LOW/MEDIUM severity) | `gemini-3-flash-preview` | `low`-`medium` |
| Rule evaluation (CRITICAL severity) | `gemini-3.1-pro-preview` | `high` |
| Rule extraction QC, conflict detection | `gemini-3.1-pro-preview` | `high` |

Temperature is always 1.0 (default). Never change it -- degrades Gemini 3 reasoning.

LLM provider is pluggable via `adapters/llm/base.py` (`LLMProvider` Protocol). Gemini is the default; Anthropic, OpenAI, and self-hosted implementations are planned.

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

The Next.js frontend has 30+ pages (including nested routes and domain-specific surfaces):

| Route | Purpose |
|---|---|
| `/` | Home dashboard (compliance rate, trends, pending actions, department-aware) |
| `/rules` | Browse and manage rules |
| `/rules/new` | Create a new rule (statement, conditions, examples) |
| `/rules/[id]` | Rule detail (context, conditions, examples, relationships, graph, effectiveness) |
| `/search` | Full-text, vector, and hybrid search with classification filtering |
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
| `/proposals` | Governance proposal lifecycle and voting |
| `/proposals/new` | Create new governance proposal (wizard) |
| `/proposals/[id]` | Proposal detail (diff, comments, votes, impact) |
| `/notifications` | Notification inbox for proposal activity |
| `/agents` | Agent compliance leaderboard and trust levels |
| `/agents/[id]` | Agent detail (mastery, exceptions, negotiations) |
| `/review` | Two-tier activity review (rough triage + detailed LLM evaluation) |
| `/audit` | Immutable audit log with hash-chain verification |
| `/tutor` | Conversational Q&A about rules with LLM-powered explanations |
| `/marketplace` | Rule package browsing, subscriptions, and publishing |
| `/onboarding` | Setup wizard for new users |
| `/contracts/review/[id]` | Legal: clause-by-clause verdict view |
| `/events/[id]` | HR: event submission with applicable rules |
| `/transactions/[id]` | Finance: transaction compliance review |
| `/creatives/review/[id]` | Marketing: creative compliance review |

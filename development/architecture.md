# Architecture

## System Overview

The Rule Repository is a monorepo with 10 services orchestrated via Docker Compose (Tier 3):

| Component | Tech | Port | Purpose |
|---|---|---|---|
| Backend API | Python 3.13 + FastAPI | 8000 | 40 API routers covering rules, evaluation, search, discovery, governance, compliance, and more |
| MCP Server | Python 3.13 + FastMCP | 8001 | AI agent tool integration (MCP protocol, 24 tools) |
| Frontend | TypeScript + Next.js 15 | 3000 | Operator console with 61 pages across 9 persona route groups, English/Japanese i18n |
| PostgreSQL | 17-alpine | 5432 | System of record (37 ORM models, 37 migrations) with Row-Level Security |
| Elasticsearch | 8.17 | 9200 | Full-text + vector search with document-level security |
| Neo4j | 5-community | 7474/7687 | Rule relationship graph |
| Redis | 7-alpine | 6379 | Job queue for arq background worker |
| arq worker | Python 3.13 + arq | -- | 9 scheduled cron jobs + on-demand tasks |
| es-setup | curlimages/curl | -- | One-shot: creates ES index templates on startup |
| neo4j-setup | neo4j:5-community | -- | One-shot: applies Cypher constraints on startup |

---

## Server Module Map

```
src/rulerepo_server/
├── main.py                         # FastAPI app factory, router registration
├── api/
│   └── v1/                         # 40 API routers
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
│       ├── approval_workflows.py   #   per-scope approval workflows (RR-021)
│       ├── ask.py                  #   conversational assistant (RR-005)
│       ├── attestation.py          #   attestation campaigns (RR-014)
│       ├── compliance.py           #   compliance workflows (RR-011,015)
│       ├── cost.py                 #   LLM cost tracking (RR-027)
│       ├── facts.py                #   fact store queries (RR-003)
│       ├── operability.py          #   health, DR endpoints (RR-028)
│       ├── regulatory.py           #   regulatory source management (RR-012)
│       ├── risks.py                #   risk register (RR-019)
│       ├── scim.py                 #   SCIM 2.0 protocol (RR-007)
│       ├── submissions.py          #   universal submissions intake (any EvaluationSubject kind)
│       ├── tenants.py              #   tenant management (RR-007)
│       ├── translations.py         #   polyglot translation management (RR-020)
│       ├── upcoming_changes.py     #   scheduled rule changes (RR-036)
│       ├── lineage.py              #   norm lineage upstream/downstream
│       ├── assistant.py            #   conversational assistant (Phase 7g)
│       ├── cockpit.py              #   compliance cockpit dashboard (Phase 7h)
│       ├── events_ingest.py        #   universal business event ingestion (Phase 7e)
│       └── onboarding.py           #   guided onboarding wizard
├── core/
│   ├── config.py                   # Settings (Pydantic BaseSettings)
│   ├── logging.py                  # structlog JSON logger
│   ├── errors.py                   # Exception hierarchy
│   ├── deps.py                     # FastAPI dependency providers
│   ├── llm.py                      # LLM model config (model IDs, thinking levels)
│   ├── auth.py                     # Authentication & authorization (API key, roles)
│   ├── middleware.py               # RequestIdMiddleware
│   ├── db_context.py               # with_user_context() for RLS session setup
│   ├── pii/                        # PII redaction
│   │   ├── redactor.py             #   PII masking in logs and outputs
│   │   └── tokenizer.py            #   Tokenization for sensitive data
│   └── tenancy/                    # Multi-tenant context
│       ├── context.py              #   TenantContext using contextvars
│       └── middleware.py            #   Request-scoped tenancy middleware
├── domain/                         # Pure domain models (25 files, no deps on project)
│   ├── rule.py                     # Rule, RuleRelationship, RuleRevision, EffectivePeriod
│   ├── subject.py                  # SubjectKind enum (8 kinds), Subject protocol
│   ├── department.py               # Department, DepartmentType, Capacity, RuleOwnership
│   ├── classification.py           # Classification enum (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED)
│   ├── evaluation.py               # EvaluationContext, FileChange, RuleVerdict, Surface enum
│   ├── verdict.py                  # Verdict enum and helpers
│   ├── remediation.py              # RemediationKind enum, polymorphic Remediation
│   ├── audit.py                    # AuditEntry, hash chaining
│   ├── business_event.py           # BusinessEvent, ActorRef, event-type-to-scope mapping
│   ├── contract.py                 # Contract domain model
│   ├── event_sequence.py           # Event sequence for temporal evaluation modes
│   ├── tenant.py                   # Tenant, Organization, Principal, Role (multi-tenancy)
│   ├── proposal.py                 # Proposal, ProposalStatus, ProposalVote
│   ├── agent.py                    # AgentProfile, TrustLevel, AgentSession
│   ├── revision.py                 # Revision tracking
│   ├── federation.py               # Federation domain objects
│   ├── abac.py                     # Attribute-Based Access Control
│   ├── applies_to.py               # AppliesTo model (artifact_type, triggering_events)
│   ├── evaluable.py                # Evaluable abstraction for non-diff artifacts
│   ├── attestation.py              # Attestation campaigns
│   ├── fact.py                     # Fact store entries
│   ├── regulatory.py               # Regulatory source tracking
│   ├── risk.py                     # Risk register
│   ├── scope.py                    # Structured scope with dimensions
│   └── translation.py              # Polyglot rule translations
├── services/
│   ├── rule_service.py             # Rule CRUD orchestration (PG + ES + Neo4j)
│   ├── search.py                   # Search coordination (ES + PG hydration + classification filter)
│   ├── intent.py                   # Intent classification via Gemini
│   ├── intent_prompts/             # Prompt templates for intent service
│   ├── project_service.py          # Project/workspace management
│   ├── evaluation/                 # Subject-polymorphic evaluation pipeline
│   │   ├── service.py              #   EvaluationService (subject-agnostic orchestrator)
│   │   ├── batch_evaluator.py      #   Batched multi-rule evaluation (kind-aware dispatch → LLM)
│   │   ├── kind_dispatch.py        #   Kind-based routing (normative→LLM, computational→deterministic, etc.)
│   │   ├── deterministic/          #   Hybrid eval: deterministic constraint layer (Proposal 9)
│   │   │   ├── constraint.py       #     NumericConstraint, DateConstraint, EnumConstraint, Operator
│   │   │   └── evaluator.py        #     DeterministicEvaluator (runs before LLM, PASS/FAIL skip LLM)
│   │   ├── evaluation_core.py      #   LLM-as-Judge per rule (subject-agnostic)
│   │   ├── context_assembler.py    #   Stage 1: normalize inputs
│   │   ├── rule_selector.py        #   Stage 2: narrow rule corpus (structured scope + dimension scoring)
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
│   │   ├── prompts/                #   Evaluation prompt templates
│   │   └── surfaces/              #   Surface abstraction (Phase 10+)
│   │       ├── base.py             #     SurfaceAdapter ABC, EvaluationSubjectPayload
│   │       ├── code/               #     Code surface (diffs, file changes)
│   │       ├── contract/           #     Contract surface (clauses, NDAs)
│   │       ├── document/           #     Document surface (policies, handbooks)
│   │       ├── generic/            #     Generic surface (free-form facts)
│   │       ├── human_action/       #     Human action surface (overtime, leave)
│   │       ├── message/            #     Message surface (email, Slack, Teams)
│   │       └── transaction/        #     Transaction surface (expenses, invoices)
│   ├── norm_lineage/               # Norm derivation chain traversal
│   │   └── walker.py               #   upstream/downstream DERIVES_FROM walks
│   ├── extraction/                 # Document ingestion + rule extraction
│   │   ├── pipeline.py             #   Main extraction orchestrator
│   │   ├── legal_pipeline.py       #   Legal document-specific pipeline
│   │   ├── pdf_sanitizer.py        #   PDF content cleaning
│   │   ├── clause_normalizer.py    #   Normalize clause text
│   │   ├── redline_differ.py       #   Contract version diffing
│   │   ├── bilingual_pairer.py     #   Match translated rule pairs
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
│   ├── agent_governance/           # Agent trust and governance
│   │   └── service.py
│   ├── domains/                    # Domain modules (RR-002,008,009,016,017,018)
│   │   ├── _protocol.py            #   DomainModule interface
│   │   ├── _base_evaluator.py      #   BaseDomainEvaluator (LLM router wiring)
│   │   ├── __init__.py              #   Domain registry
│   │   ├── engineering/             #   Code evaluation domain
│   │   ├── legal/                   #   Contract/clause evaluation domain
│   │   ├── hr/                      #   HR event/form evaluation domain
│   │   ├── finance/                 #   Financial transaction domain
│   │   ├── it_security/             #   IaC/vulnerability domain
│   │   ├── sales/                   #   Discount/quote/ad-copy domain
│   │   ├── communications/          #   Email/Slack/Teams message domain
│   │   └── governance/              #   Disclosure/board-minutes/ESG domain
│   ├── fact_store/                 # External fact resolution (RR-003)
│   │   ├── service.py, cache.py, registry.py
│   │   └── providers/              #   employee_attributes, ofac_sanctions, regulatory_feed, internal_master_data
│   ├── compliance/                 # Regulatory compliance (RR-011,015)
│   │   ├── approval_policy.py, erasure.py, cmek.py, read_access_log.py, regional_routing.py
│   │   └── ...
│   ├── operability/                # Operational monitoring (RR-025,026,028)
│   │   ├── health.py, cost_tracker.py, llm_fallback.py, dr_runbook.py, leader_election.py
│   │   └── ...
│   ├── identity/                   # User/tenant management (RR-007)
│   │   ├── scim.py, service.py
│   │   └── ...
│   ├── regulatory/                 # Regulation tracking (RR-012)
│   │   └── service.py
│   ├── risk/                       # Risk register (RR-019)
│   │   └── service.py
│   ├── approval/                   # Per-scope approval workflows (RR-021)
│   │   └── service.py
│   ├── attestation/                # Attestation campaigns (RR-014)
│   │   └── service.py
│   └── translation/                # Polyglot rule management (RR-020)
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
│   ├── llm/                        # Pluggable LLM providers (RR-010)
│   │   ├── base.py                 #   LLMProvider Protocol
│   │   ├── router.py               #   LLM provider router with fallback chain
│   │   ├── gemini.py               #   Google Gemini integration
│   │   ├── anthropic.py            #   Anthropic Claude
│   │   ├── openai.py               #   OpenAI
│   │   └── local.py                #   Self-hosted LLM
│   ├── graph/                      # Tier 1 graph fallback
│   │   └── postgres_adjacency.py   #   Neo4j fallback using Postgres adjacency tables
│   ├── search/                     # Tier 1 search fallback
│   │   └── postgres_fts.py         #   ES fallback using Postgres full-text search
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
│   ├── settings.py                 # arq WorkerSettings: 9 cron jobs + on-demand tasks
│   ├── tasks.py                    # On-demand async tasks
│   ├── policy_review_cycle.py      # Policy review alerting
│   ├── conflict_scanner.py         # Background conflict detection
│   ├── verdict_drift.py            # Verdict drift monitoring
│   ├── polyglot_validator.py       # Multi-language validation
│   ├── archival.py                 # Rule archival and retention
│   ├── norm_lineage_propagation.py # Propagate norm changes downstream
│   └── translation_drift.py       # Detect translation locale drift
├── domain_packs/                   # Bundled rule packs per domain (6 packs)
│   ├── communication/              #   Communications policy pack
│   ├── engineering/                #   Engineering rules pack
│   ├── finance/                    #   Finance expense/invoice pack
│   ├── hr/                         #   HR attendance/leave pack
│   ├── legal/                      #   Legal/regulatory pack
│   └── sales/                      #   Sales/pricing pack
└── schemas/                        # Pydantic request/response models
    ├── rule.py, common.py, search.py, evaluation.py, extraction.py
    ├── intent.py, intelligence.py, discovery.py, feedback.py
    ├── federation.py, playground.py, alerts.py, snapshots.py
    ├── proposals.py, agent_governance.py, contract.py
    ├── department.py, event.py, review.py, audit.py, project.py
```

### ORM Models (37 total in `adapters/postgres/models.py`)

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
| `DepartmentModel` | `departments` | Department definitions and metadata (Phase 7) |
| `CapacityAssignmentModel` | `capacity_assignments` | User-to-department capacity assignments (Phase 7) |
| `RuleOwnershipModel` | `rule_ownerships` | Rule-to-department ownership mappings (Phase 7) |
| `RuleTranslationModel` | `rule_translations` | Multilingual rule translations (post-Phase 8) |
| `EvaluationDailyAggModel` | `evaluation_daily_agg` | Daily aggregated evaluation statistics |

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

## Plugin Architecture

Domain-specific evaluators, extractors, and feedback handlers are organized as plugins under `plugins/`. Each plugin implements a base protocol (`plugins/base.py`) and registers itself with `plugins/_registry.py`.

```
plugins/
├── _registry.py         # Plugin registration and lookup
├── base.py              # Plugin protocol (evaluators, extractors, feedback)
├── engineering/          # Code-aware evaluation
│   ├── evaluators/code_change.py
│   ├── extractors/claude_md.py, linter_config.py
│   └── feedback/pr_capture.py
├── legal/               # Contract and clause evaluation
│   ├── evaluators/document_evaluator.py
│   └── extractors/clause_extractor.py
├── hr/                  # HR form and event evaluation
│   ├── evaluators/form_evaluator.py
│   └── extractors/handbook.py
├── finance/             # Transaction evaluation
│   └── evaluators/transaction_evaluator.py
└── marketing/           # Content and creative evaluation
    └── evaluators/content_evaluator.py
```

**Layering**: Plugins consume core services. The core never imports from any plugin. Each plugin owns its prompt templates under a `prompts/` subdirectory.

---

## Phase 8 Domain Engines

### Contract Clause Engine

```
Contract (DOCX/PDF/text) --> ContractParser (adapters/) --> ClauseSetSubject --> EvaluationService --> ClauseAggregator --> ContractEvaluateResponse
                                                       --> ContractComparator (adapters/) --> ComparisonResult
```

Components:
- `adapters/contract_parser.py` — DOCX via python-docx, PDF via Gemini Files API, text direct
- `adapters/contract_compare.py` — semantic clause-level diffing with similarity scoring
- `services/evaluation/clause_aggregator.py` — clause-by-clause verdicts collapse to contract-level
- `api/v1/contract.py` — `POST /api/v1/evaluate/contract` with review types: self_conformance, cross_contract, regulatory_compliance, risk_scoring
- Prompt templates: `services/evaluation/prompts/clause_set/`

### Event Engine with Temporal Modes

```
Event + SequenceContext --> EventSubject --> EvaluationService --> EvaluateResponse
```

Three evaluation modes:
- **single** — evaluate event alone (default)
- **sequence** — monthly event window with accumulations
- **calendar** — annual aggregates (YTD overtime, 36-Agreement status)

Components:
- `domain/event_sequence.py` — `EventEvaluationMode`, `EventRecord`, `EventWindow`, `CalendarContext`, `SequenceContext`
- `api/v1/event.py` — `POST /api/v1/evaluate/event` with `evaluation_mode` parameter
- Prompt templates: `services/evaluation/prompts/event/`

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
File contents --> DiscoveryService.start_scan --> Analyzers (claude_md, linter_config, code_patterns, policy_document) --> PatternDetector (dedup+score) --> CandidateGenerator --> DiscoveryCandidateModel (pending) --> approve/dismiss
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

### Contract Clause Evaluation
```
Contract body --> api/v1/contract.py --> ContractParser --> ClauseSetSubject --> EvaluationService.evaluate(subject_kind=CLAUSE_SET) --> ClauseAggregator --> ContractEvaluateResponse (contract verdict + per-clause verdicts)
```

### Event Evaluation (with temporal context)
```
Event facts + optional SequenceContext --> api/v1/event.py --> EventSubject (with mode: single|sequence|calendar) --> EvaluationService.evaluate(subject_kind=EVENT) --> EvaluateResponse
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

## Tier 1 Infrastructure (Postgres-only)

The system supports **three deployment tiers** (RR-001):

| Tier | Services | Use Case |
|---|---|---|
| **Tier 1** | Postgres only | Minimal deployments, dev machines, CI |
| **Tier 2** | Postgres + Elasticsearch | Search-heavy workloads without graph |
| **Tier 3** | Postgres + Elasticsearch + Neo4j + Redis | Full production stack |

Feature flags control degradation: `ELASTICSEARCH_ENABLED`, `NEO4J_ENABLED`, `REDIS_ENABLED`.

Fallback adapters:
- Elasticsearch → `adapters/search/postgres_fts.py` (Postgres `tsvector` + `pgvector`)
- Neo4j → `adapters/graph/postgres_adjacency.py` (recursive CTEs)
- Redis → APScheduler in-process

Docker Compose files:
- `infra/compose/tier1.yml` — Postgres only
- `infra/compose/tier2.yml` — Postgres + Elasticsearch
- `infra/compose/tier3.yml` — Full stack (default)

---

## Alembic Migrations

37 migrations in `apps/server/alembic/versions/` (001-038, skipping 020):

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
| `027_rename_subject_kinds` | Rename SubjectType to SubjectKind alignment |
| `028_add_departments_capacities` | Departments, capacity assignments, rule ownerships |
| `029_add_classification_column` | Classification column on rules, evaluations, audit_log |
| `030_add_surface_aware_rule_fields` | Surface-aware fields on rules (norm_tier, norm_authority, etc.) |
| `031_add_surface_aware_evaluation_fields` | Surface-aware fields on evaluations |
| `032_backfill_applicable_subject_types` | Backfill subject type support on existing rules |
| `033_backfill_structured_scope` | Hierarchical structured scope backfill |
| `034_add_rule_kind_column` | Rule kind discriminator (normative/computational/procedural/definitional/principle) |
| `035_add_constraints_column` | Deterministic evaluation constraints (JSONB) |
| `036_create_rule_translations_table` | Multilingual rule translations table |
| `037_move_frozen_tables_to_schema` | Move frozen feature tables to `frozen` schema |
| `038_add_structured_scope_gin_indexes` | GIN indexes on `scope_structured` JSONB for fast multi-axis scope queries |

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

The Next.js frontend has 61 pages across 9 persona route groups (including nested routes and domain-specific surfaces):

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
| `/onboarding` | Setup wizard for new users |
| `/contracts/review/[id]` | Legal: clause-by-clause verdict view |
| `/events/[id]` | HR: event submission with applicable rules |
| `/transactions/[id]` | Finance: transaction compliance review |
| `/creatives/review/[id]` | Marketing: creative compliance review |
| `/admin` | Admin: system dashboard, tenant/user management |
| `/admin/tenants` | Admin: tenant management |
| `/admin/users` | Admin: user management |
| `/compliance` | Compliance: cross-domain compliance dashboard |
| `/compliance/bundles` | Compliance: rule bundles |
| `/compliance/audit-packets` | Compliance: audit packet viewer |
| `/compliance/exceptions` | Compliance: exception tracking |
| `/compliance/regulatory` | Compliance: regulatory feed |
| `/sales` | Sales: sales dashboard |
| `/security` | Security: security dashboard |
| `/marketing` | Marketing: marketing dashboard |
| `/marketing/creative-reviews` | Marketing: creative submission reviews |
| `/marketing/guidelines` | Marketing: brand guidelines |

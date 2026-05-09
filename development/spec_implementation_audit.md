# Spec Implementation Audit

> Generated: 2026-05-06 10:16:15 UTC
> Method: code-only heuristic (file existence, pattern matching)
> Source docs: PROJECT.md, CLAUDE.md

## Summary

| Status | Count | % |
|--------|-------|---|
| IMPLEMENTED | 165 | 98.8% |
| PARTIAL | 2 | 1.2% |
| PLANNED | 0 | 0.0% |
| MISSING | 0 | 0.0% |
| **Total** | **167** | |

## Detailed Breakdown

### Agent Governance

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Agent profile registration | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/register", response_model=AgentProfileResponse, status_code=201); async def register_agent( |
| Agent trust levels | IMPLEMENTED | IMPLEMENTED | Y | class TrustLevel found in server src |
| Agent mastery tracking | IMPLEMENTED | IMPLEMENTED | Y | """Get rules personalized to an agent's history and mastery."""; @router.get("/mastery/{agent_id}") |
| Agent exception requests | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/exception-request", response_model=ExceptionResponse, status_code=201); async def request_exception( |
| Agent negotiation | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/negotiate", response_model=NegotiationResponse, status_code=201) |
| Governance sessions | IMPLEMENTED | IMPLEMENTED | Y | from rulerepo_server.adapters.postgres.session import get_db_session; def _get_service(session: AsyncSession = Depends(get_db_session)) -> AgentGovernanceService: |

### Audit

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Audit log (append-only, hash-chained) | IMPLEMENTED | IMPLEMENTED | Y | class AuditLogModel found in server src |
| Audit inspection API (GET /audit) | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/audit.py |
| Audit chain verification script | IMPLEMENTED | IMPLEMENTED | Y | scripts/verify_audit_chain.py |
| Audit frontend page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/audit/page.tsx |

### CLI

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Unified rulerepo CLI (packages/cli) | IMPLEMENTED | IMPLEMENTED | Y | packages/cli/src/rulerepo_cli/main.py |
| rulerepo check command | IMPLEMENTED | IMPLEMENTED | Y | packages/cli/src/rulerepo_cli/check.py |
| rulerepo hook command | IMPLEMENTED | IMPLEMENTED | Y | packages/cli/src/rulerepo_cli/hook.py |
| rulerepo ingest command | IMPLEMENTED | IMPLEMENTED | Y | packages/cli/src/rulerepo_cli/ingest.py |
| rulerepo export command | IMPLEMENTED | IMPLEMENTED | Y | packages/cli/src/rulerepo_cli/export.py |
| rulerepo context command | IMPLEMENTED | IMPLEMENTED | Y | packages/cli/src/rulerepo_cli/context.py |
| rulerepo mcp command | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/mcp/server.py |
| rulerepo init command | IMPLEMENTED | IMPLEMENTED | Y | packages/cli/src/rulerepo_cli/commands/init.py |
| rulerepo doctor command | IMPLEMENTED | IMPLEMENTED | Y | packages/cli/src/rulerepo_cli/commands/doctor.py |
| rulerepo audit verify command | IMPLEMENTED | IMPLEMENTED | Y | packages/cli/src/rulerepo_cli/commands/audit.py |

### Core

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Rule CRUD API | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/rules.py; apps/server/src/rulerepo_server/services/rule_service.py |
| Rule revision history | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/domain/revision.py |
| Rule effective_period (valid_from/valid_until) | IMPLEMENTED | IMPLEMENTED | Y | class EffectivePeriod found in server src |
| Rule maturity_level (EXPERIMENTAL/STABLE/PROVEN) | IMPLEMENTED | IMPLEMENTED | Y | class MaturityLevel found in server src |
| Rule sensitivity field | IMPLEMENTED | IMPLEMENTED | Y | sensitivity: Sensitivity = Sensitivity.INTERNAL |
| Rule applicable_to (SubjectFilter) | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/domain/subject.py |
| Rule equivalence_id (polyglot) | IMPLEMENTED | IMPLEMENTED | Y | equivalence_id: str \| None = None |
| Rule regulatory_severity | IMPLEMENTED | IMPLEMENTED | Y | regulatory_severity: RegulatorySeverity = RegulatorySeverity.NONE |
| Rule tenant_id | IMPLEMENTED | IMPLEMENTED | Y | tenant_id: Mapped[str] = mapped_column(Uuid, nullable=False, default=DEFAULT_TENANT_ID, index=True); __table_args__ = (sa.UniqueConstraint("rule_id", "tenant_id", "date", name="uq_eval_daily_agg"),) |

### Discovery

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Discovery scan API | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/discovery.py |
| CLAUDE.md analyzer | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/discovery/analyzers/claude_md.py |
| Linter config analyzer | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/discovery/analyzers/linter_config.py |
| Code patterns analyzer | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/discovery/analyzers/code_patterns.py |
| Policy document analyzer | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/discovery/analyzers/policy_document.py |

### Evaluation

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Evaluation API (POST /evaluate) | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/evaluation.py |
| Diff parser | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/diff_parser.py |
| Context assembler | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/context_assembler.py |
| Rule selector | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/rule_selector.py |
| Batch evaluator | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/batch_evaluator.py |
| Verdict aggregator | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/verdict_aggregator.py |
| Conflict aggregator | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/conflict_aggregator.py |
| Graph resolver | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/graph_resolver.py |
| Impact preview | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/impact_preview.py |
| EvaluationDomainAdapter Protocol | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/adapters/base.py |
| Code adapter (under adapters/code/) | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/adapters/code/ (directory with files) |
| business_event adapter | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/adapters/business_event/ (directory with files) |
| document_diff adapter | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/adapters/document_diff/ (directory with files) |
| communication adapter | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/adapters/communication/ (directory with files) |
| documentation adapter | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/adapters/documentation/ (directory with files) |
| Consensus voting for CRITICAL | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/consensus.py |
| Idempotency-Key middleware | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/evaluation/idempotency.py |

### Extraction

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Extraction pipeline | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/extraction/pipeline.py |
| Document upload API | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/extraction.py |
| PDF sanitizer (pikepdf) | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/extraction/pdf_sanitizer.py |
| Contract clause segmenter | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/extraction/contract/ (directory with files) |

### Federation

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Federation CRUD API | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/federation.py |
| Effective rules resolution | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/federation/resolver.py |
| Federation diff | IMPLEMENTED | IMPLEMENTED | Y | @router.get("/{federation_id}/diff/{other_id}"); async def diff_federations( |

### Feedback

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Correction feedback API | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/feedback.py |
| Auto-draft from corrections | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/feedback/auto_drafter.py |
| Correction analyzer | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/feedback/correction_analyzer.py |

### Frontend

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Rules list page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/rules/page.tsx |
| Rule detail page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/rules/page.tsx |
| Search page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/search/page.tsx |
| Documents page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/documents/page.tsx |
| Discovery page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/discover/page.tsx |
| Playground page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/playground/page.tsx |
| Proposals page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/proposals/page.tsx |
| Federation page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/federations/page.tsx |
| Snapshots page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/snapshots/page.tsx |
| Intelligence page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/intelligence/page.tsx |
| Feedback page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/feedback/page.tsx |
| Agents page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/agents/page.tsx |
| Gateway page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/gateway/page.tsx |
| Review page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/review/page.tsx |
| Notifications page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/notifications/page.tsx |
| Projects page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/projects/page.tsx |
| Integrations page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/integrations/page.tsx |
| Audit page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/audit/page.tsx |
| Rule Tutor page | IMPLEMENTED | IMPLEMENTED | Y | apps/frontend/app/(dashboard)/tutor/page.tsx |
| Persona switcher | IMPLEMENTED | IMPLEMENTED | Y | export function PersonaSwitcher() {; const [persona, setPersona] = useState<Persona>("all"); |
| Sidebar reorganization (Compose/Govern/Observe/Share/Agents) | PARTIAL | PARTIAL | Y | { href: "/agents", label: "Agents", section: "observe", tooltip: "Track AI agent compliance leaderboard, trust levels, rule mastery, and verdict challenges" }, |

### Gateway

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Gateway webhook ingestion | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/gateway/router.py |
| Gateway enforcement policies | IMPLEMENTED | IMPLEMENTED | Y | class EnforcementPolicyModel found in server src |
| Slack/Teams/Email gateways | IMPLEMENTED | IMPLEMENTED | Y | slack.py; teams.py |

### Infrastructure

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Docker Compose full stack | IMPLEMENTED | IMPLEMENTED | Y | docker-compose.yml |
| PostgreSQL init.sql | IMPLEMENTED | IMPLEMENTED | Y | infra/postgres/init.sql |
| Elasticsearch setup | IMPLEMENTED | IMPLEMENTED | Y | infra/elasticsearch/setup.sh |
| Neo4j init.cypher | IMPLEMENTED | IMPLEMENTED | Y | infra/neo4j/init.cypher |
| Redis service | IMPLEMENTED | IMPLEMENTED | Y | redis:; image: redis:7-alpine |
| arq-worker service | IMPLEMENTED | IMPLEMENTED | Y | arq-worker: |
| MCP server service | IMPLEMENTED | IMPLEMENTED | Y | mcp-server: |

### Integrations

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| GitHub webhook receiver | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/integrations/github/router.py |
| GitHub check reporter | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/integrations/github/check_reporter.py |

### Intelligence

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Intelligence dashboard API | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/intelligence.py |
| Health scoring | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/intelligence/health_scorer.py |
| Rule effectiveness | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/intelligence/effectiveness.py |
| Recommendations | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/intelligence/recommender.py |
| Agent analytics | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/intelligence/agent_analytics.py |
| Weekly digest | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/intelligence/digest.py |

### Intent

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Intent API (POST /intent) | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/intent.py |
| Intent classifier | IMPLEMENTED | IMPLEMENTED | Y | class IntentClassifier found in server src |

### LLM

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| LLMProvider Protocol (adapters/llm/base.py) | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/adapters/llm/base.py |
| Gemini adapter | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/adapters/gemini/ (directory with files) |
| Anthropic adapter | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/adapters/llm/anthropic.py |
| OpenAI adapter | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/adapters/llm/openai.py |
| Local LLM adapter (vLLM/Ollama) | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/adapters/llm/local.py |

### MCP

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| MCP server (stdio + HTTP) | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/mcp/server.py |
| MCP tools (search, explain, conflicts) | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/mcp/tools.py |
| MCP resources | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/mcp/resources.py |
| MCP prompts | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/mcp/prompts.py |

### Multi-tenancy

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Tenant model and tenant_id FK | IMPLEMENTED | IMPLEMENTED | Y | tenant_id: Mapped[str] = mapped_column(Uuid, nullable=False, default=DEFAULT_TENANT_ID, index=True); __table_args__ = (sa.UniqueConstraint("rule_id", "tenant_id", "date", name="uq_eval_daily_agg"),) |
| Postgres Row-Level Security | IMPLEMENTED | IMPLEMENTED | Y | infra/postgres/rls_policies.sql |
| Elasticsearch routing by tenant | IMPLEMENTED | IMPLEMENTED | Y | tenant_id: Optional tenant ID for routing tenant isolation.; kwargs["routing"] = f"tenant_{tenant_id}" |
| Neo4j multi-database per tenant | IMPLEMENTED | IMPLEMENTED | Y | Supports multi-database tenant isolation via Neo4j 5 multi-database.; When tenant_database is set, all operations target that database. |

### Observability

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Cost ledger (token counts on evaluations) | IMPLEMENTED | IMPLEMENTED | Y | input_tokens: Mapped[int \| None] = mapped_column(Integer, nullable=True) |

### PII

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| PII tokenizer (core/pii/tokenizer.py) | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/core/pii/tokenizer.py |
| PII masking in logs | PARTIAL | PARTIAL | Y | core/pii.py or core/pii/ exists |
| Evaluation context encryption | IMPLEMENTED | IMPLEMENTED | Y | context_encrypted: Mapped[bytes \| None] = mapped_column(LargeBinary, nullable=True) |

### Playground

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Playground evaluate API | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/playground.py |
| Test case generation | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/playground/test_generator.py |
| Test runner | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/playground/test_runner.py |
| Counterexample generator | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/playground/counterexample_generator.py |

### Proposals

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Proposal CRUD API | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/proposals.py |
| Proposal voting workflow | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/{proposal_id}/vote", response_model=ProposalResponse); async def vote_on_proposal( |
| Proposal enact/revert | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/{proposal_id}/enact", response_model=ProposalResponse); async def enact_proposal( |
| Proposal notifications | IMPLEMENTED | IMPLEMENTED | Y | @router.get("/notifications/inbox", response_model=NotificationListResponse); async def get_notifications( |

### Provenance

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Why API (GET /rules/{id}/why) | IMPLEMENTED | IMPLEMENTED | Y | @router.get("/{rule_id}/why"); async def get_rule_why( |
| Provenance lineage resolver | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/services/provenance/lineage_resolver.py |
| DERIVES_FROM basis_type edge property | IMPLEMENTED | IMPLEMENTED | Y | basis_type: str \| None = None,; basis_type: For DERIVES_FROM edges, the provenance type |

### Sample Rules

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Coding rules (10 documents) | IMPLEMENTED | IMPLEMENTED | Y | sample_rules/coding_rules/ (directory with files) |
| Company rules (6 documents) | IMPLEMENTED | IMPLEMENTED | Y | sample_rules/company_rules/ (directory with files) |
| Sales team rules (5 documents) | IMPLEMENTED | IMPLEMENTED | Y | sample_rules/sales_team_rules/ (directory with files) |
| Rule templates (5 YAML) | IMPLEMENTED | IMPLEMENTED | Y | sample_rules/templates/ (directory with files) |
| Legal rules | IMPLEMENTED | IMPLEMENTED | Y | sample_rules/legal_rules/ (directory with files) |
| Communication rules | IMPLEMENTED | IMPLEMENTED | Y | sample_rules/communication_rules/ (directory with files) |

### Scripts

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| seed_data.py | IMPLEMENTED | IMPLEMENTED | Y | scripts/seed_data.py |
| reconcile_graph.py | IMPLEMENTED | IMPLEMENTED | Y | scripts/reconcile_graph.py |
| reindex_elasticsearch.py | IMPLEMENTED | IMPLEMENTED | Y | scripts/reindex_elasticsearch.py |
| generate_claude_md.py | IMPLEMENTED | IMPLEMENTED | Y | scripts/generate_claude_md.py |
| spec_audit.py | IMPLEMENTED | IMPLEMENTED | Y | scripts/spec_audit.py |
| verify_audit_chain.py | IMPLEMENTED | IMPLEMENTED | Y | scripts/verify_audit_chain.py |

### Search

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Full-text search | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/fulltext"); async def fulltext_search( |
| Vector search | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/vector"); async def vector_search( |
| Hybrid search | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/hybrid"); async def hybrid_search( |
| Category search | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/category"); async def category_search( |
| Context search | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/context"); async def context_search( |
| Document search | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/documents/fulltext"); async def search_documents_fulltext( |
| Temporal search | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/temporal"); async def temporal_search( |
| Citation search | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/citation"); async def citation_search( |
| Subject-aware search | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/subject"); async def subject_search( |
| Conflict-aware search | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/conflict"); async def conflict_search( |

### Snapshots

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| Snapshot CRUD API | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/api/v1/snapshots.py |
| Snapshot deploy/rollback | IMPLEMENTED | IMPLEMENTED | Y | """Snapshots & Deployments API — CRUD + deploy + rollback + simulate."""; @router.get("/deployments", response_model=list[DeploymentResponse]) |
| Snapshot simulate | IMPLEMENTED | IMPLEMENTED | Y | """Snapshots & Deployments API — CRUD + deploy + rollback + simulate."""; from rulerepo_server.services.snapshots.simulator import simulate_impact |
| Bulk impact preview (simulate-bulk) | IMPLEMENTED | IMPLEMENTED | Y | @router.post("/{snapshot_id}/simulate-bulk") |

### Tier 0

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| spec_audit.py script | IMPLEMENTED | IMPLEMENTED | Y | scripts/spec_audit.py |
| development/feature_interactions.md | IMPLEMENTED | IMPLEMENTED | Y | development/feature_interactions.md |
| development/spec_implementation_audit.md | IMPLEMENTED | IMPLEMENTED | Y | development/spec_implementation_audit.md |
| tests/integration/feature_matrix/ | IMPLEMENTED | IMPLEMENTED | Y | apps/server/tests/integration/feature_matrix/ (directory with files) |
| make spec-audit target | IMPLEMENTED | IMPLEMENTED | Y | .PHONY: seed reconcile spec-audit; spec-audit: ## Audit spec docs against codebase (outputs development/spec_implementation_audit.md) |

### Workers

| Feature | Declared | Actual | Match | Evidence |
|---------|----------|--------|-------|----------|
| arq worker settings | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/workers/settings.py |
| Continuous conflict scanner | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/workers/conflict_scanner.py |
| Archival worker | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/workers/archival.py |
| Policy review cycle worker | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/workers/policy_review_cycle.py |
| Verdict drift monitor | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/workers/verdict_drift.py |
| Polyglot validator | IMPLEMENTED | IMPLEMENTED | Y | apps/server/src/rulerepo_server/workers/polyglot_validator.py |

# REST API Reference

All endpoints are prefixed with `/api/v1` unless noted otherwise. Interactive documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI) and [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc).

## Health

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness probe. Returns `{"status": "ok"}` if the process is running. |
| GET | `/readyz` | Readiness probe. Checks connectivity to PostgreSQL, Elasticsearch, and Neo4j. |

## Rules (CRUD)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/rules` | Create a new rule. |
| GET | `/api/v1/rules` | List rules with pagination and optional filters (`modality`, `severity`, `status`). |
| GET | `/api/v1/rules/{rule_id}` | Get a single rule by ID. |
| PATCH | `/api/v1/rules/{rule_id}` | Update an existing rule (creates a new revision). |
| POST | `/api/v1/rules/{rule_id}/retire` | Retire a rule (soft-delete via `valid_until`). |
| GET | `/api/v1/rules/{rule_id}/revisions` | Get the revision history for a rule. |
| GET | `/api/v1/rules/{rule_id}/relationships` | Get all relationships involving a rule. |
| GET | `/api/v1/rules/{rule_id}/graph` | Get the relationship subgraph around a rule (configurable `depth`, 1--5). |

## Relationships

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/relationships` | Create a relationship between two rules (source_id, target_id, relationship_type). |
| DELETE | `/api/v1/relationships` | Delete a specific relationship (query params: source_id, target_id, relationship_type). |

## Search

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/search/fulltext` | BM25 full-text search over rule statements. |
| POST | `/api/v1/search/vector` | Semantic similarity search using embeddings. |
| POST | `/api/v1/search/hybrid` | Combined BM25 + vector hybrid search. |
| POST | `/api/v1/search/category` | Filter-only search by category fields (modality, severity, scope, tags, status). |
| POST | `/api/v1/search/context` | Given facts about a situation, find applicable rules. |

## Evaluation

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/evaluate` | Full evaluation of a code change or action against applicable rules. |
| POST | `/api/v1/evaluate/quick` | Simplified evaluation for a plain-text action description. |
| POST | `/api/v1/evaluate/applicable-rules` | Get rules that apply to given file paths without running evaluation. |

See [Evaluate API](evaluate.md) for detailed request/response documentation.

## Contract Evaluation

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/evaluate/contract` | Evaluate a contract against applicable clause rules. Parses the contract, evaluates each clause, and returns clause-scoped verdicts with a contract-level aggregate. Supports review types: `self_conformance`, `cross_contract`, `regulatory_compliance`, `risk_scoring`. |

## Event Evaluation

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/evaluate/event` | Evaluate a business event (attendance, overtime, leave) against applicable rules. Supports evaluation modes: `single` (default), `sequence` (monthly context), `calendar` (annual context). |

## Intent

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/intent` | Accept a natural-language query, classify intent, and route to the appropriate handler. |

See [Intent API](intent.md) for details and examples.

## Documents

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/documents/upload` | Upload a document (PDF, text, markdown) for rule extraction. |
| POST | `/api/v1/documents/{document_id}/extract` | Trigger LLM-powered rule extraction on an uploaded document. |
| GET | `/api/v1/documents/extractions/{extraction_id}` | Get extraction results (candidate rules, model, status). |
| POST | `/api/v1/documents/extractions/{extraction_id}/review` | Review extraction results: approve or edit candidates to create rules. |

## Intelligence

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/intelligence/dashboard` | Corpus-wide intelligence dashboard (health summary, evaluation volume, verdicts, cache stats, top violated rules). |
| GET | `/api/v1/intelligence/health` | Paginated rule health scores, sortable by dimension. |
| GET | `/api/v1/intelligence/health/{rule_id}` | Detailed health breakdown for a single rule. |
| GET | `/api/v1/intelligence/analytics` | Corpus-wide evaluation analytics for a configurable period (1--365 days). |
| GET | `/api/v1/intelligence/analytics/{rule_id}` | Per-rule evaluation analytics (fire rate, deny rate, trends). |
| GET | `/api/v1/intelligence/recommendations` | Active improvement recommendations, prioritized, filterable by status. |

## Gateway

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/gateway/ingest/{source}` | Receive a webhook from an external source (github, slack, generic) and evaluate against matched policies. |
| POST | `/api/v1/gateway/ingest` | Receive a generic webhook event with explicit event_type. |
| POST | `/api/v1/gateway/policies` | Create a new enforcement policy. |
| GET | `/api/v1/gateway/policies` | List enforcement policies (optionally filter to enabled only). |
| GET | `/api/v1/gateway/evaluations` | List recent gateway evaluations with pagination. |

## Discovery

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/discover/scan` | Start a discovery scan on project artifacts (config files, documentation). |
| GET | `/api/v1/discover/scans/{scan_id}` | Get the status of a discovery scan. |
| GET | `/api/v1/discover/scans/{scan_id}/candidates` | List candidate rules from a completed scan. |
| POST | `/api/v1/discover/candidates/{candidate_id}/approve` | Approve a candidate, creating a rule. |
| POST | `/api/v1/discover/candidates/{candidate_id}/dismiss` | Dismiss a candidate. |

See [Discovery API](discovery.md) for detailed request/response documentation.

## Feedback

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/feedback/corrections` | Submit a correction (original vs. corrected diff). |
| GET | `/api/v1/feedback/corrections` | List corrections with pagination and filters (status, type). |
| POST | `/api/v1/feedback/corrections/{correction_id}/approve` | Approve a correction, applying its suggestion. |
| POST | `/api/v1/feedback/corrections/{correction_id}/dismiss` | Dismiss a correction. |
| GET | `/api/v1/feedback/stats` | Feedback statistics (totals, by type/status, rules created, top violated rules). |
| GET | `/api/v1/feedback/proposals` | List draft rule proposals from the correction-to-rule flywheel. |
| POST | `/api/v1/feedback/proposals/{proposal_id}/approve` | Approve a proposal — creates a rule with experimental maturity (shadow mode). |
| POST | `/api/v1/feedback/proposals/{proposal_id}/dismiss` | Dismiss a proposal. |

See [Feedback API](feedback.md) for detailed request/response documentation.

## Playground

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/playground/evaluate` | Sandbox evaluation of sample code against an inline rule (no audit, no cache). |
| POST | `/api/v1/rules/{rule_id}/test-cases` | Create a test case for a rule. |
| GET | `/api/v1/rules/{rule_id}/test-cases` | List test cases for a rule. |
| DELETE | `/api/v1/rules/{rule_id}/test-cases/{test_case_id}` | Delete a test case. |
| POST | `/api/v1/rules/{rule_id}/test-cases/run` | Run all test cases for a rule through sandbox evaluation. |
| POST | `/api/v1/rules/{rule_id}/test-cases/generate` | Generate test cases for a rule using Gemini. |

See [Playground API](playground.md) for detailed request/response documentation.

## Alerts

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/alerts` | List alerts with filtering by status and type, paginated. |
| GET | `/api/v1/alerts/{alert_id}` | Get a single alert by ID. |
| POST | `/api/v1/alerts/{alert_id}/acknowledge` | Mark an alert as acknowledged. |
| POST | `/api/v1/alerts/{alert_id}/resolve` | Mark an alert as resolved. |

See [Alerts API](alerts.md) for detailed request/response documentation.

## Snapshots

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/snapshots` | Create a new snapshot of the current rule corpus. |
| GET | `/api/v1/snapshots` | List snapshots with pagination. |
| GET | `/api/v1/snapshots/{snapshot_id}` | Get a snapshot by ID. |
| POST | `/api/v1/snapshots/{snapshot_id}/deploy` | Deploy a snapshot to an environment. |
| POST | `/api/v1/snapshots/{snapshot_id}/rollback` | Rollback to the previous snapshot in the deployed environment. |
| POST | `/api/v1/snapshots/{snapshot_id}/simulate` | Simulate the impact of deploying this snapshot. |
| GET | `/api/v1/snapshots/deployments` | List active snapshot per environment. |
| GET | `/api/v1/snapshots/deployments/{environment}` | Get deployment history for an environment. |

See [Snapshots API](snapshots.md) for detailed request/response documentation.

## Federation

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/federations` | Create a federation node (organization, team, or project). |
| GET | `/api/v1/federations` | List federation nodes as a tree. |
| GET | `/api/v1/federations/{node_id}` | Get a federation node's details. |
| POST | `/api/v1/federations/{node_id}/rules` | Add a rule to a federation node (optionally overriding a parent rule). |
| DELETE | `/api/v1/federations/{node_id}/rules/{rule_id}` | Remove a rule from a federation node. |
| GET | `/api/v1/federations/{node_id}/effective-rules` | Get the resolved effective rule set for a node. |
| GET | `/api/v1/federations/{node_id}/diff` | Diff this node's effective rules against its parent. |

See [Federation API](federation.md) for detailed request/response documentation.

## Integrations

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/integrations/webhooks/github` | GitHub App webhook receiver. Processes pull request events, runs evaluation, and returns formatted review comments. |

## Projects

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/projects` | Create a new project. |
| GET | `/api/v1/projects` | List projects with pagination. |
| GET | `/api/v1/projects/{project_id}` | Get a project by ID. |
| PATCH | `/api/v1/projects/{project_id}` | Update a project. |

## Proposals

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/proposals` | Create a governance proposal (create, amend, retire, merge, split, override). |
| GET | `/api/v1/proposals` | List proposals with pagination and filters. |
| GET | `/api/v1/proposals/{proposal_id}` | Get a proposal by ID. |
| POST | `/api/v1/proposals/{proposal_id}/submit` | Submit a proposal for review. |
| POST | `/api/v1/proposals/{proposal_id}/vote` | Cast a vote on a proposal. |
| POST | `/api/v1/proposals/{proposal_id}/comments` | Add a comment to a proposal. |

## Agent Governance

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/agents` | Register an agent profile. |
| GET | `/api/v1/agents` | List agent profiles. |
| GET | `/api/v1/agents/{agent_id}` | Get an agent profile. |
| GET | `/api/v1/agents/{agent_id}/personalized-rules` | Get rules personalized for an agent (mastered suppressed, weak boosted). |
| POST | `/api/v1/agents/{agent_id}/challenge` | Challenge a verdict. |
| POST | `/api/v1/agents/{agent_id}/exception` | Request a rule exception. |

## Departments

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/departments` | Create a department. |
| GET | `/api/v1/departments` | List departments. |
| GET | `/api/v1/departments/{department_id}` | Get a department by ID. |
| PATCH | `/api/v1/departments/{department_id}` | Update a department. |

## Audit

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/audit` | List audit log entries with filters (action, classification, date range). |
| GET | `/api/v1/audit/{entry_id}` | Get a single audit log entry. |
| POST | `/api/v1/audit/verify` | Verify hash chain integrity for a range of entries. |

## Review

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/evaluate/review/rough` | Rough triage: evaluate all rules for relevance to an activity. |
| POST | `/api/v1/evaluate/review/detailed` | Detailed evaluation: full LLM evaluation on a shortlisted set of rules. |

## Approval Workflows

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/approval-workflows` | Create a per-scope approval workflow. |
| GET | `/api/v1/approval-workflows` | List approval workflows. |
| GET | `/api/v1/approval-workflows/{scope}` | Get the workflow for a scope. |

## Attestation

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/attestation/campaigns` | Create an attestation campaign. |
| GET | `/api/v1/attestation/campaigns` | List campaigns. |
| POST | `/api/v1/attestation/campaigns/{id}/respond` | Submit an attestation response. |

## Compliance

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/compliance/status` | Get compliance status for a scope. |
| POST | `/api/v1/compliance/erasure` | Submit a data erasure request (GDPR). |

## Cost

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/cost/summary` | Get LLM cost summary for the current tenant. |
| GET | `/api/v1/cost/breakdown` | Get cost breakdown by model/domain/period. |

## Facts

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/facts/resolve` | Resolve external facts for evaluation context. |
| GET | `/api/v1/facts/providers` | List available fact providers. |
| GET | `/api/v1/facts/providers/{key}/health` | Check fact provider health. |

## Operability

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/operability/health` | Detailed system health check. |
| GET | `/api/v1/operability/dr/status` | Disaster recovery status. |

## Regulatory

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/regulatory/sources` | Register a regulatory source. |
| GET | `/api/v1/regulatory/sources` | List tracked regulatory sources. |
| GET | `/api/v1/regulatory/sources/{id}/amendments` | Get amendments for a source. |

## Risks

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/risks` | Create a risk register entry. |
| GET | `/api/v1/risks` | List risk entries. |
| POST | `/api/v1/risks/{id}/rules` | Map rules to a risk. |

## SCIM

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/scim/Users` | List SCIM users. |
| POST | `/api/v1/scim/Users` | Provision a SCIM user. |
| GET | `/api/v1/scim/Groups` | List SCIM groups. |

## Tenants

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/tenants` | Create a tenant. |
| GET | `/api/v1/tenants` | List tenants. |
| GET | `/api/v1/tenants/{id}` | Get a tenant by ID. |

## Translations

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/translations/{rule_id}` | Add a translation for a rule. |
| GET | `/api/v1/translations/{rule_id}` | Get translations for a rule. |

## Upcoming Changes

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/upcoming-changes` | List scheduled rule changes (effective_from in the future). |

## Ask (Conversational Assistant)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/ask` | Ask a natural-language question about rules. Returns LLM-powered explanation. |

## Conversational Assistant

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/assistant/turn` | Submit a conversational turn. The assistant classifies intent, searches rules, and generates a contextual answer with citations. |

## Norm Lineage

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/lineage/{rule_id}/upstream` | Trace rule derivation chain upstream to source law/regulation (max_depth=20). |
| GET | `/api/v1/lineage/{rule_id}/downstream` | Trace rule derivation chain downstream to all derived operational rules (max_depth=20). |

## Compliance Cockpit

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/cockpit/dashboard` | Department-level compliance dashboard (violation trends, policy fire/deny rates, regulatory propagation). |
| GET | `/api/v1/cockpit/action-queue` | Action queue: unapproved proposals, low-effectiveness rules, dormant rules. |

## Events Ingestion

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/events/ingest` | Universal business event ingestion. Resolves scope from event_type, selects rules, dispatches to the correct subject evaluator. |

## Onboarding

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/onboarding/status` | Get onboarding progress for the current project. |
| POST | `/api/v1/onboarding/complete-step` | Mark an onboarding step as complete. |

# Architecture Overview

## Deployable Components

The Rule Repository consists of ten services (plus two one-shot setup containers), all orchestrated locally via Docker Compose. The backend exposes 18 API routers backed by 13 service directories. Rules are scoped to projects for multi-team organization.

| Component | Technology | Port | Role |
|---|---|---|---|
| **Backend API** | Python 3.13 / FastAPI | 8000 | System of record. REST, Evaluate, Intent, Gateway, and Integration APIs. |
| **MCP Server** | Python / FastMCP | 8001 | Exposes rule search, evaluation, and context delivery to AI agents via the Model Context Protocol. |
| **Frontend** | TypeScript / Next.js / Tailwind | 3000 | Operator console for browsing, searching, uploading documents, and reviewing evaluations. |
| **PostgreSQL** | PostgreSQL 17 | 5432 | Relational store for rules, revisions, relationships, documents, audit log, policies, and cache. |
| **Elasticsearch** | Elasticsearch 8.17 | 9200 | Full-text (BM25) and vector (768-dim cosine) search index for rules. |
| **Neo4j** | Neo4j 5 Community | 7474 / 7687 | Directed graph of rule relationships (refines, overrides, conflicts_with, depends_on, derives_from, succeeds). |
| **Redis** | Redis 7 Alpine | 6379 | Job queue and result backend for background workers. |
| **arq-worker** | Python 3.13 / arq | -- | Background worker running scheduled cron jobs (health refresh, recommendation generation, feedback analysis). |

## Data Store Roles

- **PostgreSQL** is the system of record. All rule data, revisions, and audit records live here.
- **Elasticsearch** is a derived search index. It is rebuilt from PostgreSQL on rule changes.
- **Neo4j** is a derived relationship graph. PostgreSQL wins if they disagree; the `reconcile_graph.py` script can rebuild Neo4j from scratch.

## Layering Rule

The backend follows a strict layering discipline:

```
api/  -->  services/  -->  domain/
                      -->  adapters/
```

- `api/` (routers) depends on `services/` only.
- `services/` depends on `domain/` (pure business objects) and `adapters/` (Postgres, Elasticsearch, Neo4j, Gemini).
- `domain/` depends on nothing else in the project.
- No layer imports upward.

## Key Data Flows

### Rule Creation

1. Client sends `POST /api/v1/rules` with a rule statement and metadata.
2. The rule service persists the rule to PostgreSQL, indexes it in Elasticsearch, and creates the corresponding Neo4j node.
3. An audit log entry records the creation event.

### Document Extraction

1. Client uploads a document via `POST /api/v1/documents/upload`.
2. Client triggers extraction via `POST /api/v1/documents/{id}/extract`.
3. The extraction pipeline (Gemini-powered) proposes candidate rules.
4. A human reviews, edits, and approves candidates, which become rules through the standard creation flow.

### Evaluation

1. Client sends a diff, file list, or free-form facts to `POST /api/v1/evaluate`.
2. The evaluation engine selects relevant rules (metadata filtering + effective_period enforcement + semantic ranking).
3. The graph resolver fetches Neo4j relationships (OVERRIDES, CONFLICTS_WITH, DEPENDS_ON) between selected rules and builds an evaluation plan.
4. The **batched evaluator** sends all selected rules to Gemini in a single API call with structured JSON output requesting per-rule verdicts. For DENY + CRITICAL rules, a Pro model confirmation pass re-evaluates those specific rules. If the batch call fails, the system falls back to per-rule concurrent evaluation.
5. Each evaluation result is persisted to the `evaluations` table for analytics.
6. The conflict-aware aggregator applies overrides, resolves conflicts (severity > modality > specificity tiebreak), and skips rules whose prerequisite was denied.
7. The response includes violations, warnings, code locations, fix suggestions, and `conflict_resolutions[]` explaining any relationship-based decisions.
8. The full evaluation is logged to the audit trail.

See [Batched Evaluation](batch-evaluation.md) for the detailed architecture.

### Context Delivery (MCP)

1. An AI agent connects to the MCP server.
2. The agent calls `get_rules_for_context` with its current working context.
3. The MCP server selects applicable rules and returns them in a format optimized for LLM consumption.

### Rule Discovery

1. Client submits project artifacts to `POST /api/v1/discover/scan` — or uses **one-click GitHub import** via `POST /api/v1/discover/import` with a repository URL.
2. For GitHub import: the importer fetches CLAUDE.md, pyproject.toml, eslint config, tsconfig, and other key files via the GitHub Contents API.
3. Source analyzers extract candidate rules; the pattern detector deduplicates and scores them.
4. Gemini refines candidates into well-formed rule statements with suggested metadata.
5. Candidates enter a human review queue for approval or dismissal.

### Correction Feedback

1. A correction is submitted manually via `POST /api/v1/feedback/corrections`, or **captured automatically** when a PR is merged that differs from what was evaluated.
2. For auto-capture: the PR merge webhook compares the evaluated diff (stored in audit log) against the final merged diff, and submits the delta as a correction.
3. Gemini analyzes the correction and classifies it (new_rule, improve_existing, adjust_scope).
4. Approved corrections create or update rules, closing the feedback loop.

### Rule Impact Preview

1. Before updating a rule, call `POST /api/v1/rules/{id}/impact-preview` with proposed changes.
2. The system replays historical evaluations involving that rule with the modified version.
3. Returns how many verdicts would change, affected repositories, and a risk assessment.

### Federation

1. Rules are organized into a hierarchy of federation nodes (organization, team, project).
2. When rules are requested for a node, the federation resolver walks the ancestor chain and applies overrides.
3. The effective rule set reflects inherited rules plus local customizations.

### Webhook Enforcement (Gateway)

1. An external system (GitHub, Slack, or generic) sends a webhook to `POST /api/v1/gateway/ingest/{source}`.
2. The gateway normalizes the event, matches it against enabled enforcement policies, and runs the evaluation engine.
3. Results are recorded and optionally trigger response actions.

## Further Reading

### Playground Evaluation

1. Client sends a rule definition and sample code to `POST /api/v1/playground/evaluate`.
2. The sandbox pipeline runs the same Gemini evaluation but skips audit logging, LLM caching, and persistence.
3. Returns a verdict, confidence, reasoning, and fix suggestion.

### Snapshots and Environments

1. An operator creates a snapshot (`POST /api/v1/snapshots`) capturing the current live rule corpus.
2. The snapshot is deployed to an environment (development, staging, production) via `POST /api/v1/snapshots/{id}/deploy`.
3. Evaluation and MCP requests that specify an `environment` parameter resolve rules from the deployed snapshot rather than the live corpus.
4. Impact simulation (`POST /api/v1/snapshots/{id}/simulate`) replays historical evaluations to predict verdict changes before promotion.

### Proactive Alerts

1. Background workers (health refresh cron) and the evaluation pipeline detect conditions such as dormant rules, high deny rates, health declines, and conflicts.
2. Alerts are created in the alerts table and surfaced via `GET /api/v1/alerts`.
3. Operators acknowledge or resolve alerts through the API or the dashboard alerts panel.

## Further Reading

See [Data Stores](data-stores.md) for schema details, [Evaluation Engine](evaluation-engine.md) for the evaluation pipeline, [Rule Discovery](discovery.md) for automated rule extraction, [Rule Playground](playground.md) for sandbox testing, [Snapshots](snapshots.md) for versioned deployments, and [Federation](federation.md) for hierarchical rule composition.

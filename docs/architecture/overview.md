# Architecture Overview

## Deployable Components

The Rule Repository consists of six services, all orchestrated locally via Docker Compose.

| Component | Technology | Port | Role |
|---|---|---|---|
| **Backend API** | Python 3.13 / FastAPI | 8000 | System of record. REST, Evaluate, Intent, Gateway, and Integration APIs. |
| **MCP Server** | Python / FastMCP | 8001 | Exposes rule search, evaluation, and context delivery to AI agents via the Model Context Protocol. |
| **Frontend** | TypeScript / Next.js / Tailwind | 3000 | Operator console for browsing, searching, uploading documents, and reviewing evaluations. |
| **PostgreSQL** | PostgreSQL 17 | 5432 | Relational store for rules, revisions, relationships, documents, audit log, policies, and cache. |
| **Elasticsearch** | Elasticsearch 8.17 | 9200 | Full-text (BM25) and vector (768-dim cosine) search index for rules. |
| **Neo4j** | Neo4j 5 Community | 7474 / 7687 | Directed graph of rule relationships (refines, overrides, conflicts_with, depends_on, derives_from, succeeds). |

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
2. The evaluation engine selects relevant rules (metadata filtering, then semantic ranking).
3. Each selected rule is judged against the context by Gemini (model tier based on rule severity).
4. Per-rule verdicts are aggregated into an overall verdict (any DENY causes overall DENY).
5. The response includes violations, warnings, code locations, and fix suggestions.
6. The full evaluation is logged to the audit trail.

### Context Delivery (MCP)

1. An AI agent connects to the MCP server.
2. The agent calls `get_rules_for_context` with its current working context.
3. The MCP server selects applicable rules and returns them in a format optimized for LLM consumption.

### Webhook Enforcement (Gateway)

1. An external system (GitHub, Slack, or generic) sends a webhook to `POST /api/v1/gateway/ingest/{source}`.
2. The gateway normalizes the event, matches it against enabled enforcement policies, and runs the evaluation engine.
3. Results are recorded and optionally trigger response actions.

## Further Reading

See [Data Stores](data-stores.md) for schema details and [Evaluation Engine](evaluation-engine.md) for the evaluation pipeline.

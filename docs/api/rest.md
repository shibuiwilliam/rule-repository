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
| GET | `/api/v1/intelligence/dashboard` | Corpus-wide intelligence dashboard (health summary, evaluation volume, verdicts). |
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

## Integrations

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/integrations/webhooks/github` | GitHub App webhook receiver. Processes pull request events, runs evaluation, and returns formatted review comments. |

# API Reference

Base URL: `http://localhost:8000`

Interactive documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

All API v1 endpoints are prefixed with `/api/v1`. Health endpoints are at the root level.

---

## Health

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness probe. Always returns `{"status": "ok"}` if the process is running. No dependency checks. |
| GET | `/readyz` | Readiness probe. Checks connectivity to PostgreSQL, Elasticsearch, and Neo4j. Returns `{"status": "ok"}` or `{"status": "degraded"}` with per-service check results. |
| GET | `/api/v1/health` | API-level health check. Returns `{"status": "ok", "version": "v1"}`. |

---

## Rules CRUD

All rule endpoints are in `api/v1/rules.py`. Router prefix: `/api/v1/rules`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/rules` | Create a new rule. Body: `RuleCreate` (statement, modality, severity, scope, tags, rationale). Returns the created rule with generated UUID. Status 201. |
| GET | `/api/v1/rules` | List rules with pagination and optional filters. Query params: `page` (default 1), `page_size` (default 20, max 100), `modality`, `severity`, `status`. |
| GET | `/api/v1/rules/{rule_id}` | Get a single rule by UUID. Returns full rule metadata. |
| PATCH | `/api/v1/rules/{rule_id}` | Update an existing rule. Body: `RuleUpdate` (partial). Creates a revision record. |
| POST | `/api/v1/rules/{rule_id}/retire` | Retire a rule by setting `effective_period.valid_until`. Rules are never deleted. |
| GET | `/api/v1/rules/{rule_id}/revisions` | Get the full revision history for a rule. Returns list of revision dicts with revision number, changed fields, changed_by, and change_note. |
| GET | `/api/v1/rules/{rule_id}/relationships` | Get all relationships involving a rule (both as source and target). Returns relationship type, source_id, target_id. |
| GET | `/api/v1/rules/{rule_id}/graph` | Get the Neo4j relationship subgraph around a rule. Query param: `depth` (default 1, max 5). Returns nodes and edges. |

---

## Relationships

Endpoints in `api/v1/relationships.py`. Router prefix: `/api/v1/relationships`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/relationships` | Create a directed relationship between two rules. Body: `RelationshipCreate` with `source_id` (UUID), `target_id` (UUID), `relationship_type` (REFINES, OVERRIDES, CONFLICTS_WITH, DEPENDS_ON, DERIVES_FROM, SUCCEEDS). Status 201. |
| DELETE | `/api/v1/relationships` | Delete a specific relationship. Query params: `source_id`, `target_id`, `relationship_type`. All three are required. |

---

## Search

Endpoints in `api/v1/search.py`. Router prefix: `/api/v1/search`. All search endpoints use POST with a JSON body.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/search/fulltext` | BM25 full-text search over rule statements. Body: `SearchQuery` with `query` (string), optional `modality`, `severity`, `scope`, `tags`, `page`, `page_size`. |
| POST | `/api/v1/search/vector` | Semantic similarity search using embeddings (dense_vector in Elasticsearch). Same body as fulltext. |
| POST | `/api/v1/search/hybrid` | Combined BM25 + kNN hybrid search. Combines keyword and semantic signals. Same body as fulltext. |
| POST | `/api/v1/search/category` | Filter-only search by category fields (no free-text query required). Body: `CategorySearchQuery` with optional `modality`, `severity`, `status`, `scope` (list), `tags` (list), `page`, `page_size`. |
| POST | `/api/v1/search/context` | Context-based search. Given a set of facts about a situation, returns applicable rules. Body: `ContextSearchQuery` with `facts` (dict), optional `scope`, `page`, `page_size`. |

---

## Evaluation

Endpoints in `api/v1/evaluation.py`. Router prefix: `/api/v1/evaluate`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/evaluate` | Full code-aware evaluation. Accepts unified diffs, file lists, or free-form facts. Runs the 4-stage pipeline (context assembly, rule selection, LLM-as-Judge, verdict aggregation). Returns `EvaluateResponse`. |
| POST | `/api/v1/evaluate/quick` | Simplified non-code evaluation. Body: `QuickEvaluateRequest` with `action` (string) and optional `scope`. Internally wraps the action as `facts={"action": action}`. |
| POST | `/api/v1/evaluate/applicable-rules` | Rule discovery without running LLM evaluation. Body: `ApplicableRulesRequest` with `file_paths`, `repository`, `scope`. Returns list of rule dicts that would apply. |
| GET | `/api/v1/evaluate/{id}` | Retrieve a past evaluation result by ID. |

### EvaluateRequest body

```json
{
  "diff": "unified diff text (optional)",
  "files": [{"path": "src/foo.py", "content": "..."}],
  "facts": {"key": "value"},
  "intent": "What the change does",
  "scope": "engineering/python",
  "repository": "my-repo",
  "mode": "preflight",
  "max_rules": 20,
  "severity_min": "MEDIUM"
}
```

### EvaluateResponse body

```json
{
  "evaluation_id": "uuid",
  "overall_verdict": "ALLOW | DENY | NEEDS_CONFIRMATION",
  "rule_verdicts": [
    {
      "rule_id": "uuid",
      "rule_statement": "...",
      "verdict": "DENY",
      "confidence": 0.92,
      "reasoning": "...",
      "issue_description": "...",
      "fix_suggestion": "...",
      "locations": [
        {
          "file_path": "src/api/handler.py",
          "start_line": 42,
          "end_line": 45,
          "function_name": "process_refund",
          "snippet": "..."
        }
      ]
    }
  ],
  "violations": [],
  "warnings": [],
  "rules_evaluated": 8,
  "rules_passed": 6,
  "rules_violated": 1,
  "rules_uncertain": 1,
  "fix_summary": "Fix 1 violation(s):\n  1. Add Pydantic model for input validation",
  "model_ids_used": ["gemini-3-flash-preview"],
  "total_latency_ms": 2340,
  "timestamp": "2026-04-26T10:00:00Z"
}
```

---

## Intent

Endpoint in `api/v1/intent.py`. Router prefix: `/api/v1/intent`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/intent` | Accept a natural-language query, classify intent via Gemini, and route to the appropriate handler. Body: `IntentRequest` with `query` (string) and optional `context` (dict). Supported intents: `lookup_rule`, `check_compliance`, `find_conflicts`, `explain_rule`, `simulate_change`. Falls back to fulltext search if Gemini is unavailable. |

---

## Documents and Extraction

Endpoints in `api/v1/extraction.py`. Router prefix: `/api/v1/documents`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/documents/upload` | Upload a document for rule extraction. Multipart file upload. Stores locally and creates a `DocumentModel` record. Returns `document_id`, filename, mime_type, size. Status 200. |
| POST | `/api/v1/documents/{document_id}/extract` | Trigger LLM-powered rule extraction on an uploaded document. Runs the `ExtractionPipeline` with Gemini. Returns `extraction_id`, candidate rules with statements/modality/severity/confidence, and `model_id`. |
| GET | `/api/v1/documents/extractions/{extraction_id}` | Get extraction results by ID. Returns candidates, status (`PENDING_REVIEW` or `REVIEWED`), model_id. |
| POST | `/api/v1/documents/extractions/{extraction_id}/review` | Review extraction results. Body: `CandidateReviewRequest` with `approved_indices` (list of ints) and `edits` (dict of index to `RuleCreate`). Approved candidates become rules. Returns count of rules created and their IDs. |

---

## Intelligence

Endpoints in `api/v1/intelligence.py`. Router prefix: `/api/v1/intelligence`.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/intelligence/dashboard` | Corpus-wide intelligence dashboard. Returns health summary, evaluation volume, verdict distribution. |
| GET | `/api/v1/intelligence/health` | Paginated rule health scores. Query params: `page`, `page_size` (max 200), `sort_by` (default `overall_score`). Health dimensions: completeness, freshness, activity. Note: `clarity` and `test_coverage` dimensions are currently hardcoded to 50.0. |
| GET | `/api/v1/intelligence/health/{rule_id}` | Detailed health breakdown for a single rule. Returns per-dimension scores. |
| GET | `/api/v1/intelligence/analytics` | Corpus-wide evaluation analytics for a given period. Query param: `period_days` (default 30, max 365). |
| GET | `/api/v1/intelligence/analytics/{rule_id}` | Per-rule evaluation analytics. Fire rate, deny rate, trends over time. Query param: `period_days`. |
| GET | `/api/v1/intelligence/recommendations` | Active improvement recommendations, prioritized. Query params: `status` (default `open`), `page`, `page_size`. |

### Implementation Notes

- Health scoring works for `completeness`, `freshness`, and `activity` dimensions.
- `clarity` and `test_coverage` dimensions are **hardcoded to 50.0** -- not yet implemented.
- Drift detection is **not implemented**.

---

## Gateway

Endpoints in `gateway/router.py`. Router prefix: `/api/v1/gateway`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/gateway/ingest/{source}` | Receive a webhook from an external source. Path param: `source` (github, slack, generic). Normalizes the payload, matches against enabled enforcement policies, runs the real evaluation engine for each matched policy, and returns per-policy verdicts. |
| POST | `/api/v1/gateway/ingest` | Receive a generic webhook event. Body: `WebhookIngestRequest` with `event_type` and `payload`. |
| POST | `/api/v1/gateway/policies` | Create an enforcement policy. Body: `PolicyCreate` with name, event_source, event_type_pattern, rule_scope, evaluation_mode, on_deny actions, etc. Status 201. |
| GET | `/api/v1/gateway/policies` | List enforcement policies. Query param: `enabled_only` (default false). |
| GET | `/api/v1/gateway/evaluations` | List recent gateway evaluations. Paginated (page, page_size). Returns evaluation ID, policy ID, event source/type, verdict, latency, timestamp. |

### Implementation Notes

- Webhook normalization, policy matching, and verdict from the real evaluation engine all work.
- **NOT IMPLEMENTED**: Action execution on DENY verdict (webhook callbacks, Slack notifications, blocking). The `actions_taken` field is hardcoded to an empty list `[]`.

---

## Integrations

Endpoint in `integrations/github/router.py`. Router prefix: `/api/v1/integrations`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/integrations/webhooks/github` | GitHub webhook receiver. Verifies `X-Hub-Signature-256`, parses event type, processes `pull_request.opened` and `pull_request.synchronize` events through the evaluation engine. Returns verdict and formatted review comment. |

---

## Error Responses

All application errors return structured JSON:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Rule not found: <uuid>"
  }
}
```

Standard HTTP status codes are used. The custom exception hierarchy under `core/errors.py` maps to appropriate status codes. Unhandled exceptions return 500 with `code: "INTERNAL_ERROR"`.

---

## Authentication

The API does not currently implement authentication. In production, add an auth middleware or API gateway in front of the server. The GitHub webhook endpoint uses HMAC-SHA256 signature verification via `GITHUB_WEBHOOK_SECRET`.

---

## CORS

CORS is configured via the `cors_origins` setting. Default allows all origins in development. The `X-Request-ID` header is exposed for request tracing.

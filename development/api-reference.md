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
| POST | `/api/v1/evaluate` | Full code-aware evaluation. Accepts unified diffs, file lists, or free-form facts. Runs the 4-stage pipeline (context assembly, rule selection, LLM-as-Judge, verdict aggregation). Supports `environment` parameter for snapshot-based evaluation. Returns `EvaluateResponse`. |
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
  "severity_min": "MEDIUM",
  "environment": "production"
}
```

The `environment` field is optional. When set, evaluation uses the snapshot deployed to that environment instead of the live rule corpus.

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

## Discovery

Endpoints in `api/v1/discovery.py`. Router prefix: `/api/v1/discover`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/discover/scan` | Start a discovery scan. Body: `ScanRequest` with `sources` (list of source types: `code_patterns`, `linter_config`, `claude_md`), `file_contents` (dict mapping file paths to content strings), optional `repository`. Runs analyzers to find implicit conventions. Status 201. Returns `scan_id`, `status`, `candidates_found`. |
| GET | `/api/v1/discover/scan/{scan_id}` | Get scan status and results. Returns `scan_id`, `status`, `candidates_found`. |
| GET | `/api/v1/discover/candidates` | List candidates for a scan. Query params: `scan_id` (required), `status` (optional filter: `pending`, `approved`, `dismissed`). Returns list of candidate dicts with `id`, `statement`, `modality`, `severity`, `confidence`, `source_type`, `status`. |
| POST | `/api/v1/discover/candidates/{candidate_id}/approve` | Approve a candidate and create a rule from it. Returns dict with created rule info. |
| POST | `/api/v1/discover/candidates/{candidate_id}/dismiss` | Dismiss a candidate, marking it as not useful. Returns confirmation dict. |

### Discovery Analyzers

The scan delegates to three source-specific analyzers:

- **`claude_md`**: Parses CLAUDE.md files for MUST/SHOULD/MUST_NOT directives using regex patterns. Extracts heading context as scope.
- **`linter_config`**: Parses `ruff.toml`, `.eslintrc.json`, `tsconfig.json` for enforced coding standards.
- **`code_patterns`**: Detects conventions from code (test naming patterns, docstring coverage thresholds).

After analysis, a `PatternDetector` deduplicates similar candidates and boosts confidence when the same pattern is found across multiple sources.

---

## Feedback

Endpoints in `api/v1/feedback.py`. Router prefix: `/api/v1/feedback`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/feedback/corrections` | Submit a correction for analysis. Body: `CorrectionRequest` with `original_diff`, `corrected_diff`, `file_paths`, optional `repository`, `pr_number`, `evaluation_ids`. Compares diffs and extracts a semantic delta. Returns `CorrectionResponse`. |
| GET | `/api/v1/feedback/corrections` | List corrections with pagination. Query params: `status` (optional), `page` (default 1), `page_size` (default 20, max 100). Returns `CorrectionListResponse` with items, total, page, page_size. |
| POST | `/api/v1/feedback/corrections/{correction_id}/approve` | Approve a correction, optionally creating a new rule from the pattern. Returns dict with status and optional `rule_id`. |
| POST | `/api/v1/feedback/corrections/{correction_id}/dismiss` | Dismiss a correction without taking action. Returns confirmation dict. |
| GET | `/api/v1/feedback/stats` | Aggregate statistics about the correction feedback loop. Returns `FeedbackStatsResponse`. |

---

## Federation

Endpoints in `api/v1/federation.py`. Router prefix: `/api/v1/federations`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/federations` | Create a federation node. Body: `FederationCreate` with `name`, `level`, optional `parent_id`, `description`, `default_scope`. Status 201. Returns `FederationResponse`. |
| GET | `/api/v1/federations` | List all federation nodes as a tree structure. Returns list of root nodes with nested children. |
| GET | `/api/v1/federations/{federation_id}` | Get a federation node with its children and direct rules. |
| POST | `/api/v1/federations/{federation_id}/rules` | Add a rule to a federation node. Body: `AddRuleRequest` with `rule_id` and optional `override_parent_rule_id`. Status 201. |
| DELETE | `/api/v1/federations/{federation_id}/rules/{rule_id}` | Remove a rule from a federation node. |
| GET | `/api/v1/federations/{federation_id}/effective-rules` | Resolve the effective rule set for a federation node. Walks the ancestor chain and applies overrides to produce the final set of rules that apply at this level. Returns list of `EffectiveRuleResponse`. |
| GET | `/api/v1/federations/{federation_id}/diff/{other_id}` | Compare the effective rule sets of two federation nodes. Returns dict with `only_in_a`, `only_in_b`, and `common` rule lists. |

### Federation Concepts

- **Federation nodes** form a hierarchy (e.g., `Organization > Division > Team`). Each node has a `level` and optional `parent_id`.
- **Rule membership** associates rules with federation nodes. A rule at a parent level applies to all children unless overridden.
- **Override**: A child node can add a rule with `override_parent_rule_id` to replace a parent's rule at that level.
- **Effective rules**: The resolver walks from the target node up to the root, collecting rules and applying overrides, producing the final merged set.

---

## Playground

Endpoints in `api/v1/playground.py`. Router prefix: `/api/v1/playground`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/playground/evaluate` | Sandbox evaluation of a rule statement without persistence. Body: `PlaygroundEvalRequest` with `rule_statement`, `rule_modality`, `rule_severity`, `sample_code` (optional), `sample_facts` (optional). Returns `PlaygroundEvalResponse` with verdict, confidence, reasoning. |
| POST | `/api/v1/playground/rules/{rule_id}/test-cases` | Create a new test case for a rule. Body: `TestCaseCreate` with `name`, `sample_input`, `input_type` (code/facts), `expected_verdict`. Returns `TestCaseResponse`. |
| GET | `/api/v1/playground/rules/{rule_id}/test-cases` | List all test cases for a rule. Returns list of `TestCaseResponse`. |
| DELETE | `/api/v1/playground/rules/{rule_id}/test-cases/{test_case_id}` | Delete a test case. Returns status confirmation. |
| POST | `/api/v1/playground/rules/{rule_id}/test-cases/run` | Run all test cases for a rule and return results. Returns `TestRunResult` with total, passing, failing counts and per-case results. |
| POST | `/api/v1/playground/rules/{rule_id}/test-cases/generate` | Generate test cases via Gemini and persist them. Body: `TestGenerateRequest` with `count`. Returns list of generated `TestCaseResponse`. |

### Playground Concepts

- **Sandbox evaluation**: Runs a rule statement against sample code or facts through the LLM-as-Judge without creating any database records. Useful for drafting and iterating on rules before committing them.
- **Test cases**: Persistent test inputs attached to a rule. Each has an expected verdict (ALLOW/DENY/NEEDS_CONFIRMATION). Running tests compares the LLM verdict against expectations to measure rule quality.
- **Test generation**: Uses Gemini to automatically generate test cases for a given rule, producing both positive (should ALLOW) and negative (should DENY) examples.

---

## Alerts

Endpoints in `api/v1/alerts.py`. Router prefix: `/api/v1/alerts`.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/alerts` | List alerts with optional status filter and pagination. Query params: `status` (optional, e.g., `active`, `acknowledged`, `resolved`), `page` (default 1), `page_size` (default 20, max 100). Returns `AlertListResponse` with items and total count. |
| GET | `/api/v1/alerts/{alert_id}` | Fetch a single alert by ID. Returns `AlertResponse`. |
| POST | `/api/v1/alerts/{alert_id}/acknowledge` | Acknowledge an alert (sets status to `acknowledged`). Returns updated `AlertResponse`. |
| POST | `/api/v1/alerts/{alert_id}/resolve` | Resolve an alert (sets status to `resolved`, records `resolved_at` timestamp). Returns updated `AlertResponse`. |

### Alert Types

Alerts are generated by background workers, not directly by API calls:

| Alert Type | Source | Trigger |
|---|---|---|
| `health_decline` | `compute_health_scores` cron | Rule overall health score drops below 40 |
| `dormant_rule` | `compute_health_scores` cron | Rule has had zero evaluations in 90 days |
| `high_deny_rate` | `generate_recommendations_task` cron | Rule deny rate exceeds 50% with at least 10 evaluations |

---

## Snapshots

Endpoints in `api/v1/snapshots.py`. Router prefix: `/api/v1/snapshots`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/snapshots` | Create a new rule-set snapshot. Body: `SnapshotCreate` with `name`, `scope_filter` (optional), `description` (optional), `created_by` (optional). Captures current rules matching the scope filter. Status 201. Returns `SnapshotResponse`. |
| GET | `/api/v1/snapshots` | List all snapshots. Returns list of `SnapshotResponse`. |
| GET | `/api/v1/snapshots/{snapshot_id}` | Get a single snapshot by ID. Returns `SnapshotResponse` with name, description, scope_filter, rule_count, created_at. |
| POST | `/api/v1/snapshots/{snapshot_id}/deploy` | Deploy a snapshot to an environment. Body: `DeployRequest` with `environment` (string, e.g., "production", "staging") and `deployed_by`. Status 201. Returns `DeploymentResponse`. |
| POST | `/api/v1/snapshots/{snapshot_id}/rollback` | Roll back the most recent active deployment of this snapshot. Finds the active deployment, deactivates it, and reactivates the previous deployment for the same environment. Returns `DeploymentResponse`. |
| POST | `/api/v1/snapshots/{snapshot_id}/simulate` | Simulate the impact of deploying a snapshot. Body: `SimulateRequest` with `compare_to` (environment) and `sample_size`. Returns `SimulateResponse` with impact analysis. |
| GET | `/api/v1/snapshots/deployments` | List all deployments across environments. Returns list of `DeploymentResponse`. |
| GET | `/api/v1/snapshots/deployments/{environment}` | Get the active deployment for a specific environment. Returns `DeploymentResponse` or null if no active deployment. |

### Snapshot Concepts

- **Snapshots** capture the current state of rules (optionally filtered by scope) as an immutable point-in-time record. The `rule_snapshot` field stores serialized rule data.
- **Deployments** associate a snapshot with a named environment (e.g., `production`, `staging`). Only one deployment can be active per environment at a time.
- **Evaluation integration**: When the evaluation API receives an `environment` parameter, it looks up the active deployment for that environment and evaluates against the snapshotted rules instead of the live corpus.
- **Rollback**: Deactivates the current deployment and reactivates the previous one for the same environment.
- **Simulation**: Compares a snapshot against the currently deployed rules in an environment to predict what would change.

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

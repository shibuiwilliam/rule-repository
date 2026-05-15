# Evaluate API

> **Note:** For new integrations, prefer the [Universal Submissions API](submissions.md) (`POST /api/v1/submissions`), which accepts any `EvaluationSubject` kind (code changes, business events, documents, transactions, communications, decision requests). The `/evaluate` endpoint below remains for backward compatibility and internally constructs a `code_change` subject forwarded to the submissions pipeline.

## POST /api/v1/evaluate

The core evaluation endpoint. Accepts code changes, file information, or free-form facts and returns per-rule verdicts with code locations and fix suggestions.

### Request Body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `diff` | string | No | null | Unified diff text. |
| `files` | list of `{path, content?}` | No | null | Files to evaluate. |
| `facts` | dict | No | null | Free-form context (key-value pairs). |
| `intent` | string | No | null | Description of the change or action. |
| `scope` | string | No | null | Rule scope filter (e.g., `"engineering/backend"`). |
| `repository` | string | No | null | Repository identifier for scope matching. |
| `mode` | string | No | `"preflight"` | `preflight` (before action) or `posthoc` (after action). |
| `max_rules` | int | No | 20 | Maximum rules to evaluate (1--100). |
| `severity_min` | string | No | `"MEDIUM"` | Minimum severity to include (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`). |

### Response

| Field | Type | Description |
|---|---|---|
| `evaluation_id` | string | Unique evaluation ID for audit trail. |
| `overall_verdict` | string | `ALLOW`, `DENY`, or `NEEDS_CONFIRMATION`. |
| `rule_verdicts` | list | All per-rule verdicts. |
| `violations` | list | Verdicts with DENY. |
| `warnings` | list | Verdicts with NEEDS_CONFIRMATION. |
| `rules_evaluated` | int | Total rules evaluated. |
| `rules_passed` | int | Rules that returned ALLOW. |
| `rules_violated` | int | Rules that returned DENY. |
| `rules_uncertain` | int | Rules that returned NEEDS_CONFIRMATION. |
| `fix_summary` | string | Consolidated fix suggestions. |
| `model_ids_used` | list of string | Gemini models used during evaluation. |
| `total_latency_ms` | int | End-to-end evaluation time in milliseconds. |
| `timestamp` | datetime | When the evaluation ran. |

Each item in `rule_verdicts`, `violations`, and `warnings` has:

| Field | Type | Description |
|---|---|---|
| `rule_id` | string | The rule's ID. |
| `rule_statement` | string | The rule text. |
| `verdict` | string | ALLOW, DENY, or NEEDS_CONFIRMATION. |
| `confidence` | float | Model confidence (0.0--1.0). |
| `reasoning` | string | Why this verdict was reached. |
| `issue_description` | string | What the issue is (for violations). |
| `fix_suggestion` | string | How to fix the issue. |
| `locations` | list | Code locations (file_path, start_line, end_line, function_name, snippet). |

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "diff": "--- a/src/api/handler.py\n+++ b/src/api/handler.py\n@@ -10,6 +10,8 @@\n def handle_request(data):\n+    print(data)\n+    result = process(data)\n     return result",
    "intent": "Add logging to request handler",
    "scope": "engineering/backend",
    "mode": "preflight",
    "severity_min": "MEDIUM"
  }'
```

### Example Response

```json
{
  "evaluation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "overall_verdict": "DENY",
  "rule_verdicts": [
    {
      "rule_id": "rule-001",
      "rule_statement": "All server code must use structured logging via structlog. print() is not allowed.",
      "verdict": "DENY",
      "confidence": 0.95,
      "reasoning": "The diff adds a print() call in handler.py line 12, which violates the structured logging requirement.",
      "issue_description": "print() used instead of structured logging",
      "fix_suggestion": "Replace print(data) with logger.info('request_received', data=data) using structlog.",
      "locations": [
        {
          "file_path": "src/api/handler.py",
          "start_line": 12,
          "end_line": 12,
          "function_name": "handle_request",
          "snippet": "print(data)"
        }
      ]
    }
  ],
  "violations": [
    { "...same as above..." : "" }
  ],
  "warnings": [],
  "rules_evaluated": 8,
  "rules_passed": 7,
  "rules_violated": 1,
  "rules_uncertain": 0,
  "fix_summary": "Replace print() with structlog logger calls.",
  "model_ids_used": ["gemini-3-flash-preview"],
  "total_latency_ms": 1240,
  "timestamp": "2026-04-26T10:30:00Z"
}
```

## POST /api/v1/evaluate/quick

Simplified evaluation for non-code actions. Accepts a plain-text action description.

### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `action` | string | Yes | The action to evaluate (1--5000 characters). |
| `scope` | string | No | Rule scope filter. |

### Example

```bash
curl -X POST http://localhost:8000/api/v1/evaluate/quick \
  -H "Content-Type: application/json" \
  -d '{"action": "Register 55 hours of overtime for employee E001 in April", "scope": "hr/attendance"}'
```

The response format is the same as the full evaluate endpoint.

## POST /api/v1/evaluate/applicable-rules

Returns rules that apply to given file paths without running evaluation. Useful for discovering which rules are relevant before making changes.

### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `file_paths` | list of string | No | File paths to check. |
| `repository` | string | No | Repository identifier. |
| `scope` | string | No | Rule scope filter. |

### Example

```bash
curl -X POST http://localhost:8000/api/v1/evaluate/applicable-rules \
  -H "Content-Type: application/json" \
  -d '{"file_paths": ["src/api/handler.py", "tests/test_handler.py"], "scope": "engineering"}'
```

Returns a list of matching rule objects.

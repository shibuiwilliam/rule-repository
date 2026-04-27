# Playground API

The Playground API provides sandbox evaluation and test case management. All endpoints are prefixed with `/api/v1`.

## Sandbox Evaluation

### POST /api/v1/playground/evaluate

Evaluate sample code against an inline rule definition. No audit log, no cache, no persistence.

**Request:**

```json
{
  "rule_statement": "All public functions must have type hints on parameters and return values",
  "rule_modality": "MUST",
  "rule_severity": "ERROR",
  "sample_code": "def greet(name):\n    return f'Hello, {name}!'"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `rule_statement` | string | yes | The natural-language rule to evaluate against |
| `rule_modality` | string | yes | `MUST`, `SHOULD`, or `MAY` |
| `rule_severity` | string | yes | `ERROR`, `WARNING`, or `INFO` |
| `sample_code` | string | yes | Code or text to evaluate |

**Response:**

```json
{
  "verdict": "DENY",
  "confidence": 0.95,
  "reasoning": "The function 'greet' lacks a type hint on parameter 'name' and has no return type annotation.",
  "fix_suggestion": "def greet(name: str) -> str:\n    return f'Hello, {name}!'",
  "locations": [
    {
      "line": 1,
      "column": 0,
      "snippet": "def greet(name):"
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `verdict` | string | `ALLOW`, `DENY`, or `WARN` |
| `confidence` | float | Model confidence (0.0--1.0) |
| `reasoning` | string | Explanation of the verdict |
| `fix_suggestion` | string or null | Suggested fix if the verdict is DENY or WARN |
| `locations` | array | Code locations relevant to the verdict |

## Test Cases

### POST /api/v1/rules/{rule_id}/test-cases

Create a test case for a rule.

**Request:**

```json
{
  "name": "Missing type hints",
  "input": "def add(a, b):\n    return a + b",
  "expected_verdict": "DENY"
}
```

### GET /api/v1/rules/{rule_id}/test-cases

List all test cases for a rule. Returns an array of test case objects.

### DELETE /api/v1/rules/{rule_id}/test-cases/{test_case_id}

Delete a specific test case.

### POST /api/v1/rules/{rule_id}/test-cases/run

Run all test cases for a rule through sandbox evaluation. Returns per-case results and an overall pass rate.

**Response:**

```json
{
  "rule_id": "ENG-042",
  "total": 5,
  "passed": 4,
  "failed": 1,
  "results": [
    {
      "test_case_id": "tc-001",
      "name": "Missing type hints",
      "expected_verdict": "DENY",
      "actual_verdict": "DENY",
      "passed": true
    },
    {
      "test_case_id": "tc-002",
      "name": "Fully typed function",
      "expected_verdict": "ALLOW",
      "actual_verdict": "WARN",
      "passed": false,
      "reasoning": "Return type is annotated but uses 'Any', which is discouraged."
    }
  ]
}
```

### POST /api/v1/rules/{rule_id}/test-cases/generate

Generate test cases using Gemini. The LLM analyzes the rule statement and produces synthetic test cases that cover typical, edge, and boundary scenarios.

**Response:** an array of generated test case objects (not yet persisted). The caller can review and selectively create them via `POST /rules/{rule_id}/test-cases`.

## See Also

- [Rule Playground Architecture](../architecture/playground.md) -- design overview
- [Evaluate API](evaluate.md) -- production evaluation endpoint

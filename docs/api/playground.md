# Playground API

The Playground API provides sandbox evaluation and test case management. All endpoints are prefixed with `/api/v1`.

## Sandbox Evaluation

### POST /api/v1/playground/evaluate

Evaluate sample code or a scenario against an inline rule definition. No audit log, no cache, no persistence.

The endpoint accepts two input modes: **code** (via `sample_code`) and **scenario** (via `sample_facts`). Each mode triggers a different evaluation prompt optimized for that input type.

**Code evaluation request:**

```json
{
  "rule_statement": "All public functions must have type hints on parameters and return values",
  "rule_modality": "MUST",
  "rule_severity": "MEDIUM",
  "sample_code": "def greet(name):\n    return f'Hello, {name}!'"
}
```

**Scenario evaluation request:**

```json
{
  "rule_statement": "Monthly overtime must not exceed 45 hours without prior 36-agreement filing",
  "rule_modality": "MUST_NOT",
  "rule_severity": "HIGH",
  "sample_facts": {
    "narrative": "Employee John submitted 52 hours of overtime for April 2026. No 36-agreement has been filed.",
    "employee_id": "E001",
    "overtime_hours": "52",
    "month": "2026-04",
    "agreement_filed": "false"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `rule_statement` | string | yes | The natural-language rule to evaluate against |
| `rule_modality` | string | no | `MUST`, `MUST_NOT`, `SHOULD`, `MAY`, or `INFO` (default: `MUST`) |
| `rule_severity` | string | no | `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` (default: `MEDIUM`) |
| `sample_code` | string | no | Code snippet or unified diff (triggers code evaluation prompt) |
| `sample_facts` | object | no | Key-value facts with optional `narrative` key (triggers scenario evaluation prompt) |

If both `sample_code` and `sample_facts` are provided, `sample_code` takes precedence. If neither is provided, the evaluation runs against an empty context.

**Response:**

```json
{
  "verdict": "DENY",
  "confidence": 0.95,
  "reasoning": "The employee's 52 overtime hours exceed the 45-hour limit, and no 36-agreement has been filed.",
  "issue_description": "Overtime of 52 hours exceeds the 45-hour limit without a 36-agreement.",
  "fix_suggestion": "File a 36-agreement before registering overtime above 45 hours, or reduce overtime to 45 hours or fewer.",
  "locations": []
}
```

| Field | Type | Description |
|---|---|---|
| `verdict` | string | `ALLOW`, `DENY`, or `NEEDS_CONFIRMATION` |
| `confidence` | float | Model confidence (0.0--1.0) |
| `reasoning` | string | Explanation of the verdict |
| `issue_description` | string | What's wrong (empty string if ALLOW) |
| `fix_suggestion` | string or null | Suggested fix if the verdict is DENY or NEEDS_CONFIRMATION |
| `locations` | array | Code locations relevant to the verdict (typically empty for scenario evaluations) |

## Test Cases

### POST /api/v1/rules/{rule_id}/test-cases

Create a test case for a rule.

**Request:**

```json
{
  "name": "Missing type hints",
  "sample_input": "def add(a, b):\n    return a + b",
  "input_type": "code",
  "expected_verdict": "DENY"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Human-readable label |
| `sample_input` | string | yes | Code snippet or scenario text |
| `input_type` | string | no | `"code"` (default) or `"facts"` — determines how the test runner evaluates the input |
| `expected_verdict` | string | yes | `ALLOW` or `DENY` |

### GET /api/v1/rules/{rule_id}/test-cases

List all test cases for a rule. Returns an array of test case objects.

### DELETE /api/v1/rules/{rule_id}/test-cases/{test_case_id}

Delete a specific test case.

### POST /api/v1/rules/{rule_id}/test-cases/run

Run all test cases for a rule through sandbox evaluation. The `input_type` on each test case determines whether the input is treated as code or facts. Returns per-case results and an overall pass rate.

**Response:**

```json
{
  "total": 5,
  "passing": 4,
  "failing": 1,
  "results": [
    {
      "id": "tc-001",
      "name": "Missing type hints",
      "sample_input": "def add(a, b):\n    return a + b",
      "input_type": "code",
      "expected_verdict": "DENY",
      "last_result": "DENY",
      "passing": true,
      "last_run_at": "2026-04-29T10:30:00Z"
    },
    {
      "id": "tc-002",
      "name": "Fully typed function",
      "sample_input": "def add(a: int, b: int) -> int:\n    return a + b",
      "input_type": "code",
      "expected_verdict": "ALLOW",
      "last_result": "NEEDS_CONFIRMATION",
      "passing": false,
      "last_run_at": "2026-04-29T10:30:01Z"
    }
  ]
}
```

### POST /api/v1/rules/{rule_id}/test-cases/generate

Generate test cases using Gemini. The LLM analyzes the rule statement and produces synthetic test cases that cover compliant and non-compliant scenarios.

**Request:**

```json
{
  "count": 6
}
```

**Response:** an array of generated test case objects (persisted to the database). Each case has a name, sample_input, input_type, and expected_verdict.

## See Also

- [Rule Playground Architecture](../architecture/playground.md) -- design overview
- [Evaluate API](evaluate.md) -- production evaluation endpoint

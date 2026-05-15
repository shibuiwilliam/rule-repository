# Universal Submissions API

The submissions endpoint is the canonical intake for evaluating any `EvaluationSubject` kind. Prefer this over `POST /api/v1/evaluate` for new integrations.

## `POST /api/v1/submissions`

Submit any evaluation subject for compliance checking.

### Request Body

The request uses a Pydantic discriminated union on `subject.kind`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `subject` | object | Yes | The evaluation subject (discriminated by `kind`) |
| `subject.kind` | string | Yes | One of: `code_change`, `business_event`, `document_artifact`, `transaction`, `communication`, `decision_request` |
| `scope` | object | No | Structured scope filter (domain, org_unit, subject_type) |
| `submission_id` | string | No | Idempotency key — same ID returns cached verdict |
| `max_rules` | integer | No | Maximum rules to evaluate (default: 20) |

### Subject Kinds

| Kind | Fields | Example Use Case |
|------|--------|-----------------|
| `code_change` | `diff`, `file_paths`, `repository` | Code review compliance |
| `business_event` | `event_type`, `actor`, `facts`, `timestamp` | HR overtime, leave requests |
| `document_artifact` | `document_id`, `content`, `document_type` | Contract review, policy check |
| `transaction` | `transaction_type`, `amount`, `currency`, `facts` | Expense approval, PO review |
| `communication` | `channel`, `content`, `recipients`, `facts` | Marketing copy, press releases |
| `decision_request` | `decision_type`, `context`, `options` | Policy exceptions, approvals |

### Response

```json
{
  "verdict": "DENY",
  "violations": [
    {
      "rule_id": "...",
      "rule_statement": "...",
      "verdict": "DENY",
      "confidence": 0.95,
      "reasoning": "...",
      "remediation": { ... }
    }
  ],
  "applied_rules": ["..."],
  "deterministic_results": [...],
  "llm_results": [...],
  "evaluation_id": "..."
}
```

### Example: Expense Submission

```bash
curl -X POST http://localhost:8000/api/v1/submissions \
  -H "Content-Type: application/json" \
  -d '{
    "subject": {
      "kind": "transaction",
      "transaction_type": "expense_report",
      "amount": 15000,
      "currency": "JPY",
      "facts": {
        "category": "entertainment",
        "per_person_amount": 7500,
        "attendees": 2,
        "receipt_attached": true
      }
    },
    "scope": {
      "domain": "finance",
      "org_unit": "sales"
    }
  }'
```

### Relationship to Legacy Evaluate Endpoint

The legacy `POST /api/v1/evaluate` endpoint remains for backward compatibility. It internally constructs a `code_change` subject and forwards to the submissions pipeline. New integrations should use `/api/v1/submissions` directly.

# Intent API

## POST /api/v1/intent

The Intent API accepts natural-language questions about rules, classifies the user's intent, and routes the query to the appropriate backend handler. It is the simplest way to query the Rule Repository without knowing the specific REST endpoints.

### Request

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | Natural-language question (1--5000 characters). |
| `context` | dict | No | Optional context to help classify and answer the query. |

### Response

| Field | Type | Description |
|---|---|---|
| `intent` | string | The classified intent type. |
| `result` | dict | Intent-specific result data (varies by intent). |
| `explanation` | string | Human-readable explanation of what was done and why. |

## Supported Intents

The classifier routes queries to one of six intent handlers:

### lookup_rule

Find a specific rule by name, ID, or description.

**Example queries:**

- "What is rule R-2024-0042?"
- "Show me the overtime limit rule"
- "Find the rule about password complexity"

### check_compliance

Evaluate whether a specific action or situation complies with applicable rules.

**Example queries:**

- "Is it okay to register 55 hours of overtime this month?"
- "Can we deploy on Friday afternoon?"
- "Does this contract clause comply with our procurement policy?"

### find_conflicts

Identify rules that conflict with each other or with a proposed change.

**Example queries:**

- "Are there any rules that conflict with our new remote work policy?"
- "What rules contradict the 40-hour overtime limit?"
- "Find conflicting rules in the engineering guidelines"

### explain_rule

Get a detailed explanation of a rule, including its rationale, source, and relationships.

**Example queries:**

- "Why do we have the structured logging requirement?"
- "Explain the background of the overtime policy"
- "What is the rationale behind the code review rule?"

### search_rules

Search for rules matching a topic, keyword, or category.

**Example queries:**

- "What rules apply to API design?"
- "Show me all CRITICAL severity rules"
- "Find rules related to data retention"

### simulate_change

Predict the impact of a proposed rule change on the existing corpus and historical evaluations.

**Example queries:**

- "What would happen if we changed the overtime limit from 45 to 60 hours?"
- "How many evaluations would change if we retired the print() ban?"
- "Simulate making the documentation rule CRITICAL severity"

## Example

### Request

```bash
curl -X POST http://localhost:8000/api/v1/intent \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the rules for refunding orders over $500?",
    "context": {"department": "customer-support"}
  }'
```

### Response

```json
{
  "intent": "search_rules",
  "result": {
    "rules": [
      {
        "id": "rule-refund-001",
        "statement": "Refunds exceeding $500 require manager approval and must be processed within 5 business days.",
        "modality": "MUST",
        "severity": "HIGH",
        "scope": ["customer-support/refunds"]
      }
    ],
    "total": 1
  },
  "explanation": "Found 1 rule related to refund thresholds in the customer-support scope."
}
```

## Fallback Behavior

If the Gemini API is unavailable, the Intent API falls back to a keyword-based full-text search. The response will include:

```json
{
  "intent": "search_rules",
  "result": { "..." : "" },
  "explanation": "Gemini unavailable -- defaulting to fulltext search"
}
```

This ensures the endpoint remains functional even when the LLM is down, though intent classification and smart routing are degraded to simple text matching.

# Feedback API

The Feedback API captures correction data from developer workflows (PR reviews, code changes) and uses it to improve the rule corpus over time.

## Endpoints

### Submit a correction

```
POST /api/v1/feedback/corrections
```

**Request body:**

```json
{
  "original_diff": "- def process(data):\n+ def process(data: dict) -> None:",
  "corrected_diff": "- def process(data):\n+ def process(data: dict[str, Any]) -> Result:",
  "file_paths": ["src/services/processor.py"],
  "repository": "my-org/my-project",
  "context": "Reviewer corrected the type hints to be more specific"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `original_diff` | string | Yes | The diff as originally proposed or generated. |
| `corrected_diff` | string | Yes | The diff after human correction. |
| `file_paths` | array of strings | Yes | Files involved in the correction. |
| `repository` | string | No | Repository identifier. |
| `context` | string | No | Free-text explanation of the correction. |

**Response (201 Created):**

```json
{
  "correction_id": "f1a2b3c4-...",
  "analysis": {
    "type": "improve_existing",
    "matched_rule_id": "r1s2t3u4-...",
    "suggestion": "Tighten the type-hint rule to require generic parameters"
  },
  "status": "pending_review"
}
```

### List corrections

```
GET /api/v1/feedback/corrections
```

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | integer | 1 | Page number. |
| `page_size` | integer | 20 | Items per page (max 100). |
| `status` | string | all | Filter by `pending_review`, `approved`, `dismissed`. |
| `type` | string | all | Filter by `new_rule`, `improve_existing`, `adjust_scope`. |

**Response:**

```json
{
  "corrections": [
    {
      "id": "f1a2b3c4-...",
      "type": "improve_existing",
      "matched_rule_id": "r1s2t3u4-...",
      "status": "pending_review",
      "file_paths": ["src/services/processor.py"],
      "created_at": "2026-04-26T10:00:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20
}
```

### Approve a correction

```
POST /api/v1/feedback/corrections/{correction_id}/approve
```

Applies the correction's suggestion -- either creating a new rule, updating an existing rule, or adjusting a rule's scope.

**Response (200 OK):**

```json
{
  "correction_id": "f1a2b3c4-...",
  "status": "approved",
  "action_taken": "Rule r1s2t3u4 updated with tighter type-hint requirements"
}
```

### Dismiss a correction

```
POST /api/v1/feedback/corrections/{correction_id}/dismiss
```

**Response (200 OK):**

```json
{
  "correction_id": "f1a2b3c4-...",
  "status": "dismissed"
}
```

### Get feedback stats

```
GET /api/v1/feedback/stats
```

**Response:**

```json
{
  "total_corrections": 142,
  "by_type": {
    "new_rule": 23,
    "improve_existing": 89,
    "adjust_scope": 30
  },
  "by_status": {
    "pending_review": 12,
    "approved": 105,
    "dismissed": 25
  },
  "rules_created": 18,
  "rules_improved": 67,
  "top_violated_rules": [
    {
      "rule_id": "r1s2t3u4-...",
      "statement": "All public functions must have type hints",
      "correction_count": 14
    }
  ]
}
```

# Discovery API

The Discovery API enables automated rule discovery from project artifacts such as configuration files, linter configs, and documentation.

## Endpoints

### Start a discovery scan

```
POST /api/v1/discover/scan
```

**Request body:**

```json
{
  "sources": ["policy_document", "claude_md", "linter_config", "code_patterns"],
  "file_contents": {
    "CLAUDE.md": "# CLAUDE.md\n\n## Coding Conventions\n- Use snake_case...",
    ".eslintrc.json": "{\"rules\": {\"no-console\": \"error\"}}"
  },
  "repository": "my-org/my-project"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `sources` | array of strings | Yes | Analyzer types to run. Values: `policy_document`, `claude_md`, `linter_config`, `code_patterns`. |
| `file_contents` | object | Yes | Map of file paths to their contents. |
| `repository` | string | No | Repository identifier for provenance tracking. |

**Response (202 Accepted):**

```json
{
  "scan_id": "a1b2c3d4-...",
  "status": "pending",
  "created_at": "2026-04-26T10:00:00Z"
}
```

### Get scan status

```
GET /api/v1/discover/scans/{scan_id}
```

**Response:**

```json
{
  "scan_id": "a1b2c3d4-...",
  "status": "completed",
  "candidates_count": 12,
  "created_at": "2026-04-26T10:00:00Z",
  "completed_at": "2026-04-26T10:00:15Z"
}
```

Status values: `pending`, `running`, `completed`, `failed`.

### List candidates

```
GET /api/v1/discover/scans/{scan_id}/candidates
```

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `status` | string | all | Filter by `pending`, `approved`, `dismissed`. |
| `min_confidence` | float | 0.0 | Minimum confidence score (0.0 -- 1.0). |

**Response:**

```json
{
  "candidates": [
    {
      "id": "c1d2e3f4-...",
      "statement": "All public API functions must have type hints.",
      "confidence": 0.92,
      "source_file": "CLAUDE.md",
      "source_line": 45,
      "suggested_metadata": {
        "scope": "backend",
        "modality": "MUST",
        "severity": "medium",
        "tags": ["typing", "api"]
      },
      "status": "pending"
    }
  ],
  "total": 12
}
```

### Approve a candidate

```
POST /api/v1/discover/candidates/{candidate_id}/approve
```

**Request body (optional):**

```json
{
  "statement": "All public API functions must have type hints and Google-style docstrings.",
  "metadata_overrides": {
    "severity": "high"
  }
}
```

Approving a candidate creates a rule through the standard rule creation flow. The response returns the created rule.

**Response (201 Created):**

```json
{
  "rule_id": "r1s2t3u4-...",
  "candidate_id": "c1d2e3f4-...",
  "status": "approved"
}
```

### Dismiss a candidate

```
POST /api/v1/discover/candidates/{candidate_id}/dismiss
```

**Request body (optional):**

```json
{
  "reason": "Too specific to be a general rule"
}
```

**Response (200 OK):**

```json
{
  "candidate_id": "c1d2e3f4-...",
  "status": "dismissed"
}
```

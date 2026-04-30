# Rule Templates & Bulk Import

## Overview

Rule templates are pre-built rule sets for common development scenarios. They provide 10-20 rules each, covering type safety, security, API design, testing, and more. Templates eliminate the cold-start problem — teams get useful rules immediately.

## Available Templates

| Template | Rules | Scope |
|---|---|---|
| `python-fastapi` | 15 | Type hints, Pydantic, async patterns, logging, migrations, CORS |
| `typescript-react` | 12 | Strict mode, hooks, components, state management, error boundaries |
| `security-owasp` | 10 | OWASP Top 10: injection, auth, data exposure, CSRF, rate limiting |
| `api-design` | 10 | REST conventions, versioning, pagination, error responses, status codes |
| `testing-standards` | 10 | Coverage, test isolation, mocking, naming, CI integration |

Templates are YAML files located in `sample_rules/templates/`.

## Importing Templates

Use the bulk import endpoint to load a template's rules:

```bash
# Read the template and POST to the import endpoint
curl -X POST http://localhost:8000/api/v1/rules/import \
  -H "Content-Type: application/json" \
  -d @sample_rules/templates/python-fastapi.yaml
```

Or use the API directly:

```
POST /api/v1/rules/import?project_id=<optional>
```

### Request Body

```json
{
  "version": 1,
  "rules": [
    {
      "statement": "All Python functions MUST have type annotations",
      "modality": "MUST",
      "severity": "HIGH",
      "scope": ["engineering/python"],
      "tags": ["type-safety"],
      "rationale": "Type annotations enable mypy and IDE support"
    }
  ]
}
```

### Response

```json
{
  "created": 15,
  "errors": 0,
  "rule_ids": ["uuid-1", "uuid-2", "..."]
}
```

Each imported rule receives an `["imported"]` tag and starts in DRAFT status with experimental maturity (shadow mode).

## Template Format

Templates use a YAML format with metadata:

```yaml
version: 1
template:
  name: python-fastapi
  description: "Type safety, async patterns, and API conventions"
  tags: ["python", "fastapi"]
rules:
  - statement: "..."
    modality: MUST
    severity: HIGH
    scope: ["engineering/python"]
    tags: ["type-safety"]
    rationale: "..."
```

## Session Context API

For agents that need rules delivered at session startup:

```
GET /api/v1/rules/context?files=src/api/handler.py,tests/test_handler.py&format=instructions
```

Returns rules relevant to the specified files, formatted for LLM context injection (~500 tokens for 15 rules). Scopes are resolved automatically from file paths.

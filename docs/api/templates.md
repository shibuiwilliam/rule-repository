# Rule Templates & Bulk Import

## Overview

Rule templates are pre-built rule sets for common scenarios across engineering, legal, HR, finance, and compliance domains. They provide 10-25 rules each, covering everything from type safety to labor law. Templates eliminate the cold-start problem -- teams get useful rules immediately.

## Available Templates

### Business Domain Templates

| Template | Rules | Domain |
|---|---|---|
| `hr-attendance-jp` | 25 | HR / Labor Law (Japan): overtime caps, 36-Agreement, leave usage, maternity protections, record-keeping |
| `contract-nda-standard` | 15 | Legal / Contracts: NDA definitions, asymmetric obligations, residuals clauses, governing law |
| `expense-policy-standard` | 20 | Finance / Expenses (Japan): approval thresholds, receipt requirements, invoice compliance |
| `bribery-anti-corruption` | 18 | Compliance / Anti-Corruption: FCPA, UK Bribery Act, gift thresholds, due diligence |
| `data-privacy-jp` | 18 | Compliance / Privacy (Japan): APPI requirements, consent, transfers, breach notification |
| `advertising-yakukiho` | 20 | Compliance / Advertising (Japan): pharmaceutical claims, disclaimers, endorsements |

### Engineering Templates

| Template | Rules | Domain |
|---|---|---|
| `python-fastapi` | 15 | Type hints, Pydantic, async patterns, logging, migrations, CORS |
| `typescript-react` | 12 | Strict mode, hooks, components, state management, error boundaries |
| `security-owasp` | 10 | OWASP Top 10: injection, auth, data exposure, CSRF, rate limiting |
| `api-design` | 10 | REST conventions, versioning, pagination, error responses, status codes |
| `testing-standards` | 10 | Coverage, test isolation, mocking, naming, CI integration |
| `documentation-standards` | -- | Documentation conventions and standards |
| `nda-template` | -- | NDA clause review rules |

**Important:** All business-domain templates are marked `expert_reviewed: false (reference only)`. They must be reviewed by qualified domain counsel before use for actual regulatory compliance.

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

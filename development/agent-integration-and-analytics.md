# Agent Integration, Rule Impact Analytics & Templates

This document covers the three strategic enhancements implemented to close adoption gaps: seamless agent integration, ROI measurement, and zero-friction bootstrapping.

---

## 1. Seamless Agent Integration

### File-Aware Scope Resolution

**File**: `apps/server/src/rulerepo_server/services/context_delivery/scope_registry.py`

The `resolve_scopes()` function maps file paths to rule scopes using glob patterns:

```python
from rulerepo_server.services.context_delivery.scope_registry import resolve_scopes

scopes = resolve_scopes("src/api/payments.py")
# → ["engineering/python", "engineering/python/api", "engineering/api"]

scopes = resolve_scopes("tests/test_handler.py")
# → ["engineering/python", "engineering/testing"]
```

**DEFAULT_SCOPE_MAP** contains 20 patterns covering Python, TypeScript, Go, Rust, Java, documentation, Docker, and CI files. Teams override via `custom_map` parameter.

### Session Context API

**Endpoint**: `GET /api/v1/rules/context`

| Parameter | Type | Description |
|---|---|---|
| `files` | string (required) | Comma-separated file paths |
| `format` | string | `instructions` (default), `checklist`, or `detailed` |
| `project_id` | string | Optional project filter |

**Response**:
```json
{
  "rules_text": "## Rules for your current context\n\n### MUST ...",
  "rule_count": 20,
  "scopes_resolved": ["engineering/python", "engineering/api"],
  "files_analyzed": 2
}
```

**Implementation**: Resolves scopes → loads rules via ScopeRegistry → matches by language + path + tags → formats with `format_rules(format_type=...)`.

**Important**: This route is defined before `/{rule_id}` in `api/v1/rules.py` to avoid FastAPI matching "context" as a UUID.

---

## 2. Rule Impact Analytics

### Effectiveness Score

**File**: `apps/server/src/rulerepo_server/services/intelligence/effectiveness.py`

**Endpoint**: `GET /api/v1/intelligence/effectiveness/{rule_id}`

Three metrics combined into a composite score (0-100):

| Metric | Weight | Source | Formula |
|---|---|---|---|
| Precision | 40% | `rules.true_positive_count`, `false_positive_count` | TP / (TP + FP) |
| Prevention rate | 35% | `corrections` table | (corrections_before - corrections_after) / corrections_before |
| Agent adoption | 25% | `evaluations` table | ALLOW count / total evaluations |

### Weekly Governance Digest

**File**: `apps/server/src/rulerepo_server/services/intelligence/digest.py`

**Endpoint**: `GET /api/v1/intelligence/digest`

**Cron job**: `send_weekly_digest` in `workers/settings.py` — runs Monday 9am. Sends JSON payload to `DIGEST_WEBHOOK_URL` if configured.

**Response sections**:
1. `compliance` — current rate, previous rate, change (pp), trend direction, daily trend array
2. `rules` — total count, new this week, maturity distribution
3. `top_violated_rules` — top 5 by deny count in last 7 days
4. `attention_needed` — rules with >30% false positive rate
5. `corrections` — this week's count, pending proposals
6. `pending_actions` — proposals pending + active alerts

### Team Comparison

**Endpoint**: `GET /api/v1/intelligence/comparison`

Returns per-project: `project_id`, `project_name`, `rule_count`, `compliance_rate`. Sorted by compliance rate (highest first).

---

## 3. Zero-Friction Bootstrapping

### Rules Import API

**Endpoint**: `POST /api/v1/rules/import`

**Schema** (`schemas/rule.py`):
```python
class RuleImportItem(BaseModel):
    statement: str
    modality: str = "MUST"
    severity: str = "MEDIUM"
    scope: list[str] = []
    tags: list[str] = []
    rationale: str = ""

class RulesImportRequest(BaseModel):
    version: int = 1
    project: str | None = None
    rules: list[RuleImportItem]
```

**Response**: `{"created": N, "errors": N, "rule_ids": [...]}`

Each imported rule gets an `["imported"]` tag.

### Rule Templates Library

**Directory**: `sample_rules/templates/`

| Template | Rules | Focus |
|---|---|---|
| `python-fastapi.yaml` | 15 | Type hints, Pydantic, async, logging, migrations, CORS |
| `typescript-react.yaml` | 12 | Strict mode, hooks, components, state, error boundaries |
| `security-owasp.yaml` | 10 | Injection, auth, data exposure, CSRF, rate limiting |
| `api-design.yaml` | 10 | Versioning, pagination, error responses, status codes |
| `testing-standards.yaml` | 10 | Coverage, isolation, mocking, naming, CI |

**Format**: Each file has `version`, `template` (name, description, tags), and `rules` array. Import via `POST /api/v1/rules/import` with the rules array.

---

## Configuration

| Env Var | Default | Purpose |
|---|---|---|
| `DIGEST_WEBHOOK_URL` | (empty) | URL for weekly digest delivery (Slack, email, etc.) |

---

## Planned Extensions

- **CLAUDE.md generator** (`rulerepo-context update`): Auto-maintain a `## Rules` section in project CLAUDE.md
- **`rulerepo init`**: Standalone CLI that scans repo → generates rules.yaml using discovery analyzers
- **Frontend onboarding wizard**: When zero rules exist, guide user through scan → review → activate flow
- **Template CLI**: `rulerepo templates list` / `apply` commands for terminal-based template management

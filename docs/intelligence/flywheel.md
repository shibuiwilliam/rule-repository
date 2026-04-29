# Correction-to-Rule Flywheel

The Rule Repository learns from human behavior. Every time a human corrects agent-generated code, the system captures the correction, analyzes the pattern, and proposes rule improvements.

## How It Works

1. **Agent writes code** — evaluated against rules, gets ALLOW
2. **Human reviews** — corrects something the rules missed
3. **Correction captured** — automatically from PR merge or manually submitted
4. **Analyzer classifies** — is this a new rule, an improvement, or a scope gap?
5. **Rule proposed** — draft rule created with evidence from source corrections
6. **Maintainer approves** — rule becomes active
7. **Agent receives rule** — via MCP, writes compliant code from now on

## Capture Methods

| Method | Trigger | Effort |
|---|---|---|
| **Auto PR capture** | PR merged with changes beyond evaluated diff | Zero (automatic) |
| **Manual submission** | User fills in original vs corrected diff on `/feedback` | Low |
| **Agent hook** | `rulerepo-hook posthoc` detects human edits after agent writes | Zero (if hooks configured) |

## Correction Analysis

Each correction is classified:

- **`new_rule`** — No existing rule covers this pattern. A new rule candidate is generated.
- **`improve_existing`** — A rule exists but its wording is ambiguous. A rewrite is suggested.
- **`adjust_scope`** — A rule exists but wasn't delivered to the agent. The scope mapping is widened.

## Effectiveness Tracking

After a rule is created from corrections, the system tracks:
- Did corrections in that pattern decrease?
- What's the false positive rate?
- Is the rule actually being evaluated (or dormant)?

## Data Reconciliation

If Elasticsearch or Neo4j fall behind PostgreSQL:

```bash
# Rebuild ES index from Postgres
uv run python scripts/reindex_elasticsearch.py

# Rebuild Neo4j graph from Postgres
uv run python scripts/reconcile_graph.py
```

PostgreSQL is always the source of truth.

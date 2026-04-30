# Correction-to-Rule Flywheel

The Rule Repository learns from human behavior. Every time a human corrects agent-generated code, the system captures the correction, analyzes the pattern, **clusters similar corrections**, and **auto-drafts rule proposals** for one-click approval.

## How It Works

1. **Agent writes code** — evaluated against rules, gets ALLOW
2. **Human reviews** — corrects something the rules missed
3. **Correction captured** — automatically from PR merge or manually submitted
4. **Analyzer classifies** — is this a new rule, an improvement, or a scope gap?
5. **Daily worker clusters** — `cluster_corrections` groups similar corrections by embedding similarity
6. **Rule auto-drafted** — Gemini drafts a rule statement from the cluster evidence
7. **Maintainer approves** — one-click approval creates a rule in **experimental** maturity (shadow mode)
8. **Rule graduates** — as the rule proves accurate, it auto-promotes to stable, then proven
9. **Agent receives rule** — via MCP, writes compliant code from now on

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

## Clustering and Auto-Drafting

The `cluster_corrections` background worker (runs daily at 5am) implements the flywheel:

1. **Fetch**: loads all pending corrections from the last 14 days
2. **Embed**: generates embeddings for each correction's delta summary using Gemini
3. **Cluster**: groups corrections by cosine similarity (threshold 0.8)
4. **Filter**: keeps clusters with 3+ corrections and average confidence > 0.8
5. **Draft**: calls Gemini to generate a structured rule (statement, modality, severity, scope, rationale)
6. **Store**: creates `DraftRuleProposalModel` entries with status "pending"

## Proposal Review

Proposals are available at:

- **`GET /api/v1/feedback/proposals`** — list pending proposals with evidence
- **`POST /api/v1/feedback/proposals/{id}/approve`** — creates a rule with `maturity_level=experimental`
- **`POST /api/v1/feedback/proposals/{id}/dismiss`** — marks as dismissed

Approved proposals create rules in **shadow mode** (experimental maturity), meaning they observe but don't block until they prove accurate.

## Effectiveness Tracking

After a rule is created from corrections, the system tracks:
- Did corrections in that pattern decrease?
- What's the false positive rate? (tracked by `false_positive_count` / `true_positive_count` on RuleModel)
- Is the rule actually being evaluated? (health scoring activity dimension)

The `auto_promote_rules` worker automatically graduates rules from experimental → stable → proven based on accuracy.

## Data Reconciliation

If Elasticsearch or Neo4j fall behind PostgreSQL:

```bash
uv run python scripts/reindex_elasticsearch.py    # Rebuild ES index
uv run python scripts/reconcile_graph.py           # Rebuild Neo4j graph
```

PostgreSQL is always the source of truth.

## See Also

- [Feedback Loop](feedback.md) -- correction submission and analysis
- [Health Scoring](health.md) -- rule health dimensions including activity
- [Background Workers](../integrations/workers.md) -- cron job details

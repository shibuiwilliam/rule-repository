# Feedback Flywheel

How corrections flow through the system and become rules.

## The Loop

```
Agent writes code
  → Evaluation (ALLOW/DENY)
  → Human reviews in PR
  → Human corrects agent's code
  → Correction captured (manual or auto from PR merge)
  → Analyzer classifies (new_rule / improve_existing / adjust_scope)
  → [PLANNED] Auto-drafter creates DRAFT rule from pattern
  → Maintainer approves → rule active
  → Agent receives rule via MCP → fewer corrections
```

## Current Implementation

### Correction Capture

Two mechanisms:

1. **Manual** (`POST /api/v1/feedback/corrections`): User submits original_diff + corrected_diff
2. **Auto PR** (`services/feedback/pr_capture.py`): When a PR is merged, compares evaluated diff vs merged diff. Delta = correction.

### Correction Analysis

`services/feedback/correction_analyzer.py` classifies each correction:

| Classification | Meaning | Action |
|---|---|---|
| `new_rule` | No matching rule exists | Propose candidate rule |
| `improve_existing` | Rule exists but is ambiguous | Suggest rewrite |
| `adjust_scope` | Rule exists but wasn't delivered | Widen scope/file matching |

### Intelligence Integration

- Top violated rules (from `intelligence/analytics.py`)
- Correction trends over time
- Coverage gaps (file paths with unmatched corrections)

## Planned: Auto-Drafter

`services/feedback/auto_drafter.py` will:
1. Query corrections with `status=analyzed`, `type=new_rule`, `confidence > 0.8`
2. Cluster by semantic similarity (scope + statement embedding)
3. For clusters with 3+ members in 14 days: create DRAFT rule
4. Link source corrections as evidence
5. Route to federation maintainer for approval

## Scripts

```bash
# Reconcile ES from Postgres (if ES missed writes)
uv run python scripts/reindex_elasticsearch.py

# Reconcile Neo4j from Postgres
uv run python scripts/reconcile_graph.py
```

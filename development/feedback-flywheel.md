# Feedback Flywheel

How corrections flow through the system and become rules.

## The Loop

```
Agent writes code
  -> Evaluation (ALLOW/DENY)
  -> Human reviews in PR
  -> Human corrects agent's code
  -> Correction captured (manual or auto from PR merge)
  -> Analyzer classifies (new_rule / improve_existing / adjust_scope)
  -> Auto-drafter clusters similar corrections and creates DRAFT rule proposals via Gemini
  -> Maintainer approves -> rule active (starts in experimental/shadow mode)
  -> Agent receives rule via MCP -> fewer corrections
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

## Auto-Drafter (Implemented)

`services/feedback/auto_drafter.py` implements `cluster_and_draft()`:

1. Fetches unprocessed corrections from the last 14 days (`CLUSTER_WINDOW_DAYS`)
2. Generates embeddings and clusters by cosine similarity (threshold `SIMILARITY_THRESHOLD=0.8`)
3. For clusters with 3+ members (`MIN_CLUSTER_SIZE`) and average confidence > 0.8 (`MIN_CONFIDENCE`): drafts a rule via Gemini
4. Creates `DraftRuleProposalModel` entries with statement, modality, severity, scope, and evidence correction IDs
5. Proposals are reviewed at `GET /api/v1/feedback/proposals` and approved/dismissed via the API
6. Approved proposals create rules with `experimental` maturity (shadow mode)

The auto-drafter runs as the `cluster_corrections` cron job daily at 5am via the arq worker.

## Scripts

```bash
# Reconcile ES from Postgres (if ES missed writes)
uv run python scripts/reindex_elasticsearch.py

# Reconcile Neo4j from Postgres
uv run python scripts/reconcile_graph.py
```

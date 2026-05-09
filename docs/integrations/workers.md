# Background Workers

The Rule Repository uses **arq** (async Redis queue) for background job processing. Workers handle scheduled maintenance tasks that run independently of API requests.

## Infrastructure

| Component | Image | Port | Purpose |
|---|---|---|---|
| **Redis** | `redis:7-alpine` | 6379 | Job queue and result backend for arq |
| **arq-worker** | Same as server | -- | Runs scheduled cron jobs and queued tasks |

Both services are included in `docker-compose.yml` and start automatically with the rest of the stack.

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379` | Redis connection URL used by arq |

## Scheduled Jobs

The arq worker runs seven scheduled cron jobs plus on-demand tasks. All are fully implemented with real database operations.

| Job | Schedule | Description |
|---|---|---|
| `compute_health_scores` | 2:00 AM daily | Recomputes rule health scores (6 dimensions). Creates alerts for unhealthy (score < 40), dormant (0 evaluations), and effectiveness decline (score < 30 with 10+ judgments) rules. |
| `generate_recommendations_task` | 3:00 AM daily | Analyzes rule usage patterns, generates improvement recommendations. Alerts on high deny rate (> 50%). |
| `verify_translation_drift` | 3:30 AM daily | Checks semantic equivalence of translated rule locales. Creates alerts for locale drift. |
| `auto_promote_rules` | 4:00 AM daily | Promotes rules through maturity levels (experimental -> stable -> proven) based on false-positive rate. Demotes if FP exceeds 10%. |
| `cluster_corrections` | 5:00 AM daily | Clusters similar corrections by embedding similarity, auto-drafts rule proposals via Gemini. Creates `DraftRuleProposalModel` entries for human review. |
| `compute_correction_stats` | Every hour | Aggregates correction statistics by analysis_type and status. |
| `send_weekly_digest` | Monday 9:00 AM | Generates weekly governance digest (compliance trends, top violations, most effective rules, declining rules, pending actions). Sends to `DIGEST_WEBHOOK_URL` if configured. |

On-demand tasks (triggered by API or events):

| Task | Description |
|---|---|
| `propagate_norm_amendment` | Propagates upstream norm changes downstream through DERIVES_FROM lineage. |

Additional worker modules (available but not in the cron schedule):

| Module | Description |
|---|---|
| `archival.py` | Rule archival and retention policy enforcement. Respects legal holds. |
| `conflict_scanner.py` | Detects conflicting rules across the corpus. |
| `norm_lineage_propagation.py` | Walks DERIVES_FROM chain to propagate norm amendments. |
| `policy_review_cycle.py` | Alerts for rules due for periodic review. |
| `polyglot_validator.py` | Multi-language code validation for polyglot codebases. |
| `verdict_drift.py` | Monitors verdict distribution changes over time. |

Jobs are idempotent and safe to run concurrently with API requests.

### auto_promote_rules

The maturity promotion worker implements progressive enforcement:

- **experimental -> stable**: rule is 30+ days old, has 20+ evaluations, and false-positive rate < 5%
- **stable -> proven**: rule is 60+ days old and false-positive rate < 1%
- **demotion**: any stable/proven rule with FP rate > 10% is demoted back to experimental

### cluster_corrections (Flywheel)

The correction-to-rule flywheel worker:

1. Fetches unprocessed corrections from the last 14 days
2. Generates embeddings for each correction's delta summary
3. Clusters by cosine similarity (threshold 0.8)
4. For clusters with 3+ corrections and average confidence > 0.8, drafts a rule via Gemini
5. Stores proposals as `DraftRuleProposalModel` entries with status "pending"
6. Proposals are reviewed at `GET /api/v1/feedback/proposals` and approved/dismissed via the API

### policy_review_cycle

The policy review cycle worker:

1. Fires daily at 6:00 AM
2. Identifies rules that are due for periodic review based on their review schedule
3. Creates alerts for rules due for review
4. Escalation: additional alerts at 30 days overdue and 60 days overdue with increasing severity

## Docker Compose Services

### redis

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
```

### arq-worker

```yaml
arq-worker:
  build:
    context: .
    dockerfile: infra/docker/server.Dockerfile
  command: ["arq", "rulerepo_server.workers.WorkerSettings"]
  depends_on:
    redis:
      condition: service_healthy
    server:
      condition: service_healthy
  environment:
    - REDIS_URL=redis://redis:6379
```

The worker shares the same Docker image as the backend server but runs the arq entrypoint instead of uvicorn.

## See Also

- [Docker Compose](../getting-started/docker-compose.md) -- full service reference
- [Health Scoring](../intelligence/health.md) -- health scores computed by the worker
- [Feedback Loop](../intelligence/feedback.md) -- feedback analysis job details
- [Correction Flywheel](../intelligence/flywheel.md) -- the self-improving rule loop

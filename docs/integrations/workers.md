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

The arq worker runs five cron jobs. All are fully implemented with real database operations.

| Job | Schedule | Description |
|---|---|---|
| `compute_health_scores` | 2:00 AM daily | Recomputes rule health scores. Creates alerts for unhealthy (score < 40) and dormant (0 evaluations) rules. |
| `generate_recommendations_task` | 3:00 AM daily | Analyzes rule usage patterns, generates improvement recommendations. Alerts on high deny rate (> 50%). |
| `auto_promote_rules` | 4:00 AM daily | Promotes rules through maturity levels (experimental → stable → proven) based on false-positive rate. Demotes if FP exceeds 10%. |
| `cluster_corrections` | 5:00 AM daily | Clusters similar corrections by embedding similarity, auto-drafts rule proposals via Gemini. Creates `DraftRuleProposalModel` entries for human review. |
| `compute_correction_stats` | Every hour | Aggregates correction statistics by analysis_type and status. |

Jobs are idempotent and safe to run concurrently with API requests.

### auto_promote_rules

The maturity promotion worker implements progressive enforcement:

- **experimental → stable**: rule is 30+ days old, has 20+ evaluations, and false-positive rate < 5%
- **stable → proven**: rule is 60+ days old and false-positive rate < 1%
- **demotion**: any stable/proven rule with FP rate > 10% is demoted back to experimental

### cluster_corrections (Flywheel)

The correction-to-rule flywheel worker:

1. Fetches unprocessed corrections from the last 14 days
2. Generates embeddings for each correction's delta summary
3. Clusters by cosine similarity (threshold 0.8)
4. For clusters with 3+ corrections and average confidence > 0.8, drafts a rule via Gemini
5. Stores proposals as `DraftRuleProposalModel` entries with status "pending"
6. Proposals are reviewed at `GET /api/v1/feedback/proposals` and approved/dismissed via the API

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

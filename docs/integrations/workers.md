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

The arq worker runs three cron jobs. These are fully implemented and produce real, persisted outputs.

| Job | Schedule | Description |
|---|---|---|
| **Health score refresh** | Periodic | Recalculates rule health scores across the corpus based on recent evaluation data. Creates proactive alerts (`dormant_rule`, `high_deny_rate`, `health_decline`) when thresholds are exceeded. Alerts are written to the alerts table and surfaced on the dashboard. |
| **Recommendation generation** | Periodic | Analyzes rule usage patterns and persists improvement recommendations to PostgreSQL. Recommendations are queryable via `GET /api/v1/intelligence/recommendations` and appear on the dashboard. |
| **Feedback analysis** | Periodic | Aggregates correction statistics, computes per-rule correction rates, and identifies patterns. Results feed into the health scoring dimensions and the recommendation engine. |

Jobs are idempotent and safe to run concurrently with API requests.

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

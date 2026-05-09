# Docker Compose Setup

The full local stack runs via `docker compose up --build` from the repository root. This page documents each service, its configuration, and useful commands.

## Services

### postgres

| Property | Value |
|---|---|
| Image | `postgres:17-alpine` |
| Port | 5432 |
| Health check | `pg_isready -U rule -d ruledb` (5s interval) |
| Volume | `pgdata` mounted at `/var/lib/postgresql/data` |

Creates the `ruledb` database with user `rule` / password `rule`. Runs `infra/postgres/init.sql` on first start to install the `uuid-ossp` and `pgcrypto` extensions. Schema is managed by Alembic migrations in the server.

### elasticsearch

| Property | Value |
|---|---|
| Image | `elasticsearch:8.17.0` |
| Port | 9200 |
| Health check | `curl -sf http://localhost:9200/_cluster/health` (10s interval) |
| Volume | `esdata` mounted at `/usr/share/elasticsearch/data` |

Runs as a single-node cluster with security disabled. Java heap is set to 512 MB.

### es-setup

| Property | Value |
|---|---|
| Image | `curlimages/curl:latest` |
| Depends on | `elasticsearch` (healthy) |
| Restart | `no` (runs once) |

Applies the `rules` index template from `infra/elasticsearch/rules-index-template.json` and creates the `rules` index. This container exits after setup completes.

### neo4j

| Property | Value |
|---|---|
| Image | `neo4j:5-community` |
| Ports | 7474 (HTTP browser), 7687 (Bolt) |
| Health check | `cypher-shell -u neo4j -p ruledev1 'RETURN 1'` (10s interval) |
| Volume | `neo4jdata` mounted at `/data` |

Credentials: `neo4j` / `ruledev1`.

### neo4j-setup

| Property | Value |
|---|---|
| Image | `neo4j:5-community` |
| Depends on | `neo4j` (healthy) |
| Restart | `no` (runs once) |

Runs `infra/neo4j/init.cypher` via `cypher-shell` to create uniqueness constraints and property indexes on the `Rule` node label.

### server

| Property | Value |
|---|---|
| Build | `infra/docker/server.Dockerfile` |
| Port | 8000 |
| Depends on | `postgres`, `elasticsearch`, `neo4j` (all healthy) |
| Health check | `curl -sf http://localhost:8000/healthz` (10s interval) |
| Volume | `file_storage` mounted at `/tmp/rulerepo-files` |

The FastAPI backend. Reads `.env` for `GEMINI_API_KEY` and other configuration. Database, Elasticsearch, and Neo4j connection strings are set in the compose file and override `.env` values to use Docker network hostnames.

### frontend

| Property | Value |
|---|---|
| Build | `infra/docker/frontend.Dockerfile` (target: `dev`) |
| Port | 3000 |
| Depends on | `server` (healthy) |
| Health check | `wget -qO- http://localhost:3000` (15s interval) |

Next.js development server. `NEXT_PUBLIC_API_BASE_URL` is set to `http://localhost:8000` so the browser talks directly to the backend.

### mcp-server

| Property | Value |
|---|---|
| Build | `infra/docker/server.Dockerfile` |
| Port | 8001 |
| Depends on | `server` (healthy) |
| Command | `rulerepo-mcp` |

MCP server for AI agent integration. Uses `streamable-http` transport. Shares the same image as the backend server but runs the MCP entrypoint.

### redis

| Property | Value |
|---|---|
| Image | `redis:7-alpine` |
| Port | 6379 |
| Health check | `redis-cli ping` (5s interval) |

Redis serves as the job queue and result backend for the arq background worker. No persistent volume by default; job state is ephemeral.

### arq-worker

| Property | Value |
|---|---|
| Build | `infra/docker/server.Dockerfile` |
| Command | `arq rulerepo_server.workers.WorkerSettings` |
| Depends on | `redis` (healthy), `server` (healthy) |

Runs 7 scheduled cron jobs (health scoring, recommendations, translation drift, rule promotion, correction clustering, correction stats, weekly digest) plus on-demand tasks. Shares the same Docker image as the backend server but uses the arq entrypoint.

## Volumes

| Volume | Purpose |
|---|---|
| `pgdata` | PostgreSQL data directory |
| `esdata` | Elasticsearch data directory |
| `neo4jdata` | Neo4j data directory |
| `file_storage` | Uploaded documents for the server |

## Commands

```bash
# Start the full stack (build images if needed)
docker compose up --build

# Start in detached mode
docker compose up -d --build

# Stop all containers (preserve data)
docker compose down

# Stop and delete all volumes (fresh start)
docker compose down -v

# Tail logs for a specific service
docker compose logs -f server

# Rebuild a single service
docker compose build server

# Restart a single service
docker compose restart frontend
```

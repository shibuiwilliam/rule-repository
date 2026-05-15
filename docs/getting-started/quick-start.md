# Quick Start

## Prerequisites

- **Docker** and **Docker Compose** (v2). No other local tooling is required to run the stack.
- A **Gemini API key** for LLM features (extraction, evaluation, intent classification). The stack starts without one, but LLM-powered features will be unavailable.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/shibuiwilliam/rule-repository.git
cd rule-repository
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set `GEMINI_API_KEY` to your key. All other defaults work for local development.

### 3. Start the stack

```bash
make up                       # or: docker compose up --build -d
```

Docker Compose builds the backend and frontend images, starts PostgreSQL, Elasticsearch, Neo4j, and Redis, runs initialization scripts, and brings up the application services. First build takes a few minutes; subsequent starts are faster.

### 4. Load sample data

The repository includes 35+ sample rule documents and 15 YAML template packs with 200+ rules across 7+ domains. Load them with:

```bash
make seed
```

Or drag and drop files from `sample_rules/` onto the Documents page at [http://localhost:3000/documents](http://localhost:3000/documents).

## Services

Once all containers are healthy, the following services are available:

| Service | URL | Purpose |
|---|---|---|
| Backend API | [http://localhost:8000](http://localhost:8000) | 40 API routers (rules, evaluation, search, submissions, governance, compliance, etc.) |
| API docs (Swagger) | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive OpenAPI documentation |
| Frontend | [http://localhost:3000](http://localhost:3000) | Operator console (browse, search, upload, evaluate, govern) |
| PostgreSQL | localhost:5432 | Relational store (`ruledb`, user `rule`) with Row-Level Security |
| Elasticsearch | [http://localhost:9200](http://localhost:9200) | Full-text and vector search index |
| Neo4j Browser | [http://localhost:7474](http://localhost:7474) | Rule relationship graph (user `neo4j`, password `ruledev1`) |
| MCP Server | [http://localhost:8001](http://localhost:8001) | Model Context Protocol server for AI agents (24 tools) |
| Redis | localhost:6379 | Job queue for background workers |
| arq-worker | -- | Background worker running 9 cron jobs (health, recommendations, translation drift, promotion, verdict drift, corrections, stats, polyglot validation, digest) |

## Try It Out

**Open the frontend** at [http://localhost:3000](http://localhost:3000) to browse rules, search, and upload documents. Use the persona switcher to see the UI adapt for different roles (Compliance, Legal, HR, Finance, Engineering).

**Search via the API**:

```bash
curl -X POST http://localhost:8000/api/v1/search/fulltext \
  -H "Content-Type: application/json" \
  -d '{"query": "overtime limit"}'
```

**Upload a document** for rule extraction:

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@path/to/policy.pdf"
```

**Evaluate a code change**:

```bash
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"diff": "...", "intent": "Add new API endpoint"}'
```

**Evaluate with a specific subject kind** (e.g., HR event):

```bash
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"subject_kind": "event", "facts": {"employee_id": "E001", "overtime_hours": 50}}'
```

## Tear Down

```bash
docker compose down       # stop containers, keep data
docker compose down -v    # stop containers and delete all volumes
```

## Next Steps

- Browse the [Architecture Overview](../architecture/overview.md) for a deep dive into how the system works.
- Check out the [SDKs and CLI](../sdks/cli.md) for integrating rule evaluation into your workflows.
- See [MCP Integration](../integrations/mcp.md) for connecting AI agents.
- Explore [Rule Templates](../api/templates.md) for pre-built rule sets across 7+ domains.

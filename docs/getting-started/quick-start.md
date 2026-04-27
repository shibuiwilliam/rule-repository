# Quick Start

## Prerequisites

- **Docker** and **Docker Compose** (v2). No other local tooling is required to run the stack.
- A **Gemini API key** for LLM features (extraction, evaluation, intent classification). The stack starts without one, but LLM-powered features will be unavailable.

## Setup

### 1. Clone the repository

```bash
git clone <repo-url> rule-repository
cd rule-repository
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set `GEMINI_API_KEY` to your key. All other defaults work for local development.

### 3. Start the stack

```bash
docker compose up --build
```

Docker Compose builds the backend and frontend images, starts PostgreSQL, Elasticsearch, and Neo4j, runs initialization scripts, and brings up the application services. First build takes a few minutes; subsequent starts are faster.

## Services

Once all containers are healthy, the following services are available:

| Service | URL | Purpose |
|---|---|---|
| Backend API | [http://localhost:8000](http://localhost:8000) | REST, Evaluate, Intent, Gateway APIs |
| API docs (Swagger) | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive OpenAPI documentation |
| Frontend | [http://localhost:3000](http://localhost:3000) | Operator console (browse, search, upload, evaluate) |
| PostgreSQL | localhost:5432 | Relational store (`ruledb`, user `rule`) |
| Elasticsearch | [http://localhost:9200](http://localhost:9200) | Full-text and vector search index |
| Neo4j Browser | [http://localhost:7474](http://localhost:7474) | Rule relationship graph (user `neo4j`, password `ruledev`) |
| MCP Server | [http://localhost:8001](http://localhost:8001) | Model Context Protocol server for AI agents |
| Redis | localhost:6379 | Job queue for background workers |
| arq-worker | -- | Background worker running cron jobs (health refresh, recommendations, feedback analysis) |

## Try It Out

**Open the frontend** at [http://localhost:3000](http://localhost:3000) to browse rules, search, and upload documents.

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

## Tear Down

```bash
docker compose down       # stop containers, keep data
docker compose down -v    # stop containers and delete all volumes
```

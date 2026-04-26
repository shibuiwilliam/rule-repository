# Architecture

## System Overview

The Rule Repository is a monorepo with five deployable components:

| Component | Tech | Port | Purpose |
|---|---|---|---|
| Backend API | Python 3.13 + FastAPI | 8000 | REST, Evaluate, Intent, Gateway, Intelligence APIs |
| MCP Server | Python 3.13 + FastMCP | 8001 | AI agent tool integration (MCP protocol) |
| Frontend | TypeScript + Next.js 15 | 3000 | Operator console |
| PostgreSQL | 17-alpine | 5432 | System of record (rules, revisions, audit log) |
| Elasticsearch | 8.17 | 9200 | Full-text + vector search |
| Neo4j | 5-community | 7474/7687 | Rule relationship graph |

## Data Flow

### Rule Creation
```
User/API → RuleService → [Postgres INSERT] + [ES index] + [Neo4j node] + [Audit log]
```

### Code Evaluation
```
Diff/Files → ContextAssembler → RuleSelector(PG+ES) → EvaluationCore(Gemini) → VerdictAggregator → AuditLog
```

### Agent Context Delivery
```
Agent calls get_rules_for_context → ScopeRegistry(in-memory) → RuleFormatter → formatted text
```

### Webhook Enforcement
```
GitHub/Slack → Gateway normalizer → PolicyEngine match → EvaluationService → Actions (webhook/comment)
```

## Layering Rule

```
api/ → services/ → domain/ + adapters/
```

- `domain/` depends on **nothing else** in the project
- `services/` depends on `domain/` and `adapters/`
- `api/` depends on `services/`
- `mcp/`, `gateway/`, `integrations/` are parallel to `api/` — they call services

## Data Stores

| Store | Role | Source of Truth? |
|---|---|---|
| PostgreSQL | Rules, revisions, audit log, documents, extractions, policies | **Yes** |
| Elasticsearch | Search index (BM25 + dense_vector) | No — derived from PG |
| Neo4j | Relationship graph (REFINES, OVERRIDES, etc.) | No — derived from PG |

If Neo4j and Postgres disagree, **Postgres wins**. Use `scripts/reconcile_graph.py` to rebuild.

## LLM Strategy

| Use Case | Model | Thinking Level |
|---|---|---|
| Search ranking, classification, extraction | `gemini-3-flash-preview` | `low` |
| Rule evaluation (LOW/MEDIUM severity) | `gemini-3-flash-preview` | `low`-`medium` |
| Rule evaluation (CRITICAL severity) | `gemini-3.1-pro-preview` | `high` |
| Rule extraction QC, conflict detection | `gemini-3.1-pro-preview` | `high` |

Temperature is always 1.0 (default). Never change it — degrades Gemini 3 reasoning.

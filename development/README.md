# Development Documentation

Technical documentation for developing and extending the Rule Repository.

---

## Documents

| Document | Description |
|---|---|
| [architecture.md](architecture.md) | System architecture: 10 deployable services, server module map (15 routers, 11 service areas), layering rules, data flows, 17 migrations, 25 ORM models |
| [evaluation-engine.md](evaluation-engine.md) | How the Code-Aware Evaluation Engine works: batched evaluation, diff parsing, context assembly, rule selection (with project + environment scoping), verdict aggregation, shadow mode, structured remediations |
| [api-reference.md](api-reference.md) | All API endpoints (14 routers): rules, search, evaluation, extraction, intent, intelligence (including /summary), relationships, discovery, feedback, federation, playground (including suggest-input), alerts, snapshots, projects |
| [mcp-server.md](mcp-server.md) | MCP tools (6 tools), resources, prompts, and transport configuration (stdio + HTTP) |
| [integrations.md](integrations.md) | GitHub App, CI CLI, agent hooks, rule ingestion, background workers (arq + Redis, 5 cron jobs), and webhook gateway |
| [testing.md](testing.md) | Test strategy (20 test files), running tests, writing new tests, LLM mocking, and linting |
| [feedback-flywheel.md](feedback-flywheel.md) | Correction capture → analysis → auto-drafting → rule improvement loop (flywheel implemented with clustering + proposals) |
| [rule-registration-workflows.md](rule-registration-workflows.md) | Sequence diagrams for all 4 rule registration paths: manual, extraction, discovery, feedback. Data store sync matrix |
| [database-schema.md](database-schema.md) | Database schema: 25 ORM models across 17 migrations, ER diagram, design decisions |
| [intelligence-dashboard-plan.md](intelligence-dashboard-plan.md) | Intelligence Dashboard implementation plan (completed) |
| [playground-enhancement-plan.md](playground-enhancement-plan.md) | Playground multi-mode input support (completed) — Code + Scenario evaluation, rule picker, suggest-by-LLM |
| [project-entity-plan.md](project-entity-plan.md) | Project entity as top-level organizational boundary (completed) |
| [phase5-improvements.md](phase5-improvements.md) | Phase 5 self-improving governance: batched evaluation, evaluation persistence, dashboard summary, outcome-oriented home page, maturity model, remediation, flywheel |
| [agent-integration-and-analytics.md](agent-integration-and-analytics.md) | Seamless agent integration (scope resolution, session context API), rule impact analytics (effectiveness score, weekly digest, team comparison), rule templates library, bulk import API |

---

## Related Top-Level Docs

- **[PROJECT.md](../PROJECT.md)** -- Project vision, domain model, roadmap, and specification. Read this first for context on what the system does and why.
- **[CLAUDE.md](../CLAUDE.md)** -- Operational contract for Claude Code: coding conventions, tech stack rules, Gemini API constraints, and non-negotiable development rules.

---

## Quick Reference: Common Make Commands

### Setup and Infrastructure

```bash
make setup             # First-time setup: create .env + install all deps
make install           # Install all dependencies (server + frontend + SDKs)
make up                # Start full stack (docker compose up --build -d)
make down              # Stop the stack
make down.clean        # Stop + wipe all volumes
make ps                # Show running services
make logs              # Tail logs for all services
make logs.server       # Tail backend logs only
```

### Pre-commit

```bash
make precommit.install # Install pre-commit hooks (ruff, mypy, trailing-whitespace, etc.)
make precommit.run     # Run all hooks on all files
make precommit.update  # Update hook versions in .pre-commit-config.yaml
```

### Development

```bash
make dev.server        # Run backend dev server (hot-reload, port 8000)
make dev.frontend      # Run frontend dev server (hot-reload, port 3000)
make mcp.stdio         # Run MCP server in stdio mode (for Claude Code)
make mcp.http          # Run MCP server in HTTP mode (port 8001)
```

### Testing

```bash
make test              # Run all tests (server + frontend)
make test.server       # Backend tests only
make test.frontend     # Frontend tests only
make test.client       # SDK tests only
make test.unit         # Backend unit tests only
make test.integration  # Backend integration tests only
make test.verbose      # Verbose output with short tracebacks
make test.cov          # Backend tests with coverage report
```

### Quality

```bash
make lint              # Lint everything (ruff + mypy + ESLint + tsc)
make format            # Format Python code (ruff format + ruff check --fix)
make format.check      # Check formatting without modifying (CI mode)
make check             # Full quality gate: format.check + lint + test
make ci                # Full CI pipeline: install + check
```

### Database

```bash
make db.migrate        # Run Alembic migrations to latest
make db.rollback       # Roll back one migration
make db.revision MSG="add foo table"   # Create a new migration
make db.history        # Show migration history
```

### Build and Data

```bash
make build.all         # Build all Docker images + SDK wheel
make seed              # Load sample rules into a running stack
make reconcile         # Rebuild Neo4j graph from PostgreSQL
make health            # Check backend liveness (/healthz)
make ready             # Check backend readiness (all stores)
```

Run `make help` to see the full list of available targets.

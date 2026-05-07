# Development Documentation

Technical documentation for developing and extending the Rule Repository.

---

## Documents

| Document | Description |
|---|---|
| [architecture.md](architecture.md) | System architecture: 10 deployable services, server module map (18 routers, 20+ service areas), layering rules, data flows, 22 migrations, 35 ORM models |
| [evaluation-engine.md](evaluation-engine.md) | How the Evaluation Engine works: batched evaluation, diff parsing, context assembly, rule selection (with project + environment scoping), verdict aggregation, shadow mode, structured remediations, domain adapters (code, business event, communication, document diff, documentation) |
| [api-reference.md](api-reference.md) | All API endpoints (18 routers): rules, search, evaluation, extraction, intent, intelligence, relationships, discovery, feedback, federation, playground, alerts, snapshots, projects, proposals, agent-governance, review, marketplace |
| [mcp-server.md](mcp-server.md) | MCP tools (12 tools), resources, prompts, and transport configuration (stdio + HTTP) |
| [integrations.md](integrations.md) | GitHub App, CI CLI, agent hooks, rule ingestion, background workers (arq + Redis, 6 cron jobs), and webhook gateway (5 sources: GitHub, Slack, Teams, Email, generic) |
| [testing.md](testing.md) | Test strategy (23+ test files, 212+ tests), running tests, writing new tests, LLM mocking, and linting |
| [feedback-flywheel.md](feedback-flywheel.md) | Correction capture -> analysis -> auto-drafting -> rule improvement loop (flywheel with clustering + proposals + auto-promotion) |
| [rule-registration-workflows.md](rule-registration-workflows.md) | Sequence diagrams for all 4 rule registration paths: manual, extraction, discovery, feedback. Data store sync matrix |
| [database-schema.md](database-schema.md) | Database schema: 35 ORM models across 22 Alembic migrations, ER diagram, design decisions |
| [intelligence-dashboard-plan.md](intelligence-dashboard-plan.md) | Intelligence Dashboard implementation plan (completed) |
| [playground-enhancement-plan.md](playground-enhancement-plan.md) | Playground multi-mode input support (completed) -- Code + Scenario evaluation, rule picker, suggest-by-LLM |
| [project-entity-plan.md](project-entity-plan.md) | Project entity as top-level organizational boundary (completed) |
| [phase5-improvements.md](phase5-improvements.md) | Phase 5 self-improving governance: batched evaluation, evaluation persistence, dashboard summary, outcome-oriented home page, maturity model, remediation, flywheel |
| [agent-integration-and-analytics.md](agent-integration-and-analytics.md) | Seamless agent integration (scope resolution, session context API), rule impact analytics (effectiveness score, weekly digest, team comparison), rule templates library, bulk import API |
| [proactive-delivery-and-quality.md](proactive-delivery-and-quality.md) | CLAUDE.md context generator CLI, effectiveness visibility (rule detail, dashboard, rules list, digest), alert banner, effectiveness-based alerts |
| [phase7-status.md](phase7-status.md) | Phase 7a (branding fix) status: COMPLETE. 13 templates with 181 rules across 7 domains. Next: Phase 7b (Subject Abstraction) |
| [spec_implementation_audit.md](spec_implementation_audit.md) | Code-only audit of PROJECT.md/CLAUDE.md specs vs. implementation: 174/176 features (98.9%) implemented |
| [feature_interactions.md](feature_interactions.md) | Cross-feature interaction pairs: intended vs. actual behavior, gap analysis, and remediations (federation x snapshot, proposal x federation, agent governance x federation) |

---

## Related Top-Level Docs

- **[PROJECT.md](../PROJECT.md)** -- Project vision, domain model, roadmap, and specification. Read this first for context on what the system does and why.
- **[CLAUDE.md](../CLAUDE.md)** -- Operational contract for Claude Code: coding conventions, tech stack rules, Gemini API constraints, and non-negotiable development rules.
- **[IMPROVEMENT.md](../IMPROVEMENT.md)** -- Gap analysis comparing vision vs. implementation, with Phase 7 action plan for cross-organizational generalization.

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

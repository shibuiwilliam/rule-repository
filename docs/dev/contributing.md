# Contributing

Thank you for contributing to the Rule Repository. This guide covers the essentials for getting started.

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.13+ | Backend server and Python SDKs |
| uv | Latest | Python dependency management |
| Node.js | 22+ | Frontend |
| pnpm | Latest | Node.js dependency management |
| Docker | Latest | Local development stack |

## Setup

```bash
git clone <repository-url>
cd rule-repository
cp .env.example .env          # fill in GEMINI_API_KEY
make setup                    # installs all dependencies
docker compose up --build     # starts the full local stack
```

After setup, verify the services are running:

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| PostgreSQL | localhost:5432 |
| Elasticsearch | http://localhost:9200 |
| Neo4j Browser | http://localhost:7474 |

## Coding Conventions

The full coding conventions are documented in [CLAUDE.md](https://github.com/shibuiwilliam/rule-repository/blob/main/CLAUDE.md). Here is a brief summary.

### Python (server and SDKs)

- **Formatter and linter**: `ruff` (covers formatting and linting). No black, no isort.
- **Type checker**: `mypy` with strict settings. Type hints are mandatory on all public functions.
- **Docstrings**: Google style, required on all public APIs.
- **Logging**: `structlog` with JSON output. Never use `print()`.
- **Data validation**: Pydantic v2 at all API boundaries.
- **Errors**: use the project exception hierarchy. Never raise bare `Exception`.

### TypeScript (frontend)

- **Strict mode**: `"strict": true` in tsconfig. No `any` without justification.
- **Framework**: Next.js App Router. Server Components by default.
- **Styling**: Tailwind CSS utility classes.
- **State management**: Server Components and URL state preferred. `zustand` for client state, `@tanstack/react-query` for server-state caching.
- **Linting**: ESLint + Prettier. `pnpm lint` must pass.

## Commit Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | When to Use |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `chore:` | Build, dependency, or tooling changes |
| `docs:` | Documentation only |
| `refactor:` | Code change that neither fixes a bug nor adds a feature |
| `test:` | Adding or updating tests |

## Quality Checks

Run all checks before committing:

```bash
make check
```

This runs:

- `ruff check` and `ruff format --check` (Python linting and formatting)
- `mypy src` (Python type checking)
- `pnpm lint` (TypeScript linting)
- `pnpm typecheck` (TypeScript type checking)
- `pytest` (Python tests)
- `pnpm test` (Frontend tests)

## Branch Workflow

1. Branch from `main`.
2. Make your changes.
3. Run `make check` to verify.
4. Open a pull request, even for solo work.
5. Keep `docker compose up --build` working -- if your change breaks the local stack, fix it before requesting review.

## Key Rules

- **Never commit secrets.** No API keys or passwords in code. Use `.env`.
- **Never delete rules** in the database. Use `effective_period.valid_until` to retire them.
- **Update PROJECT.md and CLAUDE.md** when introducing new dependencies, services, or architectural decisions.
- **Mock the LLM in tests.** Never call Gemini in unit tests. Gate live LLM tests behind `RULEREPO_LIVE_LLM=1`.

## See Also

- [CLAUDE.md](https://github.com/shibuiwilliam/rule-repository/blob/main/CLAUDE.md) -- full operational guide and coding conventions
- [PROJECT.md](https://github.com/shibuiwilliam/rule-repository/blob/main/PROJECT.md) -- project vision, domain model, and roadmap
- [Testing](testing.md) -- test commands and strategy

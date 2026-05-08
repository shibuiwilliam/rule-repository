# Testing

The project has **500+ tests** across backend, frontend, and SDK packages.

## Commands

| Command | What It Runs |
|---|---|
| `make test` | All tests (server + frontend) |
| `make test.server` | Backend tests only (`apps/server`) |
| `make test.frontend` | Frontend tests only (`apps/frontend`) |
| `make test.client` | SDK tests only (`packages/rule-client`) |
| `make test.unit` | Unit tests only (no external services required) |
| `make test.integration` | Integration tests (requires Docker Compose services) |
| `make test.e2e` | End-to-end tests (starts stack, uses real Gemini) |
| `make test.verbose` | Backend tests with verbose output |
| `make test.cov` | Backend tests with coverage report |

### Running tests directly

**Backend:**

```bash
cd apps/server
uv run pytest                       # all server tests
uv run pytest tests/unit            # unit tests only
uv run pytest tests/integration     # integration tests only
uv run pytest -k "test_evaluate"    # filter by name
```

**Frontend:**

```bash
cd apps/frontend
pnpm test                           # all frontend tests
pnpm test -- --watch                # watch mode
```

**Python SDKs:**

```bash
cd packages/rule-client
uv run pytest

cd packages/agentic-client
uv run pytest
```

## Test Categories

### Unit Tests

Pure logic tests with no external dependencies. These test domain models, utility functions, and business logic in isolation.

- Located in `tests/unit/` within each package
- No database, no Elasticsearch, no Neo4j, no network calls
- Fast: should complete in seconds
- Covers: domain models, evaluation pipeline stages, diff parsing, context assembly, verdict aggregation, conflict aggregation, PII sanitization, health scoring, gateway normalization, discovery analyzers, playground, context delivery formatting

### Integration Tests

Tests that run against the Docker Compose services (PostgreSQL, Elasticsearch, Neo4j).

- Located in `tests/integration/` within each package
- Require `docker compose up` to be running
- Test actual database queries, search indexing, and graph operations
- Covers: rules CRUD API, search API, intent API, relationships API, proposals lifecycle, agent governance

### Subject-Specific Tests

Each `SubjectKind` has dedicated tests validating the adapter, prompt rendering, and aggregation logic.

- Located in `tests/evaluation/subjects/test_<kind>_subject.py`
- Test that the subject adapter correctly renders facts for LLM, extracts features, and parses remediations

### Classification Tests

Every endpoint that returns classified data has tests verifying access control in both directions:

- High-clearance users see all data (PUBLIC through RESTRICTED)
- Low-clearance users see only what their classification level permits

### Audit Tests

Every action that should be audit-logged has tests verifying:

- The audit entry is created with correct fields
- Hash chain integrity is maintained after the action

### LLM Tests

Tests involving the Gemini API are split into two categories:

**Mocked LLM tests** (run in CI):

- All tests that exercise LLM-driven features (extraction, evaluation, conflict detection) use a mock LLM client by default
- The mock returns deterministic responses based on fixtures
- These tests verify that the integration code correctly handles LLM responses

**Live LLM tests** (eval suite, gated):

- Gated behind the `RULEREPO_LIVE_LLM=1` environment variable
- Call the real Gemini API to verify extraction quality, conflict detection precision/recall, and evaluation accuracy
- Run nightly, not on every PR
- Require `GEMINI_API_KEY` to be set

```bash
RULEREPO_LIVE_LLM=1 GEMINI_API_KEY=... uv run pytest tests/eval/
```

### End-to-End Tests

Full-stack tests that run against a live Docker Compose stack with real Gemini API calls:

- Located in `tests/e2e/` under `apps/server`
- Gated behind `RULEREPO_LIVE_LLM=1`
- Tests: document extraction, code evaluation, and full workflow (create rule, evaluate, verify verdict)
- Run with `make test.e2e` (starts the stack automatically)

### Frontend Tests

- **Component tests**: Vitest + React Testing Library. Test individual components in isolation.
- **End-to-end tests**: Playwright (if added). Test full user flows through the frontend.

## Writing Tests

### Mocking the LLM

Always mock the LLM in unit and integration tests:

```python
from unittest.mock import AsyncMock

async def test_evaluate_rule(mock_llm_client):
    mock_llm_client.generate.return_value = MockResponse(
        verdict="ALLOW",
        reasoning="The change follows all applicable rules.",
    )
    result = await evaluation_service.evaluate(context, mock_llm_client)
    assert result.verdict == "ALLOW"
```

### Test Data

Use fixtures in `tests/fixtures/` for:

- Sample rules and rule sets
- Document content (PDF, markdown, text)
- Expected extraction results
- Expected evaluation verdicts

## See Also

- [Contributing](contributing.md) -- setup and coding conventions
- [CLAUDE.md](https://github.com/shibuiwilliam/rule-repository/blob/main/CLAUDE.md) -- full testing policy and conventions

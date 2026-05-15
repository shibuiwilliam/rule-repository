# Testing Guide

Comprehensive guide to running, writing, and maintaining tests in the Rule Repository.

> **Current test count**: 1,184+ unit tests across 117 test files. All pass with zero regressions.

---

## Running Tests

### Via Make (recommended)

```bash
make test              # Run all tests (server + frontend)
make test.server       # Run backend tests only
make test.frontend     # Run frontend tests only
make test.client       # Run SDK tests (packages/rule-client)
make test.unit         # Run backend unit tests only
make test.integration  # Run backend integration tests only
make test.verbose      # Backend tests with verbose output and short tracebacks
make test.cov          # Backend tests with coverage report (--cov=rulerepo_server)
```

### Direct Commands

```bash
# Backend (from apps/server/)
cd apps/server && uv run pytest
cd apps/server && uv run pytest tests/unit/
cd apps/server && uv run pytest tests/integration/
cd apps/server && uv run pytest -v --tb=short
cd apps/server && uv run pytest --cov=rulerepo_server --cov-report=term-missing

# Run a specific test file
cd apps/server && uv run pytest tests/unit/test_domain.py

# Run a specific test class or function
cd apps/server && uv run pytest tests/unit/test_domain.py::TestModality
cd apps/server && uv run pytest tests/unit/test_domain.py::TestModality::test_values

# Frontend
cd apps/frontend && pnpm test

# SDK
cd packages/rule-client && uv run pytest
```

---

## Test Structure

The project has **1,184+ test functions** across 117 test files in five locations (unit + integration + safety + e2e + SDK). Test count grew significantly through Phase 7 (subject polymorphism, classification RLS), the RR-001–040 improvements (domain modules, safety, operability, eval harness), Phase 8 additions (surface-based template routing, domain SDK resources, MCP domain tools), and post-Phase 8 enhancements (deterministic evaluator, domain pack loader, structured scope matching, kind dispatch).

### Unit Tests (`apps/server/tests/unit/`)

Pure logic tests with no external services. Fast (sub-second per file).

| File | Tests | What it covers |
|---|---|---|
| `test_domain.py` | 22 | `Modality`, `Severity`, `RuleStatus`, `RelationshipType` enums; `EffectivePeriod`, `SourceRef`, `Rule`, `RuleRelationship`, `RuleRevision`, `Verdict` domain models; status transition validation (`DRAFT -> REVIEW -> APPROVED -> EFFECTIVE -> RETIRED`); audit entry hash chaining and genesis hash |
| `test_schemas.py` | 11 | Pydantic validation for `RuleCreate` (minimal, full, empty/long statement rejection), `RuleUpdate` (all-optional partial updates), `SearchQuery`, `CategorySearchQuery`, `IntentRequest` |
| `test_pii.py` | 11 | PII sanitization: email, phone, SSN, credit card detection and redaction via `sanitize_text`; `sanitize_dict` for nested structures; `contains_pii` detection; no-PII passthrough |
| `test_intelligence.py` | 13 | Health scoring: `compute_completeness` (full rule vs. empty rule, partial fields), `compute_freshness` (recent vs. stale rules), `compute_health_score` (composite); `generate_recommendations` for improvement suggestions (dormant, ambiguous, full-compliance, healthy) |
| `test_gateway.py` | 9 | `GitHubNormalizer` (PR events, issue events), `SlackNormalizer` (message events), `GenericNormalizer` (basic/empty payloads); `match_policies` policy engine matching (exact, wildcard, disabled excluded, wrong source excluded) |
| `test_evaluation/test_diff_parser.py` | 15 | Diff parsing: multiple files, new/modified file detection, path extraction, language detection (Python, TypeScript, unknown), function detection (def, async def, class, no functions), hunks, empty diff |
| `test_evaluation/test_context_assembler.py` | 5 | Context assembly: diff mode, file mode, facts mode, hybrid mode, empty input |
| `test_evaluation/test_verdict_aggregator.py` | 8 | Verdict aggregation: all-allow, any-deny-means-deny, needs-confirmation-without-deny, deny-overrides-needs-confirmation, empty verdicts, fix summary includes violations, violations property, model IDs deduplication |
| `test_evaluation/test_conflict_aggregator.py` | 5 | Conflict aggregation: overridden verdict discarded, higher severity wins, stronger modality wins on tie, dependent skipped on deny, standard aggregation with no relationships |
| `test_context_delivery.py` | 9 | Rule formatter output: instructions format (groups by modality, includes rule IDs, context label, MUST_NOT prefix, empty rules), checklist format (checkboxes, severity), detailed format (rationale, scope) |
| `test_github_integration.py` | 4 | GitHub review comment formatting: all-allow message, violations shown, warnings shown, violation count in header |
| `test_discovery.py` | 16 | Rule discovery analyzers and pattern detection: `ClaudeMdAnalyzer` (MUST/SHOULD/MUST_NOT rules, heading scope, empty/non-claude files), `LinterConfigAnalyzer` (ruff.toml, .eslintrc.json, tsconfig.json, empty config), `CodePatternsAnalyzer` (test naming, docstring detection, below-threshold detection), `deduplicate_and_score` (dedup similar patterns, keep different, confidence boost from multiple sources) |
| `test_playground.py` | 6 | Playground service: sandbox evaluation returns verdict, sandbox evaluation without Gemini returns NEEDS_CONFIRMATION, sandbox evaluation without audit log; snapshot serializer: serialize/deserialize round trip, serialize empty list, deserialize empty snapshot |
| `test_abac.py` | 13 | ABAC policy engine: policy effects, conditions, engine deny-by-default, allow/deny with priority, action/resource mismatch; segregation of duties |
| `test_classification.py` | 19 | Classification enum, clearance checks, RLS context, ES document-level security filter, PII redaction (simple, nested, deeply nested, missing fields) |
| `test_departments.py` | 12 | Department/Capacity domain types, DepartmentService resolvers (owner, approvers, audience, effective capacity) |
| `test_subjects.py` | 20 | SubjectKind enum, EvaluationSubject, CodeDiffAdapter, EventAdapter, ClauseSetAdapter, TransactionAdapter, Subject Registry |
| `test_compliance.py` | 11 | Classification ordering, PII redaction/restore, field detection, shadow store, approval policies, read access log |
| `test_fact_store.py` | 16 | Fact domain, status values, schema, resolution, provider registry, cache, FactStore resolve/health/caching |
| `test_operability.py` | 12 | Metrics collector, cost tracker (record, budget, breakdown), LLM fallback, circuit breaker status, leader election, health service |
| `test_plugins.py` | 13 | Core isolation, plugin protocols, plugin registry, engineering/HR/legal/finance/marketing plugin verification |
| `test_eval_harness.py` | 5 | Golden case structure, eval result structure, domain report F1, drift detector |
| `test_clause_aggregator.py` | 8 | Clause verdict aggregation: all allow, deny propagation, needs confirmation, risk scores, empty verdicts |
| `test_contract_parser.py` | 6 | Contract parsing: simple NDA, Japanese contracts, empty text, classified clauses, references |
| `test_contract_compare.py` | 7 | Contract comparison: identical/similar/unmatched clauses, missing standards, type matching, risk levels |
| `test_event_sequence.py` | 11 | Event window (total hours, leave days, aggregates), calendar context, sequence context, temporal mode narratives |
| `test_document_discovery.py` | 11 | Source query, document meta, change event, contract corpus analyzer, contract file selection |
| `test_conflict_scanner.py` | 11 | Scope overlap, statement similarity, contradictory pairs, potential conflicts, scanner integration |
| `test_cost_tracker.py` | 9 | Cost estimation (per-model rates, zero/large tokens, rounding), cost records, tracking |
| `test_llm_providers.py` | 8 | LLM provider protocol compliance (Anthropic, OpenAI, Local), names, generate/embed interfaces |
| `test_scope_matching.py` | 30 | `StructuredScope` dimension matching: single/multi-value, multi-dimension, wildcard, cross-axis scenarios ("US managers' expense policy"), `from_legacy()`, `to_es_fields()` |
| `test_deterministic_evaluator.py` | 33 | Deterministic constraint evaluation: `NumericConstraint` (pass/fail/missing/GE), `DateConstraint` (pass/fail/missing), `EnumConstraint` (pass/fail), constraint serialization roundtrips, dot-path resolution, `evaluate_from_dicts()`, real-world scenarios (overtime 45h cap, entertainment 5000 JPY cap) |
| `test_domain_pack_loader.py` | 84 | Domain pack loader: discovery (all 9 packs), `ENABLED_PACKS` filtering, `get_pack()`, `get_packs_for_surface()`, `get_packs_for_persona()`, prompt file listing, `PackManifest` construction/defaults, parametrized structure validation (pack.yaml, rules/, prompts/, samples/, analyzers/, `__init__.py`, required rule fields) for all 9 packs |
| `test_evaluation/test_kind_dispatch.py` | varies | Kind-based dispatch: partition normative vs. local rules, evaluate computational/procedural/definitional/principle rules locally without LLM |

### Acceptance Tests (`apps/server/tests/acceptance/`)

End-to-end scenario tests that verify cross-cutting business workflows.

| File | What it covers |
|---|---|
| `test_contract_review.py` | Contract review workflow: upload, extract clauses, evaluate against legal rules |
| `test_cross_department_rbac.py` | Cross-department RBAC enforcement: role-based access across org units |
| `test_expense_roundtrip.py` | Expense policy roundtrip: submit transaction, evaluate against finance rules, verdict |
| `test_hr_attendance.py` | HR attendance compliance: overtime caps, 36-agreement checks |
| `test_multilingual_rule.py` | Multilingual rule lifecycle: create, translate, verify equivalence |
| `test_sales_email.py` | Sales email compliance: communication subject evaluation against sales policies |

### Deterministic Evaluator Tests

Covered by `test_deterministic_evaluator.py` (listed under unit tests above). Tests numeric, date, and enum constraints, serialization roundtrips, dot-path resolution, and real-world scenarios (overtime 45h cap, entertainment 5000 JPY cap).

### Domain Pack Scaffolding Tests

Covered by `test_domain_pack_loader.py` (listed under unit tests above). Validates discovery of all 9 packs, filtering by `ENABLED_PACKS`, manifest construction, and parametrized structure validation (pack.yaml, rules/, prompts/, samples/, analyzers/, `__init__.py`, required rule fields) for every pack.

### Cross-Domain Coverage Tests

Tests spanning multiple `EvaluationSubject` kinds and domain packs to ensure the subject-dispatched evaluation engine handles all subject types correctly. Includes `test_subjects.py` (SubjectKind enum, adapters, registry) and acceptance tests that exercise different domains (legal, HR, finance, sales) through the submissions pipeline.

### Safety Tests (`apps/server/tests/safety/`)

Dedicated security tests. Run as part of the normal test suite.

| File | Tests | What it covers |
|---|---|---|
| `test_prompt_injection.py` | 31 | 20+ prompt injection patterns: role injection, system override, encoding evasion, Unicode tricks, delimiter attacks. All must be blocked. |

### Integration Tests (`apps/server/tests/integration/`)

Test API endpoints with mocked external services (Postgres, Elasticsearch, Neo4j, Gemini are all mocked via the `conftest.py` fixtures). These use an async HTTP client wired to the FastAPI test app.

| File | Tests | What it covers |
|---|---|---|
| `test_rules_api.py` | 15 | Full CRUD lifecycle: create rule, read by ID, list with pagination, update fields, status transitions; health endpoints (`/healthz`, `/api/v1/health`); validation error handling (422 responses); all modalities |
| `test_search_api.py` | 7 | All search modes: full-text, vector, hybrid, category search; search with filters (scope, modality, severity); pagination; validation (empty query) |
| `test_intent_api.py` | 3 | Intent classification via `/api/v1/intent` endpoint; intent with context; validation (empty query) |
| `test_relationships_api.py` | 2 | Relationship CRUD: create and delete rule relationships |
| `test_proposals.py` | -- | Proposal lifecycle: create, submit, vote, enact, revert, close, comments, notifications |
| `test_agent_governance.py` | -- | Agent registration, profiles, trust levels, personalized rules, mastery, exceptions, negotiations, sessions |
| `test_tier1.py` | 13 | Tier 1 (Postgres-only) end-to-end: health checks, CRUD, search fallback, evaluation, discovery, feedback (RR-001) |
| `test_tenant_isolation.py` | 6 | Multi-tenant context isolation, cross-tenant leakage prevention |

### End-to-End Tests (`apps/server/tests/e2e/`)

Full-stack tests that run against a live Docker Compose stack with real Gemini API calls. Gated behind `RULEREPO_LIVE_LLM=1`.

| File | What it covers |
|---|---|
| `test_extraction_e2e.py` | Document upload, Gemini-powered rule extraction, candidate review |
| `test_evaluation_e2e.py` | Code evaluation with real LLM judgment, verdict validation |
| `test_full_workflow.py` | End-to-end workflow: create rule, evaluate code, check verdict |

Run with:

```bash
make test.e2e                # starts stack if needed, runs all e2e tests
make test.e2e.extraction     # extraction tests only (stack must be running)
make test.e2e.evaluation     # evaluation tests only
make test.e2e.workflow       # full workflow test only
```

### Eval Harness (`apps/server/eval_harness/`)

Nightly regression suite validating LLM-driven evaluation quality across all 8 domains. Runs against golden datasets with annotated expected verdicts.

| Component | Purpose |
|---|---|
| `runner.py` | Runs all golden datasets, computes precision/recall/F1 per domain |
| `metrics.py` | Precision, recall, F1 calculation |
| `regression_gates.py` | CI blocking gates (fails build if F1 drops below threshold) |
| `datasets/` | 8 golden datasets: engineering, legal, hr, finance, it_security, sales, communications, governance |

**90/90 golden cases pass** across all 8 domains (as of 2026-05-09).

Run with:

```bash
make eval.harness              # run full harness
make eval.harness.domain D=hr  # run single domain
```

### SDK Tests (`packages/rule-client/tests/`)

| File | Tests | What it covers |
|---|---|---|
| `test_client.py` | 8 | `RuleClient` methods: health check, create/get/list/search rules; error handling (`raise_for_status` for 404 `NotFoundError`, 500 `ServerError`); HTTP mocking with `respx` |

---

## Test Configuration

### pytest

Configured in `apps/server/pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

With `asyncio_mode = "auto"`, all `async def test_*` functions are automatically treated as async tests. No need for `@pytest.mark.asyncio` decorators (though existing ones are harmless).

### Key Dependencies

- `pytest >= 8.3` -- test runner
- `pytest-asyncio >= 0.24` -- async test support
- `respx >= 0.22` -- HTTP mocking for SDK tests
- `httpx` -- async test client (`AsyncClient` with `ASGITransport`)

---

## LLM Mocking

All unit and integration tests mock Gemini by default. The `conftest.py` sets `svc._gemini_client = None` on service fixtures, and no test calls the real Gemini API.

### Real LLM Tests

To run tests that call the real Gemini API (eval harness, quality checks), gate them behind the `RULEREPO_LIVE_LLM` environment variable:

```python
import os
import pytest

skip_no_llm = pytest.mark.skipif(
    os.getenv("RULEREPO_LIVE_LLM") != "1",
    reason="Real LLM tests require RULEREPO_LIVE_LLM=1",
)

@skip_no_llm
async def test_extraction_quality():
    """Requires a real Gemini API key."""
    ...
```

Run with:

```bash
RULEREPO_LIVE_LLM=1 GEMINI_API_KEY=... cd apps/server && uv run pytest tests/eval/
```

Real LLM tests are for the eval harness (extraction quality, conflict detection precision/recall) and run nightly, not on every PR.

---

## Fixtures (`apps/server/tests/conftest.py`)

The conftest provides:

| Fixture | Scope | Description |
|---|---|---|
| `_reset_store` | function (autouse) | Clears the in-memory `_FakeStore` between tests |
| `sample_rule_data` | function | Single rule dict (production deployment rule, `MUST`/`HIGH`) |
| `sample_rule_data_list` | function | List of 3 rules with varied modality/severity/scope |
| `app` | function | FastAPI app with all dependencies overridden (mocked Postgres, ES, Neo4j, audit log) |
| `client` | function | `httpx.AsyncClient` wired to the test app via `ASGITransport` |

The `_FakeStore` is an in-memory dict-based store that backs the mocked `PostgresRuleRepository`. It supports create, get, list, update, revisions, and relationships, giving integration tests realistic CRUD behavior without a database.

---

## Writing New Tests

### Unit Tests

1. Place in `apps/server/tests/unit/`.
2. Test pure domain logic -- no external services, no network calls.
3. Import directly from `rulerepo_server.domain.*` or `rulerepo_server.core.*`.
4. No fixtures needed beyond standard pytest.

```python
"""Unit tests for new_module."""

from rulerepo_server.domain.new_module import SomeClass

class TestSomeClass:
    def test_basic_behavior(self) -> None:
        obj = SomeClass(value="test")
        assert obj.is_valid()
```

### Integration Tests

1. Place in `apps/server/tests/integration/`.
2. Use the `client` fixture for HTTP calls against the mocked app.
3. Use `sample_rule_data` for consistent test data.
4. All async -- just declare `async def test_*` (auto mode handles the rest).

```python
"""Integration tests for new API endpoint."""

from __future__ import annotations
from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_new_endpoint(client: AsyncClient, sample_rule_data: dict[str, Any]) -> None:
    resp = await client.post("/api/v1/rules", json=sample_rule_data)
    assert resp.status_code == 201
    rule_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/rules/{rule_id}/new-feature")
    assert resp.status_code == 200
```

### SDK Tests

1. Place in `packages/rule-client/tests/`.
2. Use `respx` to mock HTTP responses.
3. Test the `RuleClient` public API, not internal implementation.

```python
import respx
from httpx import Response
from rulerepo.client import RuleClient

class TestNewFeature:
    @respx.mock
    async def test_new_method(self) -> None:
        respx.get("http://test/api/v1/new").mock(
            return_value=Response(200, json={"data": "value"})
        )
        client = RuleClient(base_url="http://test")
        result = await client.new_method()
        assert result.data == "value"
```

### Naming Conventions

- File: `test_<module_or_feature>.py`
- Class: `Test<ClassName>` or `Test<Feature>`
- Function: `test_<what>_<expected_behavior>`
- Use type hints on all test functions: `def test_foo(self) -> None:`

---

## Linting and Formatting

### Via Make

```bash
make lint              # Lint everything (ruff check + mypy + pnpm lint + pnpm typecheck)
make lint.server       # Lint Python only (ruff check + mypy)
make lint.frontend     # Lint frontend only (ESLint + tsc --noEmit)
make format            # Format Python code (ruff format + ruff check --fix)
make format.check      # Check formatting without modifying files (CI mode)
```

### Direct Commands

```bash
# Python linting
cd apps/server && uv run ruff check src/ tests/
cd apps/server && uv run mypy src/

# Python formatting
cd apps/server && uv run ruff format src/ tests/
cd apps/server && uv run ruff check --fix src/ tests/

# Frontend linting
cd apps/frontend && pnpm lint
cd apps/frontend && pnpm typecheck
```

### Quality Gate

Before committing, run the full check:

```bash
make check             # format.check + lint + test
```

CI runs `make ci` which does `install + check`.

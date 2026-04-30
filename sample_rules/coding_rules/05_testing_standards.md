# Testing Standards

**YourExampleSoftware** — SNS Web Backend

**Document ID:** ENG-005
**Version:** 2.0
**Effective Date:** 2025-04-01
**Owner:** Backend Engineering Team
**Review Cycle:** Quarterly

---

## 1. Framework

- MUST use `pytest` as the test runner.
- MUST use `pytest-asyncio` for async test support.
- MUST NOT use `unittest` style (no `self.assertEqual`— use plain `assert`).

## 2. Coverage

- MUST maintain minimum 80% line coverage for all new code.
- MUST NOT merge PRs that reduce overall test coverage by more than 2%.
- SHOULD target 90%+ coverage for business logic (services and domain layers).
- MUST NOT count test files themselves toward coverage metrics.

## 3. Test Categories

### Unit Tests
- MUST write unit tests for all business logic in `services/` and `domain/`.
- MUST NOT access the database, network, or filesystem in unit tests.
- MUST mock external dependencies using `unittest.mock` or `pytest-mock`.
- MUST keep individual unit tests under 50ms execution time.

### Integration Tests
- MUST write integration tests for all API endpoints.
- MUST use `httpx.AsyncClient` with FastAPI's `TestClient` for API testing.
- MUST use a real test database (Docker-based) for integration tests, not SQLite.
- SHOULD use `testcontainers-python` for spinning up disposable databases in CI.

### End-to-End Tests
- SHOULD write E2E tests for critical user flows: registration, login, posting, following.
- MAY use Playwright or a similar tool for browser-based E2E tests.

## 4. Test Quality

- MUST follow Arrange-Act-Assert pattern.
- MUST use descriptive test names: `test_create_post_with_empty_content_returns_422`.
- MUST NOT write tests that depend on execution order.
- MUST NOT write tests that depend on the system clock — use `freezegun` or inject time.
- MUST NOT write tests that call external APIs — always mock external services.
- MUST NOT share mutable state between tests — each test starts with a clean state.

## 5. Test Data

- MUST use factory functions or `factory_boy` for creating test data.
- MUST NOT use hard-coded magic values — use descriptive constants or factories.
- MUST NOT use production data in tests.
- SHOULD use `faker` for generating realistic but random test data.

## 6. Fixtures

- MUST use `pytest` fixtures for shared setup and teardown.
- MUST scope database fixtures to `function` level (not `session`) to ensure isolation.
- MUST NOT use `autouse=True` fixtures unless they apply to every test in the module.
- SHOULD define commonly used fixtures in `conftest.py` at the package level.

## 7. CI Integration

- MUST run all tests on every pull request.
- MUST fail the build on any test failure.
- MUST run tests in parallel where possible (`pytest-xdist`).
- MUST generate a coverage report and upload it to the PR as a comment.
- SHOULD run mutation testing (`mutmut`) weekly to measure test effectiveness.

## 8. SNS-Specific Test Scenarios

- MUST test timeline generation with 0, 1, and 1000+ posts.
- MUST test follower/following operations including self-follow prevention.
- MUST test rate limiting behavior (429 responses).
- MUST test content moderation rules (blocked words, spam detection).
- MUST test notification delivery for mentions, likes, and follows.
- MUST test media upload with valid and invalid file types.

---

*Last reviewed: 2025-04-01 | Next review: 2025-07-01*

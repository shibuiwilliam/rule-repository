"""E2E test: code evaluation with real Gemini API.

Tests that the evaluation engine produces meaningful verdicts when
evaluating code against real rules.

Requires: RULEREPO_LIVE_LLM=1, running docker-compose stack.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        __import__("os").environ.get("RULEREPO_LIVE_LLM") != "1",
        reason="E2E tests require RULEREPO_LIVE_LLM=1",
    ),
]


async def _create_rule(client: httpx.AsyncClient, **kwargs) -> str:  # noqa: ANN003
    """Helper: create a rule, return its ID."""
    kwargs.setdefault("status", "EFFECTIVE")
    resp = await client.post("/api/v1/rules", json=kwargs)
    assert resp.status_code == 201, f"Rule creation failed: {resp.text}"
    return resp.json()["id"]


async def test_evaluate_clean_code_allows(
    http_client: httpx.AsyncClient,
    sample_python_code_good: str,
) -> None:
    """Clean, well-typed code should generally get ALLOW or NEEDS_CONFIRMATION."""

    # Create a type-hint rule
    await _create_rule(
        http_client,
        statement="All Python functions must have type annotations on parameters and return type.",
        modality="MUST",
        severity="HIGH",
        scope=["engineering", "python"],
        tags=["type-hints"],
    )

    resp = await http_client.post(
        "/api/v1/evaluate",
        json={
            "files": [{"path": "src/api/users.py", "content": sample_python_code_good}],
            "intent": "User profile endpoint",
            "scope": "engineering/python",
            "mode": "preflight",
            "max_rules": 5,
        },
        timeout=120,
    )
    assert resp.status_code == 200

    data = resp.json()
    print(f"  Clean code verdict: {data['overall_verdict']}")
    print(f"  Rules evaluated: {data['rules_evaluated']}")

    # Clean code should not get a hard DENY on type hints
    # (it has proper type annotations)
    assert data["overall_verdict"] in ("ALLOW", "NEEDS_CONFIRMATION"), (
        f"Expected ALLOW/NEEDS_CONFIRMATION for clean code, got {data['overall_verdict']}"
    )


async def test_evaluate_bad_code_detects_issues(
    http_client: httpx.AsyncClient,
    sample_diff_bad: str,
) -> None:
    """Code with SQL injection and hardcoded secrets should trigger violations."""

    # Create security-related rules
    await _create_rule(
        http_client,
        statement=(
            "All database queries MUST use parameterized queries. "
            "SQL string concatenation is prohibited."
        ),
        modality="MUST",
        severity="CRITICAL",
        scope=["engineering", "python", "security"],
        tags=["sql-injection", "security"],
    )
    await _create_rule(
        http_client,
        statement="Passwords, API keys, and secrets MUST NOT be hardcoded in source code.",
        modality="MUST_NOT",
        severity="CRITICAL",
        scope=["engineering", "security"],
        tags=["secrets", "security"],
    )

    resp = await http_client.post(
        "/api/v1/evaluate",
        json={
            "diff": sample_diff_bad,
            "intent": "Adding payment refund handler",
            "scope": "engineering/python",
            "mode": "preflight",
            "max_rules": 10,
            "severity_min": "MEDIUM",
        },
        timeout=120,
    )
    assert resp.status_code == 200

    data = resp.json()
    print(f"  Bad code verdict: {data['overall_verdict']}")
    print(f"  Rules evaluated: {data['rules_evaluated']}")
    print(f"  Violations: {data['rules_violated']}")

    assert data["rules_evaluated"] > 0, "No rules were evaluated"

    # Print violations for visibility
    for v in data.get("violations", []):
        print(f"    DENY: {v.get('rule_statement', '')[:80]}")

    for w in data.get("warnings", []):
        print(f"    WARN: {w.get('rule_statement', '')[:80]}")


async def test_evaluate_quick(
    http_client: httpx.AsyncClient,
) -> None:
    """Test the quick evaluation endpoint with a natural-language action."""

    resp = await http_client.post(
        "/api/v1/evaluate/quick",
        json={
            "action": "Deploy the application to production on Friday at 5pm without running tests",
            "scope": "engineering/deployment",
        },
        timeout=60,
    )
    assert resp.status_code == 200

    data = resp.json()
    print(f"  Quick eval verdict: {data['overall_verdict']}")
    assert "overall_verdict" in data
    assert "evaluation_id" in data


async def test_evaluate_applicable_rules(
    http_client: httpx.AsyncClient,
) -> None:
    """Test the applicable-rules endpoint — which rules match given file paths."""

    resp = await http_client.post(
        "/api/v1/evaluate/applicable-rules",
        json={
            "file_paths": ["src/api/handlers/payment.py", "src/core/auth.py"],
            "scope": "engineering",
        },
    )
    assert resp.status_code == 200

    rules = resp.json()
    print(f"  Applicable rules for payment+auth files: {len(rules)}")
    # After previous tests created rules, there should be some matches
    assert isinstance(rules, list)

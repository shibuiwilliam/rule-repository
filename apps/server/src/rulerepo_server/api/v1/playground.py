"""REST API routes for the Rule Playground & Testing Framework.

Provides sandbox evaluation, test-case CRUD, test running, and
LLM-powered test-case generation.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.gemini.client import get_gemini_client
from rulerepo_server.adapters.postgres.models import RuleModel
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.playground import (
    PlaygroundEvalRequest,
    PlaygroundEvalResponse,
    TestCaseCreate,
    TestCaseResponse,
    TestGenerateRequest,
    TestRunResult,
)
from rulerepo_server.services.playground.service import PlaygroundService
from rulerepo_server.services.playground.test_generator import generate_test_cases
from rulerepo_server.services.playground.test_runner import run_test_suite

logger = get_logger(__name__)

router = APIRouter(prefix="/playground", tags=["playground"])


def _get_optional_gemini() -> Any | None:
    """Attempt to get Gemini client, returning None if unavailable."""
    try:
        return get_gemini_client()
    except Exception:
        logger.warning("gemini_unavailable_for_playground")
        return None


# ---- Sandbox evaluation ----


@router.post("/evaluate", response_model=PlaygroundEvalResponse)
async def playground_evaluate(
    body: PlaygroundEvalRequest,
    session: AsyncSession = Depends(get_db_session),
) -> PlaygroundEvalResponse:
    """Evaluate a rule statement in sandbox mode without persistence.

    Args:
        body: The evaluation request with rule details and sample input.
        session: Injected database session.

    Returns:
        Evaluation result with verdict, confidence, reasoning, etc.
    """
    gemini = _get_optional_gemini()
    svc = PlaygroundService(session, gemini)
    result = await svc.evaluate_sandbox(
        rule_statement=body.rule_statement,
        rule_modality=body.rule_modality,
        rule_severity=body.rule_severity,
        sample_code=body.sample_code,
        sample_facts=body.sample_facts,
    )
    return PlaygroundEvalResponse(**result)


# ---- Test case CRUD ----


@router.post("/rules/{rule_id}/test-cases", response_model=TestCaseResponse)
async def create_test_case(
    rule_id: str,
    body: TestCaseCreate,
    session: AsyncSession = Depends(get_db_session),
) -> TestCaseResponse:
    """Create a new test case for a rule.

    Args:
        rule_id: UUID of the rule.
        body: Test case creation payload.
        session: Injected database session.

    Returns:
        The created test case.
    """
    svc = PlaygroundService(session, None)
    result = await svc.create_test_case(
        rule_id=rule_id,
        name=body.name,
        sample_input=body.sample_input,
        input_type=body.input_type,
        expected_verdict=body.expected_verdict,
    )
    await session.commit()
    return TestCaseResponse(**result)


@router.get("/rules/{rule_id}/test-cases", response_model=list[TestCaseResponse])
async def list_test_cases(
    rule_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[TestCaseResponse]:
    """List all test cases for a rule.

    Args:
        rule_id: UUID of the rule.
        session: Injected database session.

    Returns:
        List of test cases.
    """
    svc = PlaygroundService(session, None)
    rows = await svc.list_test_cases(rule_id)
    return [TestCaseResponse(**r) for r in rows]


@router.delete("/rules/{rule_id}/test-cases/{test_case_id}")
async def delete_test_case(
    rule_id: str,
    test_case_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Delete a test case.

    Args:
        rule_id: UUID of the rule (for path consistency).
        test_case_id: UUID of the test case to delete.
        session: Injected database session.

    Returns:
        Status confirmation dict.
    """
    svc = PlaygroundService(session, None)
    await svc.delete_test_case(test_case_id)
    await session.commit()
    return {"status": "deleted"}


# ---- Test runner ----


@router.post("/rules/{rule_id}/test-cases/run", response_model=TestRunResult)
async def run_tests(
    rule_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> TestRunResult:
    """Run all test cases for a rule and return results.

    Args:
        rule_id: UUID of the rule.
        session: Injected database session.

    Returns:
        Summary with total/passing/failing counts and per-case results.
    """
    gemini = _get_optional_gemini()
    result = await run_test_suite(rule_id, session, gemini)
    await session.commit()
    return TestRunResult(**result)


# ---- Test case generation ----


@router.post("/rules/{rule_id}/test-cases/generate", response_model=list[TestCaseResponse])
async def generate_tests(
    rule_id: str,
    body: TestGenerateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> list[TestCaseResponse]:
    """Generate test cases via Gemini and persist them.

    Args:
        rule_id: UUID of the rule.
        body: Generation request with count.
        session: Injected database session.

    Returns:
        List of generated and persisted test cases.
    """
    gemini = _get_optional_gemini()
    if gemini is None:
        return []

    # Fetch rule
    rule_result = await session.execute(select(RuleModel).where(RuleModel.id == rule_id))
    rule_model = rule_result.scalar_one_or_none()
    if rule_model is None:
        return []

    rule_dict: dict[str, Any] = {
        "statement": rule_model.statement,
        "modality": rule_model.modality,
        "severity": rule_model.severity,
    }

    generated = await generate_test_cases(rule_dict, gemini, count=body.count)

    # Persist generated test cases
    svc = PlaygroundService(session, gemini)
    persisted: list[TestCaseResponse] = []
    for tc in generated:
        row = await svc.create_test_case(
            rule_id=rule_id,
            name=tc["name"],
            sample_input=tc["sample_input"],
            input_type=tc.get("input_type", "code"),
            expected_verdict=tc["expected_verdict"],
        )
        persisted.append(TestCaseResponse(**row))

    await session.commit()
    return persisted

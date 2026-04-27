"""Test runner — executes all test cases for a rule and records results.

Each test case is evaluated against the rule using the evaluation core.
Results are persisted back to the database.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import RuleModel, RuleTestCaseModel
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import EvaluationContext
from rulerepo_server.services.evaluation.evaluation_core import evaluate_rule

logger = get_logger(__name__)


async def run_test_suite(
    rule_id: str,
    session: AsyncSession,
    gemini: Any | None,
) -> dict[str, Any]:
    """Run all test cases for a rule, update results, and return a summary.

    Args:
        rule_id: UUID of the rule whose test suite to run.
        session: Async database session.
        gemini: Optional Gemini API client.

    Returns:
        Dict with total, passing, failing counts and per-case results.
    """
    # Fetch rule
    rule_result = await session.execute(select(RuleModel).where(RuleModel.id == rule_id))
    rule_model = rule_result.scalar_one_or_none()
    if rule_model is None:
        return {"total": 0, "passing": 0, "failing": 0, "results": []}

    rule_dict: dict[str, Any] = {
        "id": str(rule_model.id),
        "statement": rule_model.statement,
        "modality": rule_model.modality,
        "severity": rule_model.severity,
    }

    # Fetch test cases
    tc_result = await session.execute(
        select(RuleTestCaseModel).where(RuleTestCaseModel.rule_id == rule_id)
    )
    test_cases = list(tc_result.scalars().all())

    if not test_cases:
        return {"total": 0, "passing": 0, "failing": 0, "results": []}

    passing_count = 0
    results: list[dict[str, Any]] = []

    for tc in test_cases:
        # Build context based on input type
        if tc.input_type == "code":
            context = EvaluationContext(diff=tc.sample_input)
        else:
            context = EvaluationContext(
                facts={"input": tc.sample_input},
                narrative=tc.sample_input,
            )

        if gemini is None:
            tc.last_result = "NEEDS_CONFIRMATION"
            tc.passing = False
            tc.last_run_at = datetime.now(tz=UTC)
        else:
            verdict_obj, _model_id, _latency = await evaluate_rule(
                rule_dict, context, gemini, cache_repo=None
            )
            tc.last_result = verdict_obj.verdict.value
            tc.passing = verdict_obj.verdict.value == tc.expected_verdict
            tc.last_run_at = datetime.now(tz=UTC)

        if tc.passing:
            passing_count += 1

        results.append(
            {
                "id": str(tc.id),
                "name": tc.name,
                "sample_input": tc.sample_input,
                "input_type": tc.input_type,
                "expected_verdict": tc.expected_verdict,
                "last_result": tc.last_result,
                "passing": tc.passing,
                "last_run_at": tc.last_run_at.isoformat() if tc.last_run_at else None,
            }
        )

    await session.flush()

    total = len(test_cases)
    logger.info(
        "test_suite_run",
        rule_id=rule_id,
        total=total,
        passing=passing_count,
        failing=total - passing_count,
    )

    return {
        "total": total,
        "passing": passing_count,
        "failing": total - passing_count,
        "results": results,
    }

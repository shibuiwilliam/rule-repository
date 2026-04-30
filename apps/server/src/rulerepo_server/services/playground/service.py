"""Playground service — sandbox evaluation and test case management.

Provides sandbox rule evaluation (no caching, no persistence) and
CRUD operations for rule test cases.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import RuleTestCaseModel
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import EvaluationContext, Verdict
from rulerepo_server.services.evaluation.evaluation_core import evaluate_rule

logger = get_logger(__name__)


class PlaygroundService:
    """Sandbox evaluation and test-case management for the Rule Playground.

    Attributes:
        _session: Async database session.
        _gemini: Optional Gemini API client.
    """

    def __init__(self, session: AsyncSession, gemini: Any | None) -> None:
        """Initialise the playground service.

        Args:
            session: SQLAlchemy async session for DB operations.
            gemini: Optional google-genai Client instance.
        """
        self._session = session
        self._gemini = gemini

    async def evaluate_sandbox(
        self,
        rule_statement: str,
        rule_modality: str,
        rule_severity: str,
        sample_code: str | None = None,
        sample_facts: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate a rule in sandbox mode without caching or persistence.

        Args:
            rule_statement: The rule statement text.
            rule_modality: Rule modality (MUST, SHOULD, etc.).
            rule_severity: Rule severity (LOW, MEDIUM, HIGH, CRITICAL).
            sample_code: Optional code snippet to evaluate against.
            sample_facts: Optional facts dict for non-code evaluation.

        Returns:
            Dict with verdict, confidence, reasoning, and other fields.
        """
        rule_dict: dict[str, Any] = {
            "id": "playground",
            "statement": rule_statement,
            "modality": rule_modality,
            "severity": rule_severity,
        }

        # Build evaluation context
        if sample_code:
            context = EvaluationContext(diff=sample_code)
        elif sample_facts:
            narrative = sample_facts.pop("narrative", None)
            context = EvaluationContext(facts=sample_facts, narrative=narrative)
        else:
            context = EvaluationContext(facts={}, narrative="No input provided")

        if self._gemini is None:
            logger.warning("playground_eval_no_gemini")
            return {
                "verdict": Verdict.NEEDS_CONFIRMATION.value,
                "confidence": 0.0,
                "reasoning": "LLM unavailable — cannot evaluate in sandbox mode.",
                "issue_description": "",
                "fix_suggestion": None,
                "locations": [],
            }

        verdict_obj, _model_id, _latency = await evaluate_rule(rule_dict, context, self._gemini, cache_repo=None)

        return {
            "verdict": verdict_obj.verdict.value,
            "confidence": verdict_obj.confidence,
            "reasoning": verdict_obj.reasoning,
            "issue_description": verdict_obj.issue_description,
            "fix_suggestion": verdict_obj.fix_suggestion,
            "locations": [
                {
                    "file_path": loc.file_path,
                    "start_line": loc.start_line,
                    "end_line": loc.end_line,
                    "function_name": loc.function_name,
                    "snippet": loc.snippet,
                }
                for loc in verdict_obj.locations
            ],
        }

    async def create_test_case(
        self,
        rule_id: str,
        name: str,
        sample_input: str,
        input_type: str,
        expected_verdict: str,
    ) -> dict[str, Any]:
        """Create a new test case for a rule.

        Args:
            rule_id: UUID of the rule to attach the test case to.
            name: Human-readable name for the test case.
            sample_input: Code snippet or scenario text.
            input_type: Type of input ("code" or "facts").
            expected_verdict: Expected evaluation verdict (ALLOW/DENY).

        Returns:
            Dict representation of the created test case.
        """
        model = RuleTestCaseModel(
            id=uuid4(),
            rule_id=rule_id,
            name=name,
            sample_input=sample_input,
            input_type=input_type,
            expected_verdict=expected_verdict,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info("test_case_created", rule_id=rule_id, name=name)
        return _model_to_dict(model)

    async def list_test_cases(self, rule_id: str) -> list[dict[str, Any]]:
        """List all test cases for a given rule.

        Args:
            rule_id: UUID of the rule.

        Returns:
            List of test-case dicts.
        """
        stmt = select(RuleTestCaseModel).where(RuleTestCaseModel.rule_id == rule_id)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [_model_to_dict(r) for r in rows]

    async def delete_test_case(self, test_case_id: str) -> None:
        """Delete a test case by its ID.

        Args:
            test_case_id: UUID of the test case to delete.
        """
        stmt = select(RuleTestCaseModel).where(RuleTestCaseModel.id == test_case_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
            logger.info("test_case_deleted", test_case_id=test_case_id)


def _model_to_dict(model: RuleTestCaseModel) -> dict[str, Any]:
    """Convert a RuleTestCaseModel ORM instance to a plain dict.

    Args:
        model: The ORM model instance.

    Returns:
        Serialisable dict.
    """
    return {
        "id": str(model.id),
        "name": model.name,
        "sample_input": model.sample_input,
        "input_type": model.input_type,
        "expected_verdict": model.expected_verdict,
        "last_result": model.last_result,
        "passing": model.passing,
        "last_run_at": model.last_run_at.isoformat() if model.last_run_at else None,
    }

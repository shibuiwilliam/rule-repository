"""REST API routes for the Code-Aware Evaluation Engine.

Per CLAUDE_ENHANCE.md §1.5:
- POST /evaluate — full evaluation
- POST /evaluate/quick — simplified non-code evaluation
- GET /evaluate/{id} — retrieve past evaluation
- POST /evaluate/applicable-rules — rules that apply without evaluation
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.gemini.client import get_gemini_client
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.evaluation import (
    ApplicableRulesRequest,
    CodeLocationResponse,
    EvaluateRequest,
    EvaluateResponse,
    QuickEvaluateRequest,
    RuleVerdictResponse,
)
from rulerepo_server.services.evaluation.service import EvaluationService

logger = get_logger(__name__)

router = APIRouter(prefix="/evaluate", tags=["evaluation"])


def _get_evaluation_service(
    session: AsyncSession = Depends(get_db_session),
) -> EvaluationService:
    gemini = None
    try:
        gemini = get_gemini_client()
    except Exception:
        logger.warning("gemini_unavailable_for_evaluation")
    return EvaluationService(session, gemini)


def _verdict_to_response(v: object) -> RuleVerdictResponse:
    """Convert a domain RuleVerdict to a response schema."""
    return RuleVerdictResponse(
        rule_id=v.rule_id,  # type: ignore[attr-defined]
        rule_statement=v.rule_statement,  # type: ignore[attr-defined]
        verdict=v.verdict.value,  # type: ignore[attr-defined]
        confidence=v.confidence,  # type: ignore[attr-defined]
        reasoning=v.reasoning,  # type: ignore[attr-defined]
        issue_description=v.issue_description,  # type: ignore[attr-defined]
        fix_suggestion=v.fix_suggestion,  # type: ignore[attr-defined]
        locations=[
            CodeLocationResponse(
                file_path=loc.file_path,
                start_line=loc.start_line,
                end_line=loc.end_line,
                function_name=loc.function_name,
                snippet=loc.snippet,
            )
            for loc in (v.locations or [])  # type: ignore[attr-defined]
        ],
    )


def _result_to_response(result: object) -> EvaluateResponse:
    """Convert a domain EvaluationResult to a response schema."""
    return EvaluateResponse(
        evaluation_id=result.evaluation_id,  # type: ignore[attr-defined]
        overall_verdict=result.overall_verdict.value,  # type: ignore[attr-defined]
        rule_verdicts=[_verdict_to_response(v) for v in result.rule_verdicts],  # type: ignore[attr-defined]
        violations=[_verdict_to_response(v) for v in result.violations],  # type: ignore[attr-defined]
        warnings=[_verdict_to_response(v) for v in result.warnings],  # type: ignore[attr-defined]
        rules_evaluated=result.rules_evaluated,  # type: ignore[attr-defined]
        rules_passed=result.rules_passed,  # type: ignore[attr-defined]
        rules_violated=result.rules_violated,  # type: ignore[attr-defined]
        rules_uncertain=result.rules_uncertain,  # type: ignore[attr-defined]
        fix_summary=result.fix_summary,  # type: ignore[attr-defined]
        model_ids_used=result.model_ids_used,  # type: ignore[attr-defined]
        total_latency_ms=result.total_latency_ms,  # type: ignore[attr-defined]
        timestamp=result.timestamp,  # type: ignore[attr-defined]
    )


@router.post("", response_model=EvaluateResponse)
async def evaluate(
    request: EvaluateRequest,
    service: EvaluationService = Depends(_get_evaluation_service),
) -> EvaluateResponse:
    """Evaluate a code change or action against applicable rules.

    Accepts diffs, file lists, or free-form facts. Returns per-rule verdicts
    with code locations and fix suggestions.
    """
    files_dicts = None
    if request.files:
        files_dicts = [{"path": f.path, "content": f.content} for f in request.files]

    result = await service.evaluate(
        diff=request.diff,
        files=files_dicts,
        facts=request.facts,
        intent=request.intent,
        scope=request.scope,
        repository=request.repository,
        mode=request.mode,
        max_rules=request.max_rules,
        severity_min=request.severity_min,
    )
    return _result_to_response(result)


@router.post("/quick", response_model=EvaluateResponse)
async def evaluate_quick(
    request: QuickEvaluateRequest,
    service: EvaluationService = Depends(_get_evaluation_service),
) -> EvaluateResponse:
    """Quick evaluation of a natural-language action description."""
    result = await service.evaluate(
        facts={"action": request.action},
        intent=request.action,
        scope=request.scope,
        mode="preflight",
    )
    return _result_to_response(result)


@router.post("/applicable-rules")
async def get_applicable_rules(
    request: ApplicableRulesRequest,
    service: EvaluationService = Depends(_get_evaluation_service),
) -> list[dict]:
    """Get rules that apply to given file paths without running evaluation."""
    return await service.get_applicable_rules(
        file_paths=request.file_paths,
        repository=request.repository,
        scope=request.scope,
    )

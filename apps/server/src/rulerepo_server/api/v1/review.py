"""REST API routes for Activity Review — two-tier compliance checking."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.deps import _get_optional_gemini
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.evaluation import RuleVerdictResponse
from rulerepo_server.schemas.review import (
    ActivityReviewRequest,
    CombinedReviewResponse,
    DetailedReviewRequest,
    DetailedReviewResponse,
    RoughReviewResponse,
    RuleRelevanceItem,
)
from rulerepo_server.services.evaluation.context_assembler import assemble_context

logger = get_logger(__name__)

router = APIRouter(prefix="/evaluate/review", tags=["activity-review"])


def _build_context(body: Any) -> Any:
    """Build EvaluationContext from request body."""
    files_list = None
    if body.files:
        files_list = [{"path": f.path, "content": f.content} for f in body.files]
    return assemble_context(
        diff=body.diff,
        files=files_list,
        facts=body.facts,
        intent=body.intent,
        scope=body.scope,
        repository=body.repository,
    )


@router.post("/rough", response_model=RoughReviewResponse)
async def rough_review_endpoint(
    body: ActivityReviewRequest,
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> RoughReviewResponse:
    """Tier 1: Fast relevance scan against ALL rules.

    Classifies every active rule as RELEVANT, POTENTIALLY_RELEVANT, or NOT_RELEVANT
    using heuristic scoring + optional single LLM triage call.
    """
    from rulerepo_server.services.evaluation.activity_review import (
        rough_review as _rough_review,
    )

    context = _build_context(body)
    gemini = _get_optional_gemini() if body.use_llm_triage else None
    pid = body.project_id or project_id

    result = await _rough_review(
        session,
        context,
        scope=body.scope,
        project_id=pid,
        use_llm_triage=body.use_llm_triage,
        relevance_threshold=body.relevance_threshold,
        gemini_client=gemini,
    )

    assessments = [
        RuleRelevanceItem(
            rule_id=a.rule_id,
            rule_statement=a.rule_statement,
            modality=a.modality,
            severity=a.severity,
            relevance=a.relevance.value,
            relevance_score=a.relevance_score,
            relevance_reason=a.relevance_reason,
        )
        for a in result.assessments
    ]

    return RoughReviewResponse(
        review_id=result.review_id,
        total_rules_scanned=result.total_rules_scanned,
        relevant_count=len(result.relevant),
        potentially_relevant_count=len(result.potentially_relevant),
        not_relevant_count=result.total_rules_scanned - len(result.relevant) - len(result.potentially_relevant),
        rule_assessments=assessments,
        llm_triage_used=result.llm_triage_used,
        latency_ms=result.latency_ms,
        timestamp=result.timestamp,
    )


@router.post("/detailed", response_model=DetailedReviewResponse)
async def detailed_review_endpoint(
    body: DetailedReviewRequest,
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> DetailedReviewResponse:
    """Tier 2: Full LLM evaluation of specified rules.

    Evaluates each rule using the batched evaluator, chunked for token limits.
    Provide rule_ids from a prior rough review or your own selection.
    """
    from rulerepo_server.services.evaluation.activity_review import (
        detailed_review as _detailed_review,
    )
    from rulerepo_server.services.evaluation.rule_selector import select_all_active_rules

    context = _build_context(body)
    gemini = _get_optional_gemini()
    pid = body.project_id or project_id

    if gemini is None:
        return DetailedReviewResponse(
            review_id="none",
            overall_verdict="NEEDS_CONFIRMATION",
            rule_verdicts=[],
            violations=[],
            warnings=[],
            rules_evaluated=0,
            rules_passed=0,
            rules_violated=0,
            rules_uncertain=0,
            fix_summary=None,
            model_ids_used=[],
            total_latency_ms=0,
            chunk_count=0,
            timestamp=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )

    # Load all rules then filter by provided IDs
    all_rules = await select_all_active_rules(session, scope=body.scope, project_id=pid)
    target_ids = set(body.rule_ids)
    relevant_rules = [r for r in all_rules if r["id"] in target_ids]

    cache_repo = None
    try:
        from rulerepo_server.adapters.postgres.cache_repo import LLMCacheRepository

        cache_repo = LLMCacheRepository(session)
    except Exception:
        pass

    chunk_size = 15
    chunks_needed = max(1, (len(relevant_rules) + chunk_size - 1) // chunk_size)

    result = await _detailed_review(
        session,
        context,
        relevant_rules,
        gemini_client=gemini,
        cache_repo=cache_repo,
    )

    verdicts = [_verdict_to_response(v) for v in result.rule_verdicts]
    violations = [_verdict_to_response(v) for v in result.violations]
    warnings = [_verdict_to_response(v) for v in result.warnings]

    return DetailedReviewResponse(
        review_id=result.evaluation_id,
        overall_verdict=result.overall_verdict.value,
        rule_verdicts=verdicts,
        violations=violations,
        warnings=warnings,
        rules_evaluated=result.rules_evaluated,
        rules_passed=result.rules_passed,
        rules_violated=result.rules_violated,
        rules_uncertain=result.rules_uncertain,
        fix_summary=result.fix_summary,
        model_ids_used=result.model_ids_used,
        total_latency_ms=result.total_latency_ms,
        chunk_count=chunks_needed,
        timestamp=result.timestamp,
    )


@router.post("", response_model=CombinedReviewResponse)
async def combined_review_endpoint(
    body: ActivityReviewRequest,
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> CombinedReviewResponse:
    """Combined Tier 1 + Tier 2: Rough scan then detailed evaluation.

    Runs rough review to identify relevant rules, then evaluates them in detail.
    """
    from rulerepo_server.services.evaluation.activity_review import (
        combined_review as _combined_review,
    )

    context = _build_context(body)
    gemini = _get_optional_gemini()
    pid = body.project_id or project_id

    cache_repo = None
    try:
        from rulerepo_server.adapters.postgres.cache_repo import LLMCacheRepository

        cache_repo = LLMCacheRepository(session)
    except Exception:
        pass

    rough_result, detailed_result = await _combined_review(
        session,
        context,
        scope=body.scope,
        project_id=pid,
        use_llm_triage=body.use_llm_triage,
        relevance_threshold=body.relevance_threshold,
        gemini_client=gemini,
        cache_repo=cache_repo,
    )

    # Build rough response
    rough_assessments = [
        RuleRelevanceItem(
            rule_id=a.rule_id,
            rule_statement=a.rule_statement,
            modality=a.modality,
            severity=a.severity,
            relevance=a.relevance.value,
            relevance_score=a.relevance_score,
            relevance_reason=a.relevance_reason,
        )
        for a in rough_result.assessments
    ]

    rough_resp = RoughReviewResponse(
        review_id=rough_result.review_id,
        total_rules_scanned=rough_result.total_rules_scanned,
        relevant_count=len(rough_result.relevant),
        potentially_relevant_count=len(rough_result.potentially_relevant),
        not_relevant_count=rough_result.total_rules_scanned
        - len(rough_result.relevant)
        - len(rough_result.potentially_relevant),
        rule_assessments=rough_assessments,
        llm_triage_used=rough_result.llm_triage_used,
        latency_ms=rough_result.latency_ms,
        timestamp=rough_result.timestamp,
    )

    # Build detailed response
    verdicts = [_verdict_to_response(v) for v in detailed_result.rule_verdicts]
    violations = [_verdict_to_response(v) for v in detailed_result.violations]
    warnings = [_verdict_to_response(v) for v in detailed_result.warnings]
    chunks_needed = max(1, (len(rough_result.relevant) + 14) // 15) if rough_result.relevant else 0

    detailed_resp = DetailedReviewResponse(
        review_id=detailed_result.evaluation_id,
        overall_verdict=detailed_result.overall_verdict.value,
        rule_verdicts=verdicts,
        violations=violations,
        warnings=warnings,
        rules_evaluated=detailed_result.rules_evaluated,
        rules_passed=detailed_result.rules_passed,
        rules_violated=detailed_result.rules_violated,
        rules_uncertain=detailed_result.rules_uncertain,
        fix_summary=detailed_result.fix_summary,
        model_ids_used=detailed_result.model_ids_used,
        total_latency_ms=detailed_result.total_latency_ms,
        chunk_count=chunks_needed,
        timestamp=detailed_result.timestamp,
    )

    return CombinedReviewResponse(
        rough_review=rough_resp,
        detailed_review=detailed_resp,
    )


def _verdict_to_response(v: Any) -> RuleVerdictResponse:
    """Convert a RuleVerdict domain object to a response schema."""
    from rulerepo_server.schemas.evaluation import (
        CodeLocationResponse,
        RemediationResponse,
    )

    return RuleVerdictResponse(
        rule_id=v.rule_id,
        rule_statement=v.rule_statement,
        verdict=v.verdict.value,
        confidence=v.confidence,
        reasoning=v.reasoning,
        issue_description=v.issue_description,
        fix_suggestion=v.fix_suggestion,
        locations=[
            CodeLocationResponse(
                file_path=loc.file_path,
                start_line=loc.start_line,
                end_line=loc.end_line,
                function_name=loc.function_name,
                snippet=loc.snippet,
            )
            for loc in v.locations
        ],
        remediations=[
            RemediationResponse(
                type=r.type,
                file_path=r.file_path,
                start_line=r.start_line,
                end_line=r.end_line,
                original=r.original,
                replacement=r.replacement,
                description=r.description,
                auto_applicable=r.auto_applicable,
            )
            for r in v.remediations
        ],
    )

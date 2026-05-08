"""REST API routes for Contract Clause Evaluation.

Provides a convenience endpoint that parses contracts, evaluates clauses
against applicable rules, and returns clause-scoped verdicts.

See: CLAUDE.md §12.2, ADR 0004
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.contract_parser import ContractParser, ContractScope
from rulerepo_server.adapters.gemini.client import get_gemini_client
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import Verdict
from rulerepo_server.schemas.contract import (
    ClauseVerdictResponse,
    ContractEvaluateRequest,
    ContractEvaluateResponse,
)
from rulerepo_server.services.evaluation.clause_aggregator import (
    aggregate_clause_verdicts,
)
from rulerepo_server.services.evaluation.service import EvaluationService

logger = get_logger(__name__)

router = APIRouter(prefix="/evaluate/contract", tags=["contract-evaluation"])


def _get_evaluation_service(
    session: AsyncSession = Depends(get_db_session),
) -> EvaluationService:
    gemini = None
    try:
        gemini = get_gemini_client()
    except Exception:
        logger.warning("gemini_unavailable_for_contract_evaluation")
    return EvaluationService(session, gemini)


@router.post("", response_model=ContractEvaluateResponse)
async def evaluate_contract(
    request: ContractEvaluateRequest,
    service: EvaluationService = Depends(_get_evaluation_service),
) -> ContractEvaluateResponse:
    """Evaluate a contract against applicable rules.

    Accepts either structured clauses or raw contract text. Returns
    per-clause verdicts with remediations and a contract-level verdict.
    """
    # 1. Parse contract if raw text provided
    parser = ContractParser()
    scope = ContractScope(
        contract_type=request.contract_type,  # type: ignore[arg-type]
        governing_law=request.governing_law or None,
        counterparty_country=request.counterparty_country or None,
        party_role=request.party_role,  # type: ignore[arg-type]
        language=request.language or None,
    )

    if request.contract_text:
        parsed = parser.parse_text(
            request.contract_text,
            title=request.title,
            scope=scope,
        )
        facts = parsed.to_evaluation_payload()
    elif request.clauses:
        facts = {
            "contract_type": request.contract_type,
            "governing_law": request.governing_law,
            "counterparty_country": request.counterparty_country,
            "party_role": request.party_role,
            "language": request.language,
            "clauses": [
                {
                    "clause_id": c.clause_id,
                    "clause_type": c.clause_type,
                    "text": c.text,
                    "heading": c.heading,
                }
                for c in request.clauses
            ],
            "clause_count": len(request.clauses),
            "review_type": request.review_type,
        }
    else:
        return ContractEvaluateResponse(
            evaluation_id="",
            contract_verdict=Verdict.ALLOW.value,
            review_type=request.review_type,
        )

    facts["review_type"] = request.review_type

    # 2. Run evaluation through the standard pipeline with subject_kind=clause_set
    result = await service.evaluate(
        facts=facts,
        scope=f"legal/contracts/{request.contract_type}",
        mode=request.mode,
        max_rules=request.max_rules,
        severity_min=request.severity_min,
        subject_kind="clause_set",
    )

    # 3. Aggregate clause-level verdicts
    aggregation = aggregate_clause_verdicts(result.rule_verdicts)

    # 4. Build per-clause response
    clause_verdicts: list[ClauseVerdictResponse] = []
    for clause_id, cvs in aggregation.clause_verdict_map.items():
        # Determine the worst verdict for this clause
        worst = Verdict.ALLOW
        for cv in cvs:
            if cv.verdict == Verdict.DENY:
                worst = Verdict.DENY
                break
            if cv.verdict == Verdict.NEEDS_CONFIRMATION and worst != Verdict.DENY:
                worst = Verdict.NEEDS_CONFIRMATION

        # Collect remediations with revised text
        revised_text = ""
        for cv in cvs:
            for rem in cv.remediations:
                if hasattr(rem, "revised_text") and rem.revised_text:  # type: ignore[attr-defined]
                    revised_text = rem.revised_text  # type: ignore[attr-defined]
                    break
            if revised_text:
                break

        clause_verdicts.append(
            ClauseVerdictResponse(
                clause_id=clause_id,
                verdict=worst.value,
                confidence=min(cv.confidence for cv in cvs) if cvs else 0.0,
                reasoning="; ".join(cv.reasoning for cv in cvs if cv.reasoning),
                issue_description="; ".join(cv.issue_description for cv in cvs if cv.issue_description),
                revised_text=revised_text,
                risk_level="high"
                if clause_id in aggregation.critical_clause_ids
                else ("medium" if clause_id in aggregation.warning_clause_ids else "low"),
                rule_verdicts=[
                    {
                        "rule_id": cv.rule_id,
                        "verdict": cv.verdict.value,
                        "reasoning": cv.reasoning,
                    }
                    for cv in cvs
                ],
            )
        )

    return ContractEvaluateResponse(
        evaluation_id=result.evaluation_id,
        contract_verdict=aggregation.contract_verdict.value,
        clause_verdicts=clause_verdicts,
        critical_clause_ids=aggregation.critical_clause_ids,
        warning_clause_ids=aggregation.warning_clause_ids,
        clause_risk_scores=aggregation.clause_risk_scores,
        rules_evaluated=result.rules_evaluated,
        rules_violated=result.rules_violated,
        model_ids_used=result.model_ids_used,
        total_latency_ms=result.total_latency_ms,
        review_type=request.review_type,
    )

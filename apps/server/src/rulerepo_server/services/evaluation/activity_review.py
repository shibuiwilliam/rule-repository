"""Activity Review — two-tier compliance checking against all rules.

Tier 1 (Rough): Fast heuristic + optional single-LLM-call triage.
Tier 2 (Detailed): Full LLM-as-Judge evaluation, chunked for token limits.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.llm import get_default_config
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import (
    EvaluationContext,
    EvaluationResult,
    Relevance,
    RoughReviewResult,
    RuleRelevanceAssessment,
)
from rulerepo_server.services.evaluation.batch_evaluator import evaluate_batch
from rulerepo_server.services.evaluation.rule_selector import (
    compute_keyword_relevance,
    select_all_active_rules,
)
from rulerepo_server.services.evaluation.verdict_aggregator import aggregate_verdicts

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Thresholds for heuristic classification
HIGH_RELEVANCE = 0.5
LOW_RELEVANCE = 0.15

# Chunking for Tier 2
CHUNK_SIZE = 15

# Max rules to send to LLM triage
MAX_TRIAGE_RULES = 50

_TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule_index": {"type": "integer"},
                    "relevant": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["rule_index", "relevant"],
            },
        },
    },
    "required": ["assessments"],
}


def _build_activity_description(context: EvaluationContext) -> str:
    """Build a human-readable description of the activity from context."""
    parts: list[str] = []
    if context.intent:
        parts.append(f"Intent: {context.intent}")
    if context.diff:
        diff_preview = context.diff[:3000]
        parts.append(f"Code change (diff):\n```\n{diff_preview}\n```")
    if context.file_paths:
        parts.append(f"Files: {', '.join(context.file_paths[:20])}")
    if context.facts:
        parts.append(f"Facts: {json.dumps(context.facts, default=str)}")
    if context.narrative:
        parts.append(f"Description: {context.narrative}")
    return "\n\n".join(parts) if parts else "No activity description provided."


async def rough_review(
    session: AsyncSession,
    context: EvaluationContext,
    *,
    scope: str | None = None,
    project_id: str | None = None,
    use_llm_triage: bool = True,
    relevance_threshold: float = 0.3,
    gemini_client: genai.Client | None = None,
) -> RoughReviewResult:
    """Tier 1: Scan ALL rules and classify by relevance using heuristics + optional LLM triage.

    Args:
        session: Database session.
        context: The evaluation context.
        scope: Optional scope filter.
        project_id: Optional project filter.
        use_llm_triage: Whether to confirm with a single LLM call.
        relevance_threshold: Minimum keyword score for RELEVANT classification.
        gemini_client: Gemini client (required for LLM triage).

    Returns:
        RoughReviewResult with per-rule relevance assessments.
    """
    start = time.time()
    review_id = str(uuid4())

    # 1. Load ALL active rules
    all_rules = await select_all_active_rules(session, scope=scope, project_id=project_id)

    # 2. Build context text for keyword matching
    context_text = _build_activity_description(context)

    # 3. Score each rule by heuristic relevance
    scored: list[tuple[dict[str, Any], float]] = []
    for rule in all_rules:
        # Existing scope/tag/language relevance
        heuristic_score = _compute_relevance_for_dict(rule, context)
        # Keyword overlap with rule statement
        keyword_score = compute_keyword_relevance(rule["statement"], context_text)
        # Combined score (normalize: heuristic is 0-30ish, keyword is 0-1)
        combined = (heuristic_score / 30.0) * 0.4 + keyword_score * 0.6
        scored.append((rule, combined))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # 4. Optional LLM triage for top candidates
    llm_triage_used = False
    llm_confirmations: dict[str, tuple[bool, str]] = {}

    if use_llm_triage and gemini_client and scored:
        # Take top candidates for LLM confirmation
        candidates = [(r, s) for r, s in scored if s >= LOW_RELEVANCE][:MAX_TRIAGE_RULES]
        if candidates:
            llm_confirmations = await _llm_triage(candidates, context_text, gemini_client)
            llm_triage_used = True

    # 5. Classify rules
    assessments: list[RuleRelevanceAssessment] = []
    for rule, score in scored:
        rid = rule["id"]

        if rid in llm_confirmations:
            is_relevant, reason = llm_confirmations[rid]
            relevance = Relevance.RELEVANT if is_relevant else Relevance.NOT_RELEVANT
            if not is_relevant and score >= relevance_threshold:
                relevance = Relevance.POTENTIALLY_RELEVANT
        elif score >= relevance_threshold:
            relevance = Relevance.RELEVANT
            reason = f"Heuristic score {score:.2f} above threshold"
        elif score >= LOW_RELEVANCE:
            relevance = Relevance.POTENTIALLY_RELEVANT
            reason = f"Heuristic score {score:.2f} in mid range"
        else:
            relevance = Relevance.NOT_RELEVANT
            reason = f"Heuristic score {score:.2f} below threshold"

        assessments.append(
            RuleRelevanceAssessment(
                rule_id=rid,
                rule_statement=rule["statement"],
                modality=rule["modality"],
                severity=rule["severity"],
                relevance=relevance,
                relevance_score=round(score, 3),
                relevance_reason=reason,
            )
        )

    latency_ms = int((time.time() - start) * 1000)

    logger.info(
        "rough_review_complete",
        review_id=review_id,
        total_scanned=len(all_rules),
        relevant=sum(1 for a in assessments if a.relevance == Relevance.RELEVANT),
        potentially_relevant=sum(1 for a in assessments if a.relevance == Relevance.POTENTIALLY_RELEVANT),
        llm_triage=llm_triage_used,
        latency_ms=latency_ms,
    )

    return RoughReviewResult(
        review_id=review_id,
        total_rules_scanned=len(all_rules),
        assessments=assessments,
        llm_triage_used=llm_triage_used,
        latency_ms=latency_ms,
    )


async def detailed_review(
    session: AsyncSession,
    context: EvaluationContext,
    relevant_rules: list[dict[str, Any]],
    *,
    gemini_client: genai.Client,
    cache_repo: Any | None = None,
    chunk_size: int = CHUNK_SIZE,
) -> EvaluationResult:
    """Tier 2: Full LLM evaluation on all relevant rules, chunked for token limits.

    Args:
        session: Database session.
        context: The evaluation context.
        relevant_rules: Rules to evaluate (from Tier 1 or explicit list).
        gemini_client: Gemini client.
        cache_repo: Optional LLM cache.
        chunk_size: Rules per batch chunk.

    Returns:
        EvaluationResult with per-rule verdicts.
    """
    start = time.time()

    if not relevant_rules:
        return EvaluationResult(
            evaluation_id=str(uuid4()),
            overall_verdict=__import__("rulerepo_server.domain.evaluation", fromlist=["Verdict"]).Verdict.ALLOW,
            rule_verdicts=[],
            rules_evaluated=0,
            rules_passed=0,
            rules_violated=0,
            rules_uncertain=0,
            fix_summary=None,
            model_ids_used=[],
            total_latency_ms=0,
        )

    # Chunk rules into groups
    chunks = [relevant_rules[i : i + chunk_size] for i in range(0, len(relevant_rules), chunk_size)]

    logger.info(
        "detailed_review_start",
        total_rules=len(relevant_rules),
        chunks=len(chunks),
        chunk_size=chunk_size,
    )

    # Evaluate chunks concurrently
    chunk_tasks = [evaluate_batch(chunk, context, gemini_client, cache_repo=cache_repo) for chunk in chunks]
    chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)

    # Merge all verdicts
    all_verdicts = []
    all_model_ids: list[str] = []
    total_latency = 0

    for result in chunk_results:
        if isinstance(result, Exception):
            logger.warning("detailed_review_chunk_failed", error=str(result))
            continue
        for verdict, model_id, latency_ms in result:
            all_verdicts.append(verdict)
            all_model_ids.append(model_id)
            total_latency += latency_ms

    # Aggregate
    total_wall = int((time.time() - start) * 1000)
    eval_result = aggregate_verdicts(all_verdicts, all_model_ids, total_wall)

    logger.info(
        "detailed_review_complete",
        rules_evaluated=eval_result.rules_evaluated,
        overall_verdict=eval_result.overall_verdict.value,
        chunks=len(chunks),
        latency_ms=total_wall,
    )

    return eval_result


async def combined_review(
    session: AsyncSession,
    context: EvaluationContext,
    *,
    scope: str | None = None,
    project_id: str | None = None,
    use_llm_triage: bool = True,
    relevance_threshold: float = 0.3,
    gemini_client: genai.Client | None = None,
    cache_repo: Any | None = None,
) -> tuple[RoughReviewResult, EvaluationResult]:
    """Combined Tier 1 + Tier 2 review.

    Runs rough review first, then evaluates all RELEVANT rules in detail.

    Returns:
        Tuple of (RoughReviewResult, EvaluationResult).
    """
    # Tier 1
    rough = await rough_review(
        session,
        context,
        scope=scope,
        project_id=project_id,
        use_llm_triage=use_llm_triage,
        relevance_threshold=relevance_threshold,
        gemini_client=gemini_client,
    )

    # Collect RELEVANT rules for Tier 2
    relevant_ids = {a.rule_id for a in rough.relevant}
    all_rules = await select_all_active_rules(session, scope=scope, project_id=project_id)
    relevant_rules = [r for r in all_rules if r["id"] in relevant_ids]

    if not relevant_rules or gemini_client is None:
        from rulerepo_server.domain.evaluation import Verdict

        empty_result = EvaluationResult(
            evaluation_id=str(uuid4()),
            overall_verdict=Verdict.ALLOW,
            rule_verdicts=[],
            rules_evaluated=0,
            rules_passed=0,
            rules_violated=0,
            rules_uncertain=0,
            fix_summary=None,
            model_ids_used=[],
            total_latency_ms=0,
        )
        return rough, empty_result

    # Tier 2
    detailed = await detailed_review(
        session, context, relevant_rules, gemini_client=gemini_client, cache_repo=cache_repo
    )

    return rough, detailed


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_relevance_for_dict(rule: dict[str, Any], context: EvaluationContext) -> float:
    """Compute relevance score for a rule dict (vs the ORM model version in rule_selector)."""
    score = 0.0
    rule_scope = rule.get("scope", [])
    rule_tags = rule.get("tags", [])

    for scope_item in rule_scope:
        for fp in context.file_paths:
            if scope_item.lower() in fp.lower():
                score += 10.0
        for lang in context.languages:
            if lang.lower() in scope_item.lower():
                score += 5.0

    for tag in rule_tags:
        tag_lower = tag.lower()
        for lang in context.languages:
            if lang.lower() in tag_lower:
                score += 3.0
        for fp in context.file_paths:
            if tag_lower in fp.lower():
                score += 2.0

    severity_bonus = {"CRITICAL": 5, "HIGH": 3, "MEDIUM": 1, "LOW": 0}
    score += severity_bonus.get(rule.get("severity", "LOW"), 0)

    return score


async def _llm_triage(
    candidates: list[tuple[dict[str, Any], float]],
    activity_description: str,
    gemini_client: genai.Client,
) -> dict[str, tuple[bool, str]]:
    """Single LLM call to confirm/deny relevance of candidate rules.

    Returns:
        Dict mapping rule_id → (is_relevant, reason).
    """
    config = get_default_config()
    template = (PROMPTS_DIR / "triage_relevance.txt").read_text()

    rules_block_lines = []
    rule_ids_by_index: dict[int, str] = {}
    for i, (rule, score) in enumerate(candidates):
        rules_block_lines.append(
            f"[Rule {i}] (id={rule['id']}) [{rule['modality']}] [{rule['severity']}]\n  {rule['statement']}"
        )
        rule_ids_by_index[i] = rule["id"]

    prompt = template.format(
        activity_description=activity_description[:4000],
        rules_block="\n\n".join(rules_block_lines),
    )

    try:
        response = await gemini_client.aio.models.generate_content(
            model=config.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=_TRIAGE_SCHEMA,
                thinking_config=types.ThinkingConfig(thinking_level="low"),
            ),
        )

        data = json.loads(response.text or "{}") if response.text else {}
        assessments = data.get("assessments", [])

        result: dict[str, tuple[bool, str]] = {}
        for item in assessments:
            idx = item.get("rule_index")
            if idx is not None and idx in rule_ids_by_index:
                result[rule_ids_by_index[idx]] = (
                    item.get("relevant", True),
                    item.get("reason", ""),
                )

        logger.info("llm_triage_complete", assessed=len(result), candidates=len(candidates))
        return result

    except Exception as exc:
        logger.warning("llm_triage_failed", error=str(exc))
        return {}

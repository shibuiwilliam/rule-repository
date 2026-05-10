"""Batch evaluator — evaluates multiple rules in a single LLM call.

Sends all selected rules + context to Gemini in one request, requesting
per-rule verdicts via structured output. Falls back to per-rule evaluation
if the batch call fails.

Per CLAUDE.md: uses structured output, default temperature (1.0),
thinking_level based on max severity in the batch.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from rulerepo_server.core.llm import get_default_config
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import (
    EvaluationContext,
    RuleVerdict,
    Surface,
    Verdict,
)
from rulerepo_server.services.evaluation.evaluation_core import evaluate_rule
from rulerepo_server.services.evaluation.schemas import (
    build_batch_verdict_schema,
    parse_location,
    validate_location_fields,
)

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

MAX_PROMPT_CHARS = 30_000
MAX_DIFF_CHARS = 8_000


def _resolve_surface(surface_str: str | None) -> Surface | None:
    """Resolve a surface string to a Surface enum value."""
    if surface_str is None:
        return None
    try:
        return Surface(surface_str)
    except ValueError:
        return None


def _hash_content(*parts: str) -> str:
    """Compute a short SHA-256 hash of concatenated parts."""
    return hashlib.sha256("".join(parts).encode()).hexdigest()[:16]


def _build_rules_block(rules: list[dict[str, Any]]) -> str:
    """Format rules for inclusion in the batch prompt."""
    lines: list[str] = []
    for i, rule in enumerate(rules):
        block = (
            f"[Rule {i}] (id={rule['id']}) "
            f"[{rule.get('modality', 'MUST')}] [{rule.get('severity', 'MEDIUM')}]\n"
            f"  Statement: {rule.get('statement', '')}"
        )
        rationale = rule.get("rationale", "")
        if rationale:
            block += f"\n  Rationale: {rationale}"
        context = rule.get("context", "")
        if context:
            block += f"\n  Context: {context}"
        preconditions = rule.get("preconditions", [])
        if preconditions:
            block += f"\n  Preconditions: {', '.join(preconditions)}"
        exceptions = rule.get("exceptions", [])
        if exceptions:
            block += f"\n  Exceptions: {', '.join(exceptions)}"
        following = rule.get("following_examples", [])
        if following:
            block += f"\n  Following examples: {'; '.join(following)}"
        violations = rule.get("violation_examples", [])
        if violations:
            block += f"\n  Violation examples: {'; '.join(violations)}"
        lines.append(block)
    return "\n\n".join(lines)


def _build_relationships_block(
    rules: list[dict[str, Any]],
    plan: Any | None = None,
) -> str:
    """Build relationship context from the evaluation plan.

    Includes overrides, conflicts, and dependencies so the LLM can
    reason about rule interactions when evaluating.

    Args:
        rules: List of rule dicts being evaluated.
        plan: Optional EvaluationPlan with relationship data.

    Returns:
        Formatted string describing rule relationships, or empty if none.
    """
    if plan is None:
        return ""

    rule_ids = {r["id"] for r in rules}
    lines: list[str] = []

    # Overrides
    for overridden_id, overriding_id in getattr(plan, "overrides", {}).items():
        if overridden_id in rule_ids and overriding_id in rule_ids:
            lines.append(
                f"- Rule {overriding_id[:8]} OVERRIDES Rule {overridden_id[:8]} "
                "(apply the overriding rule's verdict when they conflict)"
            )

    # Conflicts
    for a_id, b_id in getattr(plan, "conflicts", []):
        if a_id in rule_ids and b_id in rule_ids:
            lines.append(
                f"- Rule {a_id[:8]} CONFLICTS WITH Rule {b_id[:8]} "
                "(these rules may contradict — evaluate both but note the tension)"
            )

    # Dependencies (skip_if_denied)
    for prereq_id, dependent_ids in getattr(plan, "skip_if_denied", {}).items():
        for dep_id in dependent_ids:
            if prereq_id in rule_ids and dep_id in rule_ids:
                lines.append(
                    f"- Rule {dep_id[:8]} DEPENDS ON Rule {prereq_id[:8]} "
                    "(if the prerequisite rule is violated, the dependent rule may not apply)"
                )

    if not lines:
        return ""

    return "## Rule Relationships\n\n" + "\n".join(lines)


def _select_template(context: EvaluationContext) -> str:
    """Select the prompt template based on the evaluation surface.

    Routes to a surface-specific template if one exists, otherwise
    falls back to the generic template. For backward compatibility,
    contexts without an explicit surface that have a diff use the
    code template.

    Args:
        context: The evaluation context with an optional surface field.

    Returns:
        The prompt template text.
    """
    surface = context.surface
    # Backward compatibility: no surface + has diff → code
    if surface is None:
        surface = "code" if context.diff else "generic"

    template_path = PROMPTS_DIR / f"evaluate_batch_{surface}.txt"
    if template_path.exists():
        return template_path.read_text()
    return (PROMPTS_DIR / "evaluate_batch_generic.txt").read_text()


def _parse_batch_response(
    rules: list[dict[str, Any]],
    response_verdicts: list[dict[str, Any]],
    surface: Surface | None = None,
) -> list[RuleVerdict]:
    """Parse the batch JSON response into RuleVerdict objects."""
    # Build lookup by rule_index and rule_id
    verdict_by_index: dict[int, dict] = {}
    verdict_by_id: dict[str, dict] = {}
    for v in response_verdicts:
        idx = v.get("rule_index")
        rid = v.get("rule_id", "")
        if idx is not None:
            verdict_by_index[idx] = v
        if rid:
            verdict_by_id[rid] = v

    results: list[RuleVerdict] = []
    for i, rule in enumerate(rules):
        # Try matching by index first, then by rule_id
        vdata = verdict_by_index.get(i) or verdict_by_id.get(rule["id"], {})

        verdict_str = vdata.get("verdict", "NEEDS_CONFIRMATION")
        try:
            verdict = Verdict(verdict_str)
        except ValueError:
            verdict = Verdict.NEEDS_CONFIRMATION

        locations = []
        for loc in vdata.get("locations", []):
            if isinstance(loc, dict):
                cleaned = validate_location_fields(loc, surface)
                locations.append(parse_location(cleaned, surface))

        results.append(
            RuleVerdict(
                rule_id=rule["id"],
                rule_statement=rule.get("statement", ""),
                verdict=verdict,
                confidence=float(vdata.get("confidence", 0.5)),
                reasoning=vdata.get("reasoning", ""),
                issue_description=vdata.get("issue_description", ""),
                fix_suggestion=vdata.get("fix_suggestion"),
                locations=locations,
                remediations=[],
            )
        )

    return results


async def evaluate_batch(
    rules: list[dict[str, Any]],
    context: EvaluationContext,
    gemini_client: genai.Client,
    cache_repo: Any | None = None,
    evaluation_plan: Any | None = None,
    *,
    surface: Surface | str | None = None,
) -> list[tuple[RuleVerdict, str, int]]:
    """Evaluate multiple rules in a single batched LLM call.

    Args:
        rules: List of rule dicts with id, statement, modality, severity.
        context: The evaluation context (diff, facts, etc.).
        gemini_client: Gemini API client.
        cache_repo: Optional LLM cache repository.
        evaluation_plan: Optional graph-resolved evaluation plan.
        surface: Evaluation surface for schema selection.

    Returns:
        List of (RuleVerdict, model_id, latency_ms) tuples, one per rule.
        Falls back to per-rule evaluation on failure.
    """
    if not rules:
        return []

    resolved = _resolve_surface(surface) if isinstance(surface, str) else surface

    # For single rules, use the per-rule path directly
    if len(rules) == 1:
        return [
            await evaluate_rule(
                rules[0],
                context,
                gemini_client,
                cache_repo,
                surface=resolved,
            )
        ]

    try:
        return await _batch_evaluate_impl(
            rules,
            context,
            gemini_client,
            cache_repo,
            evaluation_plan,
            surface=resolved,
        )
    except Exception as exc:
        logger.warning(
            "batch_evaluation_fallback",
            error=str(exc),
            rule_count=len(rules),
        )
        return await _fallback_per_rule(
            rules,
            context,
            gemini_client,
            cache_repo,
            surface=resolved,
        )


async def _batch_evaluate_impl(
    rules: list[dict[str, Any]],
    context: EvaluationContext,
    gemini_client: genai.Client,
    cache_repo: Any | None = None,
    evaluation_plan: Any | None = None,
    *,
    surface: Surface | None = None,
) -> list[tuple[RuleVerdict, str, int]]:
    """Core batch evaluation implementation."""
    config = get_default_config()
    start = time.time()

    # Build prompt
    rules_block = _build_rules_block(rules)
    relationships_block = _build_relationships_block(rules, evaluation_plan)

    template = _select_template(context)

    if context.surface == "code" or (context.surface is None and context.diff):
        # Code surface: use diff-specific template variables
        diff_text = context.diff[:MAX_DIFF_CHARS] if context.diff else ""
        file_paths = ", ".join(context.file_paths[:20]) if context.file_paths else "unknown"
        prompt = template.format(
            rules_block=rules_block,
            diff=diff_text,
            file_paths=file_paths,
            relationships_block=relationships_block,
        )
    else:
        # All non-code surfaces: use facts-based template variables
        facts_text = json.dumps(context.facts, default=str) if context.facts else "{}"
        prompt = template.format(
            rules_block=rules_block,
            intent=context.intent or "",
            facts=facts_text,
            narrative=context.narrative or "No narrative provided",
            relationships_block=relationships_block,
        )

    # Check prompt size — if too large, fall back
    if len(prompt) > MAX_PROMPT_CHARS:
        logger.info(
            "batch_prompt_too_large",
            prompt_len=len(prompt),
            rule_count=len(rules),
        )
        raise ValueError("Prompt exceeds batch size limit")

    # Check cache
    rule_ids_sorted = sorted(r["id"] for r in rules)
    context_hash = _hash_content(
        context.diff or "",
        json.dumps(context.facts, default=str) if context.facts else "",
        context.intent or "",
    )
    cache_key = _hash_content(",".join(rule_ids_sorted), context_hash, config.model_id)

    if cache_repo:
        try:
            cached = await cache_repo.get(cache_key)
            if cached:
                logger.info("batch_cache_hit", rule_count=len(rules))
                verdicts_data = json.loads(cached["response"])
                parsed = _parse_batch_response(rules, verdicts_data.get("verdicts", []), surface=surface)
                latency = int((time.time() - start) * 1000)
                return [(v, config.model_id, latency) for v in parsed]
        except Exception:
            pass

    # Build surface-aware batch schema
    batch_schema = build_batch_verdict_schema(surface)

    # Call Gemini
    # Use medium thinking for batches (multiple rules require more reasoning)
    response = await gemini_client.aio.models.generate_content(
        model=config.model_id,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=batch_schema,
            thinking_config=types.ThinkingConfig(thinking_level="medium"),
        ),
    )

    latency_ms = int((time.time() - start) * 1000)

    # Parse response
    response_data = json.loads(response.text or "{}") if response.text else {}
    response_verdicts = response_data.get("verdicts", [])

    if len(response_verdicts) < len(rules):
        logger.warning(
            "batch_incomplete_response",
            expected=len(rules),
            received=len(response_verdicts),
        )

    parsed_verdicts = _parse_batch_response(rules, response_verdicts, surface=surface)

    # Store in cache
    if cache_repo:
        try:
            await cache_repo.store(
                cache_key=cache_key,
                model_id=config.model_id,
                prompt_version=_hash_content(prompt[:500]),
                inputs_hash=context_hash,
                response=json.dumps(response_data),
                latency_ms=latency_ms,
            )
        except Exception:
            pass

    # Tiered confirmation: re-evaluate DENY + CRITICAL rules with Pro model
    results: list[tuple[RuleVerdict, str, int]] = []
    pro_tasks: list[tuple[int, Any]] = []

    for i, (verdict, rule) in enumerate(zip(parsed_verdicts, rules, strict=False)):
        if verdict.verdict == Verdict.DENY and rule.get("severity") == "CRITICAL":
            pro_tasks.append((i, rule))
            results.append((verdict, config.model_id, latency_ms))
        else:
            results.append((verdict, config.model_id, latency_ms))

    # Run Pro confirmation for DENY+CRITICAL rules
    if pro_tasks:
        logger.info("batch_pro_confirmation", count=len(pro_tasks))
        pro_results = await asyncio.gather(
            *[evaluate_rule(rule, context, gemini_client, cache_repo, surface=surface) for _, rule in pro_tasks],
            return_exceptions=True,
        )
        for (idx, _), pro_result in zip(pro_tasks, pro_results, strict=False):
            if isinstance(pro_result, Exception):
                continue
            pro_verdict, pro_model_id, pro_latency = pro_result
            # Pro verdict overrides the batch verdict
            results[idx] = (pro_verdict, pro_model_id, pro_latency)

    logger.info(
        "batch_evaluation_complete",
        rule_count=len(rules),
        latency_ms=latency_ms,
        pro_confirmations=len(pro_tasks),
    )

    return results


async def _fallback_per_rule(
    rules: list[dict[str, Any]],
    context: EvaluationContext,
    gemini_client: genai.Client,
    cache_repo: Any | None = None,
    *,
    surface: Surface | None = None,
) -> list[tuple[RuleVerdict, str, int]]:
    """Fallback: evaluate each rule individually (existing behavior)."""
    tasks = [evaluate_rule(rule, context, gemini_client, cache_repo=cache_repo, surface=surface) for rule in rules]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results: list[tuple[RuleVerdict, str, int]] = []
    for result_item in raw_results:
        if isinstance(result_item, Exception):
            logger.warning("fallback_rule_failed", error=str(result_item))
            continue
        results.append(result_item)

    return results

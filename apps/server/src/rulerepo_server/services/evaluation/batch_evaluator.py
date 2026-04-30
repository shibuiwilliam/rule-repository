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
    CodeLocation,
    EvaluationContext,
    RuleVerdict,
    Verdict,
)
from rulerepo_server.services.evaluation.evaluation_core import evaluate_rule

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

MAX_PROMPT_CHARS = 30_000
MAX_DIFF_CHARS = 8_000

_BATCH_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule_index": {"type": "integer"},
                    "rule_id": {"type": "string"},
                    "verdict": {
                        "type": "string",
                        "enum": ["ALLOW", "DENY", "NEEDS_CONFIRMATION"],
                    },
                    "confidence": {"type": "number"},
                    "reasoning": {"type": "string"},
                    "issue_description": {"type": "string"},
                    "fix_suggestion": {"type": "string"},
                    "locations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "start_line": {"type": "integer"},
                                "end_line": {"type": "integer"},
                                "function_name": {"type": "string"},
                                "snippet": {"type": "string"},
                            },
                        },
                    },
                },
                "required": [
                    "rule_index",
                    "rule_id",
                    "verdict",
                    "confidence",
                    "reasoning",
                ],
            },
        },
    },
    "required": ["verdicts"],
}


def _hash_content(*parts: str) -> str:
    """Compute a short SHA-256 hash of concatenated parts."""
    return hashlib.sha256("".join(parts).encode()).hexdigest()[:16]


def _build_rules_block(rules: list[dict[str, Any]]) -> str:
    """Format rules for inclusion in the batch prompt."""
    lines: list[str] = []
    for i, rule in enumerate(rules):
        lines.append(
            f"[Rule {i}] (id={rule['id']}) "
            f"[{rule.get('modality', 'MUST')}] [{rule.get('severity', 'MEDIUM')}]\n"
            f"  {rule.get('statement', '')}"
        )
    return "\n\n".join(lines)


def _build_relationships_block(rules: list[dict[str, Any]]) -> str:
    """Build relationship context if rules have known interactions."""
    # Placeholder for future Neo4j relationship injection
    return ""


def _parse_batch_response(rules: list[dict[str, Any]], response_verdicts: list[dict[str, Any]]) -> list[RuleVerdict]:
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

        locations = [
            CodeLocation(
                file_path=loc.get("file_path", ""),
                start_line=loc.get("start_line"),
                end_line=loc.get("end_line"),
                function_name=loc.get("function_name"),
                snippet=loc.get("snippet"),
            )
            for loc in vdata.get("locations", [])
            if isinstance(loc, dict)
        ]

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
) -> list[tuple[RuleVerdict, str, int]]:
    """Evaluate multiple rules in a single batched LLM call.

    Args:
        rules: List of rule dicts with id, statement, modality, severity.
        context: The evaluation context (diff, facts, etc.).
        gemini_client: Gemini API client.
        cache_repo: Optional LLM cache repository.

    Returns:
        List of (RuleVerdict, model_id, latency_ms) tuples, one per rule.
        Falls back to per-rule evaluation on failure.
    """
    if not rules:
        return []

    # For single rules, use the per-rule path directly
    if len(rules) == 1:
        return [await evaluate_rule(rules[0], context, gemini_client, cache_repo)]

    try:
        return await _batch_evaluate_impl(rules, context, gemini_client, cache_repo)
    except Exception as exc:
        logger.warning(
            "batch_evaluation_fallback",
            error=str(exc),
            rule_count=len(rules),
        )
        return await _fallback_per_rule(rules, context, gemini_client, cache_repo)


async def _batch_evaluate_impl(
    rules: list[dict[str, Any]],
    context: EvaluationContext,
    gemini_client: genai.Client,
    cache_repo: Any | None = None,
) -> list[tuple[RuleVerdict, str, int]]:
    """Core batch evaluation implementation."""
    config = get_default_config()
    start = time.time()

    # Build prompt
    rules_block = _build_rules_block(rules)
    relationships_block = _build_relationships_block(rules)

    if context.diff:
        template = (PROMPTS_DIR / "evaluate_batch.txt").read_text()
        diff_text = context.diff[:MAX_DIFF_CHARS]
        file_paths = ", ".join(context.file_paths[:20]) if context.file_paths else "unknown"
        prompt = template.format(
            rules_block=rules_block,
            diff=diff_text,
            file_paths=file_paths,
            relationships_block=relationships_block,
        )
    else:
        template = (PROMPTS_DIR / "evaluate_batch_facts.txt").read_text()
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
                parsed = _parse_batch_response(rules, verdicts_data.get("verdicts", []))
                latency = int((time.time() - start) * 1000)
                return [(v, config.model_id, latency) for v in parsed]
        except Exception:
            pass

    # Call Gemini
    # Use medium thinking for batches (multiple rules require more reasoning)
    response = await gemini_client.aio.models.generate_content(
        model=config.model_id,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=_BATCH_VERDICT_SCHEMA,
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

    parsed_verdicts = _parse_batch_response(rules, response_verdicts)

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
            *[evaluate_rule(rule, context, gemini_client, cache_repo) for _, rule in pro_tasks],
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
) -> list[tuple[RuleVerdict, str, int]]:
    """Fallback: evaluate each rule individually (existing behavior)."""
    tasks = [evaluate_rule(rule, context, gemini_client, cache_repo=cache_repo) for rule in rules]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results: list[tuple[RuleVerdict, str, int]] = []
    for result_item in raw_results:
        if isinstance(result_item, Exception):
            logger.warning("fallback_rule_failed", error=str(result_item))
            continue
        results.append(result_item)

    return results

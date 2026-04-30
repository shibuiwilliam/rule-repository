"""Evaluation Core — LLM-as-Judge for each rule against the context.

Per CLAUDE_ENHANCE.md §1.4.3: evaluates each selected rule using Gemini with
structured output. Model selection based on rule severity. All calls use
response_mime_type="application/json" + schema.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from rulerepo_server.core.llm import LLMConfig, get_default_config, get_judge_config
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import (
    CodeLocation,
    EvaluationContext,
    Remediation,
    RuleVerdict,
    Verdict,
)

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

# JSON schema for structured verdict output
_VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["ALLOW", "DENY", "NEEDS_CONFIRMATION"]},
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
        "remediations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "file_path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "original": {"type": "string"},
                    "replacement": {"type": "string"},
                    "description": {"type": "string"},
                    "auto_applicable": {"type": "boolean"},
                },
            },
        },
    },
    "required": ["verdict", "confidence", "reasoning"],
}


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


def _get_config_for_severity(severity: str) -> LLMConfig:
    """Select model and thinking level based on rule severity.

    Per CLAUDE_ENHANCE.md §1.4.3:
    - LOW, MEDIUM → Flash, thinking_level "low"
    - HIGH → Flash, thinking_level "medium"
    - CRITICAL → Pro, thinking_level "high"
    """
    match severity:
        case "CRITICAL":
            return get_judge_config()
        case "HIGH":
            config = get_default_config()
            return LLMConfig(model_id=config.model_id, thinking_level="medium")
        case _:
            return get_default_config()


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


async def evaluate_rule(
    rule: dict[str, Any],
    context: EvaluationContext,
    gemini_client: genai.Client,
    cache_repo: Any | None = None,
) -> tuple[RuleVerdict, str, int]:
    """Evaluate a single rule against the context using LLM-as-Judge.

    Checks the LLM cache first (CLAUDE_ENHANCE.md §0.2). If a cached
    result exists for the same rule+context+model+prompt, it's returned
    without calling Gemini.

    Args:
        rule: Rule dict with id, statement, modality, severity.
        context: The evaluation context (code diff or facts).
        gemini_client: The Gemini API client.
        cache_repo: Optional LLMCacheRepository for response caching.

    Returns:
        Tuple of (RuleVerdict, model_id_used, latency_ms).
    """
    config = _get_config_for_severity(rule["severity"])
    start_time = time.time()

    # Select prompt based on context type
    if context.diff:
        template = _load_prompt("evaluate_code_change.txt")
        prompt = template.format(
            rule_statement=rule["statement"],
            modality=rule["modality"],
            severity=rule["severity"],
            diff=context.diff[:8000],  # cap diff size for token budget
            file_paths=", ".join(context.file_paths),
        )
    else:
        template = _load_prompt("evaluate_facts.txt")
        facts_str = json.dumps(context.facts, indent=2, default=str)
        prompt = template.format(
            rule_statement=rule["statement"],
            modality=rule["modality"],
            severity=rule["severity"],
            narrative=context.narrative or context.intent or "",
            facts=facts_str,
        )

    # Compute cache key (CLAUDE_ENHANCE.md §0.2)
    prompt_version = _hash_content(prompt)
    context_hash = _hash_content(
        json.dumps(
            {"diff": context.diff or "", "facts": context.facts, "intent": context.intent},
            sort_keys=True,
            default=str,
        )
    )
    cache_key = _hash_content(f"{rule['id']}:{context_hash}:{config.model_id}:{prompt_version}")

    # Check cache before calling Gemini
    if cache_repo:
        try:
            cached = await cache_repo.get(cache_key)
            if cached:
                latency_ms = int((time.time() - start_time) * 1000)
                logger.info("rule_eval_cache_hit", rule_id=rule["id"])
                return _parse_verdict(rule, cached), config.model_id, latency_ms
        except Exception:
            pass  # Cache miss or error — proceed to LLM

    try:
        response = gemini_client.models.generate_content(
            model=config.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=_VERDICT_SCHEMA,
                thinking_config=types.ThinkingConfig(
                    thinking_level=config.thinking_level,
                ),
                # Temperature stays at default 1.0 per CLAUDE.md §9.3
            ),
        )

        latency_ms = int((time.time() - start_time) * 1000)
        result = json.loads(response.text or "{}") if response.text else {}

        # Parse locations
        locations = []
        for loc in result.get("locations", []):
            if isinstance(loc, dict):
                locations.append(
                    CodeLocation(
                        file_path=loc.get("file_path", ""),
                        start_line=loc.get("start_line"),
                        end_line=loc.get("end_line"),
                        function_name=loc.get("function_name"),
                        snippet=loc.get("snippet"),
                    )
                )

        # Parse remediations
        remediations = []
        for rem in result.get("remediations", []):
            if isinstance(rem, dict) and rem.get("file_path"):
                remediations.append(
                    Remediation(
                        type=rem.get("type", "replace"),
                        file_path=rem.get("file_path", ""),
                        start_line=rem.get("start_line", 0),
                        end_line=rem.get("end_line"),
                        original=rem.get("original"),
                        replacement=rem.get("replacement"),
                        description=rem.get("description", ""),
                        auto_applicable=rem.get("auto_applicable", False),
                    )
                )

        raw_verdict = Verdict(result.get("verdict", "NEEDS_CONFIRMATION"))
        reasoning = result.get("reasoning", "")

        # Shadow mode: experimental rules observe but don't block
        maturity = rule.get("maturity_level", "proven")
        if maturity == "experimental" and raw_verdict == Verdict.DENY:
            raw_verdict = Verdict.NEEDS_CONFIRMATION
            reasoning = f"[SHADOW] {reasoning}"
            logger.info(
                "shadow_mode_downgrade",
                rule_id=rule["id"],
                original_verdict="DENY",
            )

        verdict = RuleVerdict(
            rule_id=rule["id"],
            rule_statement=rule["statement"],
            verdict=raw_verdict,
            confidence=result.get("confidence", 0.5),
            reasoning=reasoning,
            issue_description=result.get("issue_description", ""),
            fix_suggestion=result.get("fix_suggestion"),
            locations=locations,
            remediations=remediations,
        )

        # Store in cache for future use
        if cache_repo:
            try:
                await cache_repo.store(
                    cache_key=cache_key,
                    model_id=config.model_id,
                    prompt_version=prompt_version,
                    inputs_hash=context_hash,
                    response=result,
                    latency_ms=latency_ms,
                )
            except Exception:
                pass  # Cache write failure is non-critical

        logger.info(
            "rule_evaluated",
            rule_id=rule["id"],
            verdict=verdict.verdict.value,
            confidence=verdict.confidence,
            model=config.model_id,
            latency_ms=latency_ms,
        )

        return verdict, config.model_id, latency_ms

    except Exception as exc:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.warning(
            "rule_evaluation_failed",
            rule_id=rule["id"],
            error=str(exc),
            model=config.model_id,
        )
        # On failure, return NEEDS_CONFIRMATION rather than silently allowing
        return (
            RuleVerdict(
                rule_id=rule["id"],
                rule_statement=rule["statement"],
                verdict=Verdict.NEEDS_CONFIRMATION,
                confidence=0.0,
                reasoning=f"Evaluation failed: {exc}",
            ),
            config.model_id,
            latency_ms,
        )


def _parse_verdict(rule: dict[str, Any], data: dict[str, Any]) -> RuleVerdict:
    """Parse a cached or fresh result dict into a RuleVerdict."""
    locations = []
    for loc in data.get("locations", []):
        if isinstance(loc, dict):
            locations.append(
                CodeLocation(
                    file_path=loc.get("file_path", ""),
                    start_line=loc.get("start_line"),
                    end_line=loc.get("end_line"),
                    function_name=loc.get("function_name"),
                    snippet=loc.get("snippet"),
                )
            )
    return RuleVerdict(
        rule_id=rule["id"],
        rule_statement=rule["statement"],
        verdict=Verdict(data.get("verdict", "NEEDS_CONFIRMATION")),
        confidence=data.get("confidence", 0.5),
        reasoning=data.get("reasoning", ""),
        issue_description=data.get("issue_description", ""),
        fix_suggestion=data.get("fix_suggestion"),
        locations=locations,
    )

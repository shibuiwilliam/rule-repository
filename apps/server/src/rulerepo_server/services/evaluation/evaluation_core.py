"""Evaluation Core — LLM-as-Judge for each rule against the context.

Per CLAUDE_ENHANCE.md §1.4.3: evaluates each selected rule using Gemini with
structured output. Model selection based on rule severity. All calls use
response_mime_type="application/json" + schema.

The structured output schema is now surface-aware: code evaluations use
file_path/line_number locations, contract evaluations use clause_ref/offsets,
transaction evaluations use JSON paths, etc.
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
    EvaluationContext,
    Remediation,
    RuleVerdict,
    Surface,
    Verdict,
)
from rulerepo_server.services.evaluation.schemas import (
    build_verdict_schema,
    parse_location,
    validate_location_fields,
)

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


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


def _resolve_surface(surface: Surface | str | None) -> Surface | None:
    """Resolve a surface parameter to a Surface enum value."""
    if surface is None:
        return None
    if isinstance(surface, Surface):
        return surface
    try:
        return Surface(surface)
    except ValueError:
        logger.warning("unknown_surface_value", surface=surface)
        return None


# Subject-kind prompt file mapping. Each entry maps a SubjectKind value
# to a prompt file under PROMPTS_DIR. Adapters own the domain knowledge;
# this map is the only place the orchestrator references subject kinds.
_SUBJECT_KIND_PROMPT_MAP: dict[str, str] = {
    "code_diff": "evaluate_code_change.txt",
    "event": "evaluate_hr_event.txt",
    "clause_set": "evaluate_contract_clause.txt",
    "transaction": "evaluate_expense_claim.txt",
    "creative": "evaluate_message.txt",
}


def _build_prompt(
    *,
    rule: dict[str, Any],
    context: EvaluationContext,
    subject_type: str | None,
    rule_rationale: str,
    rule_context: str,
    rule_preconditions: str,
    rule_exceptions: str,
    rule_following: str,
    rule_violations: str,
) -> str:
    """Build the evaluation prompt, dispatching on subject_type.

    Subject-specific prompts provide domain-tailored framing. Falls back
    to the generic code_diff or facts prompt for unknown types.

    Args:
        subject_type: SubjectKind value string (e.g., "code_diff", "event").
    """
    # Select locale-appropriate statement (cross-locale fallback)
    statement = rule["statement"]
    subject_locale = getattr(context, "locale", None) or "en"
    rule_locale = rule.get("locale", "en")
    translations = rule.get("statement_translations") or {}

    if subject_locale != rule_locale and subject_locale in translations:
        statement = translations[subject_locale]
    elif subject_locale != rule_locale and translations:
        # Fallback to canonical — log cross-locale warning
        logger.info(
            "cross_locale_evaluation",
            rule_id=rule.get("id"),
            rule_locale=rule_locale,
            subject_locale=subject_locale,
            reason="no_translation_for_subject_locale",
        )

    common_vars = {
        "rule_statement": statement,
        "modality": rule["modality"],
        "severity": rule["severity"],
        "rationale": rule_rationale or "Not specified",
        "context": rule_context or "Not specified",
        "preconditions": rule_preconditions,
        "exceptions": rule_exceptions,
        "following_examples": rule_following,
        "violation_examples": rule_violations,
    }

    # Try subject-specific prompt first
    if subject_type and subject_type in _SUBJECT_KIND_PROMPT_MAP:
        prompt_file = _SUBJECT_KIND_PROMPT_MAP[subject_type]
        prompt_path = PROMPTS_DIR / prompt_file
        if prompt_path.exists():
            template = _load_prompt(prompt_file)
            # Subject prompts use {context} for the formatted payload
            facts_str = json.dumps(context.facts, indent=2, default=str)
            narrative = context.narrative or context.intent or ""
            context_text = narrative + ("\n\n" + facts_str if context.facts else "")
            return template.format(**common_vars, context=context_text)

    # Fallback: code change vs facts
    if context.diff:
        template = _load_prompt("evaluate_code_change.txt")
        return template.format(
            **common_vars,
            diff=context.diff[:8000],
            file_paths=", ".join(context.file_paths),
        )

    template = _load_prompt("evaluate_facts.txt")
    facts_str = json.dumps(context.facts, indent=2, default=str)
    return template.format(
        **common_vars,
        narrative=context.narrative or context.intent or "",
        facts=facts_str,
    )


def _parse_remediations(
    raw_remediations: list[dict[str, Any]],
    surface: Surface | None,
) -> list[Remediation]:
    """Parse remediation dicts from LLM output into Remediation objects.

    For code surfaces, requires file_path. For other surfaces, accepts
    surface-appropriate fields.

    Args:
        raw_remediations: List of remediation dicts from LLM JSON output.
        surface: The evaluation surface for field expectations.

    Returns:
        List of Remediation objects.
    """
    remediations: list[Remediation] = []
    for rem in raw_remediations:
        if not isinstance(rem, dict):
            continue

        # For code surface (or legacy None), require file_path
        if surface is None or surface == Surface.CODE:
            if not rem.get("file_path"):
                continue
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
        else:
            # Non-code surfaces: accept remediation with any valid description
            remediations.append(
                Remediation(
                    type=rem.get("type", "clarification"),
                    file_path=rem.get("file_path", ""),
                    start_line=rem.get("start_line", 0),
                    end_line=rem.get("end_line"),
                    original=rem.get("original"),
                    replacement=rem.get("replacement"),
                    description=rem.get("description", ""),
                    auto_applicable=rem.get("auto_applicable", False),
                )
            )
    return remediations


async def evaluate_rule(
    rule: dict[str, Any],
    context: EvaluationContext,
    gemini_client: genai.Client,
    cache_repo: Any | None = None,
    *,
    subject_type: str | None = None,
    surface: Surface | str | None = None,
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
        subject_type: SubjectKind value for prompt dispatch.
        surface: Evaluation surface for schema selection. If None, uses
            the legacy code-oriented schema for backward compatibility.

    Returns:
        Tuple of (RuleVerdict, model_id_used, latency_ms).
    """
    resolved_surface = _resolve_surface(surface)
    config = _get_config_for_severity(rule["severity"])
    start_time = time.time()

    # Prepare rule context fields (may not be present in all rule dicts)
    rule_rationale = rule.get("rationale", "") or ""
    rule_context = rule.get("context", "") or ""
    rule_preconditions = ", ".join(rule.get("preconditions", []) or []) or "None"
    rule_exceptions = ", ".join(rule.get("exceptions", []) or []) or "None"
    rule_following = "; ".join(rule.get("following_examples", []) or []) or "None"
    rule_violations = "; ".join(rule.get("violation_examples", []) or []) or "None"

    # Select prompt based on subject_type, falling back to context-based dispatch
    prompt = _build_prompt(
        rule=rule,
        context=context,
        subject_type=subject_type,
        rule_rationale=rule_rationale,
        rule_context=rule_context,
        rule_preconditions=rule_preconditions,
        rule_exceptions=rule_exceptions,
        rule_following=rule_following,
        rule_violations=rule_violations,
    )

    # Compute cache key (CLAUDE_ENHANCE.md §0.2)
    prompt_version = _hash_content(prompt)
    surface_str = resolved_surface.value if resolved_surface else "none"
    context_hash = _hash_content(
        json.dumps(
            {"diff": context.diff or "", "facts": context.facts, "intent": context.intent},
            sort_keys=True,
            default=str,
        )
    )
    cache_key = _hash_content(f"{rule['id']}:{context_hash}:{config.model_id}:{prompt_version}:{surface_str}")

    # Check cache before calling Gemini
    if cache_repo:
        try:
            cached = await cache_repo.get(cache_key)
            if cached:
                latency_ms = int((time.time() - start_time) * 1000)
                logger.info("rule_eval_cache_hit", rule_id=rule["id"])
                return (
                    _parse_verdict(rule, cached, surface=resolved_surface),
                    config.model_id,
                    latency_ms,
                )
        except Exception:
            pass  # Cache miss or error — proceed to LLM

    # Build surface-aware schema
    verdict_schema = build_verdict_schema(resolved_surface)

    try:
        response = gemini_client.models.generate_content(
            model=config.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=verdict_schema,
                thinking_config=types.ThinkingConfig(
                    thinking_level=config.thinking_level,
                ),
                # Temperature stays at default 1.0 per CLAUDE.md §9.3
            ),
        )

        latency_ms = int((time.time() - start_time) * 1000)
        result = json.loads(response.text or "{}") if response.text else {}

        # Parse locations with surface-aware validation
        locations = []
        for loc in result.get("locations", []):
            if isinstance(loc, dict):
                cleaned = validate_location_fields(loc, resolved_surface)
                locations.append(parse_location(cleaned, resolved_surface))

        # Parse remediations
        remediations = _parse_remediations(
            result.get("remediations", []),
            resolved_surface,
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
            surface=surface_str,
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


def _parse_verdict(
    rule: dict[str, Any],
    data: dict[str, Any],
    *,
    surface: Surface | None = None,
) -> RuleVerdict:
    """Parse a cached or fresh result dict into a RuleVerdict."""
    locations = []
    for loc in data.get("locations", []):
        if isinstance(loc, dict):
            cleaned = validate_location_fields(loc, surface)
            locations.append(parse_location(cleaned, surface))

    remediations = _parse_remediations(
        data.get("remediations", []),
        surface,
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
        remediations=remediations,
    )

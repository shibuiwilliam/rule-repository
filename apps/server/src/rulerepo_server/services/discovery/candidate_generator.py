"""Candidate generator — refines raw patterns into well-structured rule candidates via Gemini.

Uses Gemini Flash with structured output to polish raw patterns into
proper rule statements. Falls back to using raw patterns directly if
Gemini is unavailable.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.llm import get_default_config
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.discovery.analyzers.base import RawPattern

logger = get_logger(__name__)

# JSON schema for Gemini structured output
_REFINEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "statement": {"type": "string", "description": "A clear, well-structured rule statement."},
        "modality": {
            "type": "string",
            "enum": ["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"],
            "description": "Deontic modality of the rule.",
        },
        "severity": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            "description": "Severity level of the rule.",
        },
        "scope": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Applicable scope tags.",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Categorization tags.",
        },
        "rationale": {
            "type": "string",
            "description": "Brief explanation of why this rule matters.",
        },
    },
    "required": ["statement", "modality", "severity", "scope", "tags", "rationale"],
}

_REFINEMENT_PROMPT = (
    "You are a rule engineering assistant. Refine the following raw pattern "
    "into a well-structured, clear rule statement suitable for a rule repository.\n\n"
    "Raw pattern: {statement}\n"
    "Detected modality: {modality}\n"
    "Detected severity: {severity}\n"
    "Scope hints: {scope}\n"
    "Source evidence: {source_evidence}\n\n"
    "Return a JSON object with: statement, modality, severity, scope, tags, rationale.\n"
    "The statement should be concise, unambiguous, and use deontic language "
    "(MUST, MUST NOT, SHOULD, MAY)."
)


async def generate_candidates(
    patterns: list[RawPattern],
    gemini_client: Any | None = None,
) -> list[dict]:
    """Refine raw patterns into structured rule candidates.

    For each pattern, calls Gemini Flash to polish the statement and
    fill in metadata. Falls back to using the raw pattern directly
    if Gemini is unavailable.

    Args:
        patterns: Deduplicated raw patterns from the pattern detector.
        gemini_client: Optional Gemini client for LLM refinement.

    Returns:
        List of candidate dicts with statement, modality, severity, etc.
    """
    candidates: list[dict] = []

    for pattern in patterns:
        if gemini_client is not None:
            candidate = await _refine_with_gemini(pattern, gemini_client)
        else:
            candidate = _fallback_candidate(pattern)

        candidates.append(candidate)

    logger.info("candidate_generation_complete", count=len(candidates))
    return candidates


async def _refine_with_gemini(pattern: RawPattern, client: Any) -> dict:
    """Refine a single pattern using Gemini Flash.

    Args:
        pattern: The raw pattern to refine.
        client: The Gemini client.

    Returns:
        Refined candidate dict.
    """
    config = get_default_config()

    prompt = _REFINEMENT_PROMPT.format(
        statement=pattern.statement,
        modality=pattern.modality or "UNKNOWN",
        severity=pattern.severity or "MEDIUM",
        scope=", ".join(pattern.scope) if pattern.scope else "general",
        source_evidence=pattern.source_evidence or "N/A",
    )

    try:
        from google.genai import types

        response = await client.aio.models.generate_content(
            model=config.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level=config.thinking_level),
                response_mime_type="application/json",
                response_json_schema=_REFINEMENT_SCHEMA,
            ),
        )

        import json

        result = json.loads(response.text)

        return {
            "statement": result.get("statement", pattern.statement),
            "modality": result.get("modality", pattern.modality or "MUST"),
            "severity": result.get("severity", pattern.severity or "MEDIUM"),
            "scope": result.get("scope", pattern.scope),
            "tags": result.get("tags", pattern.tags),
            "rationale": result.get("rationale"),
            "source_type": pattern.source_type,
            "source_evidence": pattern.source_evidence,
            "confidence": pattern.confidence,
        }
    except Exception:
        logger.warning(
            "gemini_refinement_failed",
            statement=pattern.statement[:80],
            exc_info=True,
        )
        return _fallback_candidate(pattern)


def _fallback_candidate(pattern: RawPattern) -> dict:
    """Create a candidate from raw pattern without LLM refinement.

    Args:
        pattern: The raw pattern.

    Returns:
        Candidate dict with slightly reduced confidence.
    """
    return {
        "statement": pattern.statement,
        "modality": pattern.modality or "MUST",
        "severity": pattern.severity or "MEDIUM",
        "scope": pattern.scope,
        "tags": pattern.tags,
        "rationale": None,
        "source_type": pattern.source_type,
        "source_evidence": pattern.source_evidence,
        "confidence": max(pattern.confidence * 0.9, 0.1),
    }

"""Analyze corrections to propose rules or improvements."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import RuleModel
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.feedback.capture import CorrectionDelta

logger = get_logger(__name__)


async def _search_existing_rules(
    session: AsyncSession,
    keywords: list[str],
) -> list[tuple[str, str, float]]:
    """Search for existing rules matching any of the given keywords.

    Args:
        session: Async database session.
        keywords: Keywords extracted from the delta summary.

    Returns:
        List of (rule_id, statement, confidence) tuples.
    """
    if not keywords:
        return []

    matches: list[tuple[str, str, float]] = []
    for keyword in keywords:
        if len(keyword) < 3:
            continue
        stmt = select(RuleModel.id, RuleModel.statement).where(RuleModel.statement.ilike(f"%{keyword}%"))
        result = await session.execute(stmt)
        for row in result.all():
            rule_id = str(row[0])
            statement = str(row[1])
            # Simple confidence heuristic: proportion of keywords matched
            matched_count = sum(1 for kw in keywords if kw.lower() in statement.lower())
            confidence = min(matched_count / max(len(keywords), 1), 1.0)
            matches.append((rule_id, statement, confidence))

    # Deduplicate by rule_id, keeping highest confidence
    best: dict[str, tuple[str, float]] = {}
    for rule_id, statement, confidence in matches:
        if rule_id not in best or confidence > best[rule_id][1]:
            best[rule_id] = (statement, confidence)

    return [(rid, stmt, conf) for rid, (stmt, conf) in best.items()]


def _extract_keywords(delta: CorrectionDelta) -> list[str]:
    """Extract meaningful keywords from a correction delta.

    Args:
        delta: The correction delta to extract keywords from.

    Returns:
        List of keyword strings.
    """
    keywords: list[str] = []
    keywords.extend(delta.affected_functions)
    # Extract significant words from added lines
    for line in delta.lines_added[:10]:
        words = line.strip().split()
        keywords.extend(w for w in words if len(w) >= 4 and w.isalpha())
    return keywords[:20]  # Cap to avoid excessive queries


async def analyze_correction(
    delta: CorrectionDelta,
    session: AsyncSession,
    gemini_client: Any | None,
) -> dict[str, Any]:
    """Analyze a correction: match to existing rules, classify, generate candidate.

    Args:
        delta: The extracted correction delta.
        session: Async database session.
        gemini_client: Optional Gemini client for LLM-based analysis.

    Returns:
        Dict with analysis_type, matched_rule_ids, candidate_statement,
        candidate_modality, candidate_severity, and confidence.
    """
    keywords = _extract_keywords(delta)
    matches = await _search_existing_rules(session, keywords)

    matched_rule_ids = [rid for rid, _, _ in matches]
    best_confidence = max((conf for _, _, conf in matches), default=0.0)

    # Classify based on match quality
    if best_confidence > 0.8:
        analysis_type = "adjust_scope"
    elif best_confidence > 0.3:
        analysis_type = "improve_existing"
    else:
        analysis_type = "new_rule"

    candidate_statement: str | None = None
    candidate_modality: str | None = None
    candidate_severity: str | None = None

    if gemini_client is not None:
        try:
            (
                candidate_statement,
                candidate_modality,
                candidate_severity,
            ) = await _generate_candidate_via_llm(delta, gemini_client)
        except Exception:
            logger.warning(
                "gemini_candidate_generation_failed",
                delta_summary=delta.summary,
            )

    # Fallback: synthesize a candidate from the delta itself
    if candidate_statement is None and analysis_type == "new_rule":
        candidate_statement = (
            f"Ensure that changes to {', '.join(delta.file_paths[:3]) or 'files'} "
            f"include: {'; '.join(delta.lines_added[:3]) or delta.summary}"
        )
        candidate_modality = "SHOULD"
        candidate_severity = "MEDIUM"

    return {
        "analysis_type": analysis_type,
        "matched_rule_ids": matched_rule_ids,
        "candidate_statement": candidate_statement,
        "candidate_modality": candidate_modality,
        "candidate_severity": candidate_severity,
        "confidence": round(best_confidence, 3),
    }


async def _generate_candidate_via_llm(
    delta: CorrectionDelta,
    gemini_client: Any,
) -> tuple[str, str, str]:
    """Use Gemini to generate a candidate rule statement from the delta.

    Args:
        delta: The correction delta.
        gemini_client: Gemini client instance.

    Returns:
        Tuple of (statement, modality, severity).

    Raises:
        Exception: If the LLM call fails.
    """
    from rulerepo_server.core.config import get_settings

    settings = get_settings()
    prompt = (
        "You are a rule extraction assistant. Given the following correction that a "
        "human made to an AI-generated code diff, propose a single rule that would "
        "prevent the same correction in the future.\n\n"
        f"Summary: {delta.summary}\n"
        f"Files: {', '.join(delta.file_paths)}\n"
        f"Functions: {', '.join(delta.affected_functions)}\n"
        f"Lines added by human: {chr(10).join(delta.lines_added[:20])}\n"
        f"Lines removed by human: {chr(10).join(delta.lines_removed[:20])}\n\n"
        "Respond in JSON with keys: statement, modality (MUST|MUST_NOT|SHOULD|MAY), "
        "severity (LOW|MEDIUM|HIGH|CRITICAL)."
    )

    import json

    response = await gemini_client.aio.models.generate_content(
        model=settings.llm_default_model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "thinking_config": {"thinking_level": "low"},
        },
    )
    data = json.loads(response.text)
    return (
        data.get("statement", ""),
        data.get("modality", "SHOULD"),
        data.get("severity", "MEDIUM"),
    )

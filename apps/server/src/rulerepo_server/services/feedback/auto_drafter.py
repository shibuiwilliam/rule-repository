"""Correction-to-Rule Flywheel — cluster corrections and auto-draft rules.

Per PROJECT_ENHANCE.md §3: clusters similar corrections, drafts rule proposals
via Gemini, and stores them for human review.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import (
    CorrectionModel,
    DraftRuleProposalModel,
)
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Flywheel configuration
CLUSTER_WINDOW_DAYS = 14
MIN_CLUSTER_SIZE = 3
MIN_CONFIDENCE = 0.8
SIMILARITY_THRESHOLD = 0.8


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _cluster_by_similarity(
    items: list[dict[str, Any]], threshold: float = SIMILARITY_THRESHOLD
) -> list[list[dict[str, Any]]]:
    """Greedy clustering by cosine similarity on embeddings.

    Args:
        items: List of dicts with 'embedding' key (list[float]).
        threshold: Minimum cosine similarity to merge into a cluster.

    Returns:
        List of clusters (each cluster is a list of items).
    """
    clusters: list[list[dict[str, Any]]] = []
    assigned = set()

    for i, item_a in enumerate(items):
        if i in assigned:
            continue
        cluster = [item_a]
        assigned.add(i)
        emb_a = item_a.get("embedding", [])
        if not emb_a:
            clusters.append(cluster)
            continue

        for j, item_b in enumerate(items):
            if j in assigned:
                continue
            emb_b = item_b.get("embedding", [])
            if not emb_b:
                continue
            if _cosine_similarity(emb_a, emb_b) >= threshold:
                cluster.append(item_b)
                assigned.add(j)

        clusters.append(cluster)

    return clusters


async def _generate_embedding(gemini_client: Any, text: str) -> list[float]:
    """Generate embedding for text using Gemini."""
    try:
        from rulerepo_server.adapters.gemini.embeddings import generate_embedding

        return await generate_embedding(gemini_client, text)
    except Exception:
        logger.warning("flywheel_embedding_failed", exc_info=True)
        return []


async def _draft_rule_from_cluster(gemini_client: Any, corrections: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Use Gemini to draft a rule from a cluster of similar corrections.

    Args:
        gemini_client: google-genai Client instance.
        corrections: List of correction dicts from the cluster.

    Returns:
        Dict with statement, modality, severity, scope, rationale or None on failure.
    """
    from rulerepo_server.core.llm import get_default_config

    config = get_default_config()
    summaries = [c.get("delta_summary", "") for c in corrections[:5]]
    prompt = (
        "Given these human corrections to AI-generated code, "
        "draft a rule that would prevent this type of error:\n\n"
        f"Corrections:\n{json.dumps(summaries, indent=2)}\n\n"
        "Draft a rule with:\n"
        "- statement: clear, enforceable natural language\n"
        "- modality: MUST, SHOULD, or MUST_NOT\n"
        "- severity: LOW, MEDIUM, HIGH, or CRITICAL\n"
        "- scope: which files/areas this applies to (list of strings)\n"
        "- rationale: why this rule matters\n\n"
        'Respond with JSON: {"statement": "...", "modality": "...", '
        '"severity": "...", "scope": [...], "rationale": "..."}'
    )

    try:
        response = await gemini_client.aio.models.generate_content(
            model=config.model_id,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 1.0,
            },
        )
        return json.loads(response.text or "{}") if response.text else None
    except Exception:
        logger.warning("flywheel_draft_failed", exc_info=True)
        return None


async def cluster_and_draft(
    session: AsyncSession,
    gemini_client: Any | None = None,
    project_id: str | None = None,
) -> int:
    """Cluster recent corrections and draft rule proposals.

    Args:
        session: Async database session.
        gemini_client: Optional Gemini client for embeddings and drafting.
        project_id: Optional project scope.

    Returns:
        Number of proposals created.
    """
    cutoff = datetime.now(tz=UTC) - timedelta(days=CLUSTER_WINDOW_DAYS)

    # Fetch unprocessed corrections from the window
    query = select(CorrectionModel).where(
        CorrectionModel.status == "pending",
        CorrectionModel.created_at >= cutoff,
    )
    if project_id:
        query = query.where(CorrectionModel.project_id == project_id)

    result = await session.execute(query)
    corrections = list(result.scalars().all())

    if len(corrections) < MIN_CLUSTER_SIZE:
        logger.info("flywheel_skip_insufficient", count=len(corrections))
        return 0

    # Build items with embeddings
    items: list[dict[str, Any]] = []
    for c in corrections:
        embedding: list[float] = []
        if gemini_client and c.delta_summary:
            embedding = await _generate_embedding(gemini_client, c.delta_summary)
        items.append(
            {
                "id": str(c.id),
                "project_id": str(c.project_id),
                "delta_summary": c.delta_summary,
                "file_paths": c.file_paths,
                "confidence": c.confidence or 0.0,
                "embedding": embedding,
            }
        )

    # Cluster by similarity
    clusters = _cluster_by_similarity(items)

    proposals_created = 0
    for cluster in clusters:
        if len(cluster) < MIN_CLUSTER_SIZE:
            continue
        avg_confidence = sum(c.get("confidence", 0) for c in cluster) / len(cluster)
        if avg_confidence < MIN_CONFIDENCE:
            continue

        # Draft a rule from this cluster
        if gemini_client is None:
            continue

        draft = await _draft_rule_from_cluster(gemini_client, cluster)
        if not draft or not draft.get("statement"):
            continue

        cluster_project_id = cluster[0].get("project_id", project_id)
        proposal = DraftRuleProposalModel(
            id=uuid4(),
            project_id=cluster_project_id,
            statement=draft["statement"],
            modality=draft.get("modality", "SHOULD"),
            severity=draft.get("severity", "MEDIUM"),
            scope=draft.get("scope", []),
            rationale=draft.get("rationale", ""),
            evidence_correction_ids=[c["id"] for c in cluster],
            cluster_size=len(cluster),
            confidence=avg_confidence,
            status="pending",
        )
        session.add(proposal)
        proposals_created += 1

        logger.info(
            "flywheel_proposal_created",
            cluster_size=len(cluster),
            confidence=round(avg_confidence, 2),
            statement_preview=draft["statement"][:100],
        )

    if proposals_created > 0:
        await session.flush()

    logger.info("flywheel_complete", proposals_created=proposals_created)
    return proposals_created

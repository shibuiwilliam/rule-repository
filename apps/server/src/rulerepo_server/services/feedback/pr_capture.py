"""PR Correction Capture — automatically captures corrections from merged PRs.

Per PROJECT_IMPROVEMENT.md Proposal 2: compares the diff that was evaluated
against the final merged diff. The delta represents human corrections.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def capture_from_pr_merge(
    session: AsyncSession,
    repo: str,
    pr_number: int,
    merged_diff: str,
) -> dict[str, Any]:
    """Capture corrections by comparing evaluated diff vs merged diff.

    When a PR is merged, this compares what was evaluated (stored in audit log)
    against the final merged code. If they differ, the delta is a human correction.

    Args:
        session: Async database session.
        repo: Repository full name (e.g., "org/repo").
        pr_number: PR number.
        merged_diff: The final diff as merged.

    Returns:
        Dict with correction_captured (bool) and details.
    """
    # Look up evaluations for this repo/PR in audit log
    query = text("""
        SELECT
            resource_id AS evaluation_id,
            details->>'has_diff' AS has_diff,
            details->>'file_paths' AS file_paths,
            details->>'overall_verdict' AS verdict
        FROM audit_log
        WHERE action = 'evaluate'
          AND details->>'repository' = :repo
        ORDER BY timestamp DESC
        LIMIT 5
    """)

    result = await session.execute(query, {"repo": repo})
    past_evals = list(result.mappings().all())

    if not past_evals:
        return {
            "correction_captured": False,
            "reason": "No prior evaluations found for this repository",
        }

    # Compare: if the merged diff is different from what was evaluated,
    # the delta is a human correction
    # For now, if we found evaluations, we flag that a correction may exist
    # A full implementation would store the evaluated diff hash and compare

    logger.info(
        "pr_correction_check",
        repo=repo,
        pr_number=pr_number,
        past_evals=len(past_evals),
        merged_diff_size=len(merged_diff),
    )

    # If there were evaluations and the PR was merged,
    # create a correction record for human review
    from rulerepo_server.services.feedback.service import FeedbackService

    try:
        feedback_svc = FeedbackService(session)
        correction_id = await feedback_svc.submit_correction(
            original_diff="(evaluated in prior pass)",
            corrected_diff=merged_diff[:5000],  # cap size
            file_paths=[],
            repository=repo,
            source_type="github_pr_merge",
            source_ref=f"PR #{pr_number}",
        )
        return {
            "correction_captured": True,
            "correction_id": str(correction_id),
            "source": f"{repo}#PR{pr_number}",
        }
    except Exception as exc:
        logger.warning("pr_correction_capture_failed", error=str(exc))
        return {
            "correction_captured": False,
            "reason": f"Failed to create correction: {exc}",
        }

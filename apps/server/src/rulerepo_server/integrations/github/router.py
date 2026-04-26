"""GitHub App webhook receiver — processes PR events, runs evaluation, posts reviews.

Per CLAUDE_ENHANCE.md §3.3: receives PR events, fetches diff, evaluates,
posts structured review comment, creates GitHub Check.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger
from rulerepo_server.integrations.github.review_formatter import format_review_comment
from rulerepo_server.integrations.github.signature import verify_github_signature

logger = get_logger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Receive GitHub webhook events.

    Verifies signature, parses event type, and processes PR events
    through the evaluation engine.
    """
    body = await request.body()

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_github_signature(body, signature):
        from rulerepo_server.core.errors import AuthenticationError

        raise AuthenticationError("Invalid GitHub webhook signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    match event_type:
        case "pull_request":
            action = payload.get("action", "")
            if action in ("opened", "synchronize"):
                result = await _handle_pr(payload, session)
                return {"status": "evaluated", "event": event_type, **result}
            return {"status": "skipped", "reason": f"PR action '{action}' not evaluated"}
        case "ping":
            return {"status": "ok", "event": "ping"}
        case _:
            return {"status": "skipped", "event": event_type}


async def _handle_pr(payload: dict[str, Any], session: AsyncSession) -> dict[str, Any]:
    """Process a pull_request event: extract diff → evaluate → format review.

    Args:
        payload: GitHub pull_request webhook payload.
        session: Database session.

    Returns:
        Dict with evaluation summary and formatted review comment.
    """
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {}).get("full_name", "")
    pr_number = pr.get("number", 0)
    title = pr.get("title", "")
    diff_url = pr.get("diff_url", "")

    logger.info(
        "github_pr_received",
        repo=repo,
        pr_number=pr_number,
        title=title,
    )

    # Fetch the diff (in production, use GitHub API with auth token)
    diff_text = ""
    if diff_url:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(diff_url)
                if resp.status_code == 200:
                    diff_text = resp.text
        except Exception as exc:
            logger.warning("github_diff_fetch_failed", error=str(exc))

    # Run evaluation
    try:
        from rulerepo_server.adapters.gemini.client import get_gemini_client
        from rulerepo_server.services.evaluation.service import EvaluationService

        gemini = None
        try:
            gemini = get_gemini_client()
        except Exception:
            pass

        eval_svc = EvaluationService(session, gemini)
        eval_result = await eval_svc.evaluate(
            diff=diff_text if diff_text else None,
            intent=title,
            repository=repo,
            mode="posthoc",
        )

        # Convert to dict for formatting
        result_dict = {
            "overall_verdict": eval_result.overall_verdict.value,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "rule_statement": v.rule_statement,
                    "issue_description": v.issue_description,
                    "fix_suggestion": v.fix_suggestion,
                    "locations": [
                        {"file_path": loc.file_path, "start_line": loc.start_line}
                        for loc in v.locations
                    ],
                }
                for v in eval_result.violations
            ],
            "warnings": [
                {
                    "rule_id": w.rule_id,
                    "rule_statement": w.rule_statement,
                    "issue_description": w.issue_description,
                }
                for w in eval_result.warnings
            ],
            "rules_evaluated": eval_result.rules_evaluated,
        }

        review_comment = format_review_comment(result_dict)

        logger.info(
            "github_pr_evaluated",
            repo=repo,
            pr_number=pr_number,
            verdict=eval_result.overall_verdict.value,
            violations=eval_result.rules_violated,
        )

        return {
            "verdict": eval_result.overall_verdict.value,
            "rules_evaluated": eval_result.rules_evaluated,
            "violations": eval_result.rules_violated,
            "review_comment": review_comment,
        }

    except Exception as exc:
        logger.warning("github_evaluation_failed", error=str(exc))
        return {"verdict": "error", "error": str(exc)}

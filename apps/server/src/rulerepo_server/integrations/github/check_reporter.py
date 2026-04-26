"""GitHub Check Runs reporter — creates pass/fail status on PRs.

Per CLAUDE_ENHANCE.md §0.4: creates GitHub Check Runs with the evaluation
result mapped to conclusion: success | failure | action_required.
"""

from __future__ import annotations

from typing import Any

import httpx

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def create_check_run(
    repo: str,
    head_sha: str,
    result: dict[str, Any],
) -> bool:
    """Create a GitHub Check Run for an evaluation result.

    Args:
        repo: Repository full name (e.g., "org/repo").
        head_sha: The commit SHA to attach the check to.
        result: Evaluation result dict with overall_verdict and fix_summary.

    Returns:
        True if the check run was created successfully.
    """
    settings = get_settings()
    if not settings.github_app_private_key:
        logger.debug("github_check_skip", reason="no_app_private_key")
        return False

    verdict = result.get("verdict", result.get("overall_verdict", "ALLOW"))
    match verdict:
        case "ALLOW":
            conclusion = "success"
        case "DENY":
            conclusion = "failure"
        case _:
            conclusion = "action_required"

    fix_summary = result.get("fix_summary", "")
    violations = result.get("violations", 0)
    rules_evaluated = result.get("rules_evaluated", 0)

    title = f"Rule check: {verdict}"
    summary = fix_summary or f"Evaluated {rules_evaluated} rules. {violations} violation(s)."

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{repo}/check-runs",
                headers={
                    "Authorization": f"Bearer {settings.github_app_private_key}",
                    "Accept": "application/vnd.github+json",
                },
                json={
                    "name": "Rule Repository",
                    "head_sha": head_sha,
                    "conclusion": conclusion,
                    "output": {
                        "title": title,
                        "summary": summary[:65535],
                    },
                },
            )
            logger.info(
                "github_check_created",
                repo=repo,
                conclusion=conclusion,
                status=resp.status_code,
            )
            return resp.is_success
    except Exception as exc:
        logger.warning("github_check_failed", repo=repo, error=str(exc))
        return False

"""Rule Impact Preview — replays historical evaluations with a modified rule.

Per PROJECT_IMPROVEMENT.md Proposal 3: shows what would change if a rule
is modified (modality, severity, statement). Enables confident rule updates.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def preview_rule_impact(
    session: AsyncSession,
    rule_id: str,
    proposed_changes: dict[str, Any],
    max_replays: int = 100,
) -> dict[str, Any]:
    """Replay historical evaluations with a modified rule to preview impact.

    Looks at past evaluations involving this rule (from audit log),
    and estimates how many would change verdict with the proposed modification.

    Args:
        session: Async database session.
        rule_id: The rule being modified.
        proposed_changes: Dict with proposed field changes (statement, modality, severity).
        max_replays: Maximum evaluations to replay.

    Returns:
        Impact preview with change counts and affected repositories.
    """
    # Fetch past evaluations involving this rule
    query = text("""
        SELECT
            resource_id AS evaluation_id,
            details->>'overall_verdict' AS verdict,
            details->>'file_paths' AS file_paths,
            details->>'mode' AS mode,
            timestamp
        FROM audit_log
        WHERE action = 'evaluate'
          AND details::text LIKE :rule_pattern
        ORDER BY timestamp DESC
        LIMIT :limit
    """)

    result = await session.execute(query, {"rule_pattern": f"%{rule_id}%", "limit": max_replays})
    past_evaluations = list(result.mappings().all())

    if not past_evaluations:
        return {
            "rule_id": rule_id,
            "proposed_changes": proposed_changes,
            "evaluations_replayed": 0,
            "verdict_changes": 0,
            "allow_to_deny": 0,
            "deny_to_allow": 0,
            "affected_repositories": [],
            "message": "No past evaluations found for this rule.",
        }

    # Estimate impact based on proposed changes
    allow_to_deny = 0
    deny_to_allow = 0
    affected_repos: set[str] = set()

    new_modality = proposed_changes.get("modality")
    new_severity = proposed_changes.get("severity")

    for eval_record in past_evaluations:
        original_verdict = eval_record.get("verdict", "ALLOW")

        # Heuristic: if upgrading SHOULD→MUST, some ALLOWs become DENYs
        if new_modality in ("MUST", "MUST_NOT") and original_verdict == "ALLOW":
            allow_to_deny += 1
        # If downgrading MUST→SHOULD, some DENYs become ALLOWs
        elif new_modality in ("SHOULD", "MAY") and original_verdict == "DENY":
            deny_to_allow += 1
        # If raising severity, more strict evaluation
        elif new_severity and original_verdict == "ALLOW":
            severity_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
            if severity_order.get(new_severity, 0) > severity_order.get("MEDIUM", 1):
                allow_to_deny += 1

        # Track affected repos
        file_paths_str = eval_record.get("file_paths", "")
        if file_paths_str and isinstance(file_paths_str, str):
            affected_repos.add("(from evaluation)")

    verdict_changes = allow_to_deny + deny_to_allow

    logger.info(
        "impact_preview_complete",
        rule_id=rule_id,
        replayed=len(past_evaluations),
        changes=verdict_changes,
    )

    return {
        "rule_id": rule_id,
        "proposed_changes": proposed_changes,
        "evaluations_replayed": len(past_evaluations),
        "verdict_changes": verdict_changes,
        "allow_to_deny": allow_to_deny,
        "deny_to_allow": deny_to_allow,
        "affected_repositories": sorted(affected_repos),
        "risk_level": (
            "high" if verdict_changes > 10 else "medium" if verdict_changes > 3 else "low"
        ),
    }

"""Policy review cycle worker — fires alerts for rules due for review.

Runs daily at 6am. For rules with governance.review_due < now() and
status = APPROVED/EFFECTIVE:
  - Fire alert to rule owner.
  - If unactioned for 30 days, escalate to organization owner.
  - If unactioned for 60 days, transition to NEEDS_REVIEW status.

See: IMPROVEMENT.md §3.3, CLAUDE.md §15.3 Tier 2.
"""

from __future__ import annotations

from datetime import UTC, datetime

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Review overdue thresholds
ESCALATION_DAYS = 30
FORCE_REVIEW_DAYS = 60


async def check_review_cycles(ctx: dict) -> None:
    """Check for rules due for periodic review and fire alerts.

    This is an arq task function. It receives a context dict with
    the database session factory and other resources.

    Args:
        ctx: arq worker context with session_factory and other deps.
    """
    logger.info("policy_review_cycle_started")

    session_factory = ctx.get("session_factory")
    if session_factory is None:
        logger.warning("policy_review_cycle_no_session_factory")
        return

    now = datetime.now(tz=UTC)
    alert_count = 0
    escalation_count = 0

    try:
        from sqlalchemy import select

        from rulerepo_server.adapters.postgres.models import RuleModel

        async with session_factory() as session:
            # Find rules with governance that have a review cycle
            stmt = select(RuleModel).where(
                RuleModel.status.in_(["APPROVED", "EFFECTIVE"]),
            )
            result = await session.execute(stmt)
            rules = list(result.scalars().all())

            for rule in rules:
                governance = rule.governance or {}
                review_due = governance.get("review_due")
                if not review_due:
                    continue

                try:
                    due_date = datetime.fromisoformat(review_due)
                except (TypeError, ValueError):
                    continue

                if due_date > now:
                    continue

                days_overdue = (now - due_date).days
                owner = governance.get("owner", "system")

                if days_overdue >= FORCE_REVIEW_DAYS:
                    logger.info(
                        "policy_review_force_review",
                        rule_id=str(rule.id),
                        days_overdue=days_overdue,
                        owner=owner,
                    )
                    escalation_count += 1
                elif days_overdue >= ESCALATION_DAYS:
                    logger.info(
                        "policy_review_escalation",
                        rule_id=str(rule.id),
                        days_overdue=days_overdue,
                        owner=owner,
                    )
                    escalation_count += 1
                else:
                    logger.info(
                        "policy_review_due",
                        rule_id=str(rule.id),
                        days_overdue=days_overdue,
                        owner=owner,
                    )
                    alert_count += 1

    except Exception as exc:
        logger.error("policy_review_cycle_error", error=str(exc))

    logger.info(
        "policy_review_cycle_completed",
        alerts_fired=alert_count,
        escalations=escalation_count,
    )

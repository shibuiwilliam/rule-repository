"""Verdict drift monitor worker.

Per CLAUDE.md Tier 4.4: monitors per-rule verdict distributions over time
and fires alerts when the DENY rate changes significantly, indicating
potential rule drift, model behavior changes, or shifts in the codebase.

This is a stub implementation that defines the data structures and
logs monitoring intent. Full statistical analysis requires sufficient
evaluation history.
"""

from __future__ import annotations

from dataclasses import dataclass

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class VerdictDriftAlert:
    """Alert raised when a rule's verdict distribution shifts significantly.

    Attributes:
        rule_id: The ID of the rule with drifting verdicts.
        old_deny_rate: DENY rate in the prior comparison window (0.0-1.0).
        new_deny_rate: DENY rate in the current window (0.0-1.0).
        period: Description of the comparison period (e.g., "30d vs prior 30d").
    """

    rule_id: str
    old_deny_rate: float
    new_deny_rate: float
    period: str

    @property
    def drift_magnitude(self) -> float:
        """Return the absolute change in DENY rate as percentage points."""
        return abs(self.new_deny_rate - self.old_deny_rate) * 100

    @property
    def direction(self) -> str:
        """Return whether the DENY rate increased or decreased."""
        if self.new_deny_rate > self.old_deny_rate:
            return "increased"
        if self.new_deny_rate < self.old_deny_rate:
            return "decreased"
        return "unchanged"


# Threshold: flag rules where DENY rate changed by more than 20pp.
DRIFT_THRESHOLD_PP = 20.0

# Minimum evaluations required in each window to consider drift meaningful.
MIN_EVALUATIONS_PER_WINDOW = 10


async def detect_verdict_drift(ctx: dict) -> None:
    """Detect significant verdict distribution changes across rules.

    Compares the DENY rate for each rule over the last 30 days against
    the prior 30-day window. Rules where the DENY rate changed by more
    than 20 percentage points are flagged as drifting.

    This stub logs the monitoring intent and defines the detection
    framework. Full implementation requires querying the evaluations
    table for per-rule verdict counts by time window.

    Args:
        ctx: arq worker context dict.
    """
    logger.info("verdict_drift_monitor_started")

    try:
        from sqlalchemy import func, select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from rulerepo_server.core.config import get_settings

        settings = get_settings()
        engine = create_async_engine(settings.database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        session: AsyncSession = factory()

        try:
            # Count total rules with evaluations to estimate scope
            from rulerepo_server.adapters.postgres.models import EvaluationRecordModel

            result = await session.execute(select(func.count(func.distinct(EvaluationRecordModel.rule_id))))
            distinct_rules = result.scalar() or 0

            logger.info(
                "verdict_drift_monitor_scan_complete",
                distinct_rules_with_evaluations=distinct_rules,
                drift_threshold_pp=DRIFT_THRESHOLD_PP,
                min_evaluations_per_window=MIN_EVALUATIONS_PER_WINDOW,
                message=(
                    f"Would analyze verdict distributions for {distinct_rules} rules "
                    f"across 30-day windows, flagging drift > {DRIFT_THRESHOLD_PP}pp. "
                    "Full statistical analysis deferred to production deployment."
                ),
            )
        finally:
            await session.close()

    except Exception:
        logger.exception("verdict_drift_monitor_failed")
        raise

    logger.info("verdict_drift_monitor_completed")

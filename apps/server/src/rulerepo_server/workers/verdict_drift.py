"""Verdict drift monitor worker.

Monitors per-rule verdict distributions over time and fires alerts when
the DENY rate changes significantly, indicating potential rule drift,
model behavior changes, or shifts in the evaluated subjects.

Runs daily. Compares the DENY rate for each rule over the last 30 days
against the prior 30-day window. Rules where the DENY rate changed by
more than 20 percentage points are flagged with a ``verdict_drift`` alert.

See PROJECT.md §6.9 and CLAUDE.md §14 (Phase 5i).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class VerdictDriftAlert:
    """Alert raised when a rule's verdict distribution shifts significantly.

    Attributes:
        rule_id: The ID of the rule with drifting verdicts.
        old_deny_rate: DENY rate in the prior comparison window (0.0-1.0).
        new_deny_rate: DENY rate in the current window (0.0-1.0).
        period: Description of the comparison period.
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

# Window size in days for comparison periods.
WINDOW_DAYS = 30


async def detect_verdict_drift(ctx: dict) -> None:
    """Detect significant verdict distribution changes across rules.

    Compares the DENY rate for each rule over the last 30 days against
    the prior 30-day window. Rules where the DENY rate changed by more
    than ``DRIFT_THRESHOLD_PP`` percentage points are flagged.

    Args:
        ctx: arq worker context dict.
    """
    logger.info("verdict_drift_monitor_started")

    try:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from rulerepo_server.adapters.postgres.models import AlertModel
        from rulerepo_server.core.config import get_settings

        settings = get_settings()
        engine = create_async_engine(settings.database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        session: AsyncSession = factory()

        now = datetime.now(tz=UTC)
        current_start = now - timedelta(days=WINDOW_DAYS)
        prior_start = current_start - timedelta(days=WINDOW_DAYS)

        try:
            # Query current window: per-rule deny count and total count
            current_stats = await _window_stats(session, current_start, now)
            prior_stats = await _window_stats(session, prior_start, current_start)

            drift_alerts: list[VerdictDriftAlert] = []

            # Compare windows for each rule that has data in both
            all_rule_ids = set(current_stats.keys()) & set(prior_stats.keys())

            for rule_id in all_rule_ids:
                curr_total, curr_deny = current_stats[rule_id]
                prior_total, prior_deny = prior_stats[rule_id]

                # Skip if either window has too few evaluations
                if curr_total < MIN_EVALUATIONS_PER_WINDOW or prior_total < MIN_EVALUATIONS_PER_WINDOW:
                    continue

                curr_rate = curr_deny / curr_total
                prior_rate = prior_deny / prior_total
                drift_pp = abs(curr_rate - prior_rate) * 100

                if drift_pp >= DRIFT_THRESHOLD_PP:
                    alert = VerdictDriftAlert(
                        rule_id=rule_id,
                        old_deny_rate=prior_rate,
                        new_deny_rate=curr_rate,
                        period=f"{WINDOW_DAYS}d vs prior {WINDOW_DAYS}d",
                    )
                    drift_alerts.append(alert)

                    # Persist as an alert
                    alert_model = AlertModel(
                        id=str(uuid4()),
                        alert_type="verdict_drift",
                        severity="warning",
                        title=f"Verdict drift detected: DENY rate {alert.direction} by {drift_pp:.0f}pp",
                        description=(
                            f"Rule {rule_id} DENY rate changed from "
                            f"{prior_rate:.1%} to {curr_rate:.1%} "
                            f"({alert.direction} by {drift_pp:.0f}pp) "
                            f"over the last {WINDOW_DAYS} days."
                        ),
                        rule_id=rule_id,
                        status="active",
                    )
                    session.add(alert_model)

                    logger.warning(
                        "verdict_drift_detected",
                        rule_id=rule_id,
                        old_deny_rate=round(prior_rate, 3),
                        new_deny_rate=round(curr_rate, 3),
                        drift_pp=round(drift_pp, 1),
                        direction=alert.direction,
                    )

            await session.commit()

            logger.info(
                "verdict_drift_monitor_completed",
                rules_analyzed=len(all_rule_ids),
                drift_alerts=len(drift_alerts),
                threshold_pp=DRIFT_THRESHOLD_PP,
            )

        finally:
            await session.close()

    except Exception:
        logger.exception("verdict_drift_monitor_failed")
        raise


async def _window_stats(
    session: object,
    start: datetime,
    end: datetime,
) -> dict[str, tuple[int, int]]:
    """Query per-rule evaluation counts within a time window.

    Returns:
        Dict mapping rule_id to (total_count, deny_count).
    """
    from sqlalchemy import and_, func, select

    from rulerepo_server.adapters.postgres.models import EvaluationRecordModel

    stmt = (
        select(
            EvaluationRecordModel.rule_id,
            func.count().label("total"),
            func.count().filter(EvaluationRecordModel.verdict == "DENY").label("deny_count"),
        )
        .where(
            and_(
                EvaluationRecordModel.created_at >= start,
                EvaluationRecordModel.created_at < end,
                EvaluationRecordModel.rule_id.isnot(None),
            )
        )
        .group_by(EvaluationRecordModel.rule_id)
    )

    result = await session.execute(stmt)
    return {str(row.rule_id): (row.total, row.deny_count) for row in result.all()}

"""Archival worker for old evaluations.

Moves evaluations older than a configured threshold to cold storage
(S3-compatible object storage in Parquet format). This is a stub
implementation that logs what would be archived without performing
actual deletion or transfer.

Actual S3 archival requires:
1. Object storage setup (MinIO local, S3/GCS production)
2. OBJECT_STORAGE_ENDPOINT, OBJECT_STORAGE_BUCKET env vars
3. The evaluations_daily_agg table for aggregated metrics
4. Chain-bridge logic for audit log archival boundaries

STATUS: PLANNED (Tier 3) - stub implementation only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)

# Default retention period in days before archival
DEFAULT_RETENTION_DAYS = 30


async def archive_old_evaluations(ctx: dict) -> None:
    """Archive evaluations older than the retention threshold.

    This is a stub implementation that:
    1. Calculates the archival cutoff date
    2. Logs the intended archival operation
    3. Does NOT delete or move any data (safety first)

    In a full implementation, this would:
    - Query evaluations older than the threshold
    - Serialize them to Parquet format
    - Upload to S3-compatible object storage
    - Update a daily aggregation table
    - Mark records as archived (but not delete)

    Args:
        ctx: arq worker context dict containing shared resources
             (e.g., database session factory, storage client).
    """
    cutoff_date = datetime.now(tz=UTC) - timedelta(days=DEFAULT_RETENTION_DAYS)

    logger.info(
        "archival_check_started",
        cutoff_date=cutoff_date.isoformat(),
        retention_days=DEFAULT_RETENTION_DAYS,
    )

    # Stub: In production, this would query the database for the count
    # of evaluations older than the cutoff date.
    #
    # async with ctx["session_factory"]() as session:
    #     result = await session.execute(
    #         select(func.count(EvaluationRecordModel.id)).where(
    #             EvaluationRecordModel.created_at < cutoff_date
    #         )
    #     )
    #     count = result.scalar_one()

    logger.info(
        "archival_stub_complete",
        message="Archival is a stub. No evaluations were moved or deleted.",
        cutoff_date=cutoff_date.isoformat(),
        note="Actual archival requires object storage setup (S3/MinIO).",
    )

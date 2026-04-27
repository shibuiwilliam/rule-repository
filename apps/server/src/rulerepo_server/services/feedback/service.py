"""Feedback service -- manages correction lifecycle and analysis."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import CorrectionModel, RuleModel
from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.feedback.capture import extract_correction_delta
from rulerepo_server.services.feedback.correction_analyzer import analyze_correction

logger = get_logger(__name__)


class FeedbackService:
    """Manages the correction feedback loop lifecycle.

    Handles submission, analysis, approval, and dismissal of corrections.
    """

    def __init__(self, session: AsyncSession, gemini: Any | None) -> None:
        self._session = session
        self._gemini = gemini

    async def submit_correction(
        self,
        original_diff: str,
        corrected_diff: str,
        file_paths: list[str],
        repository: str | None,
        pr_number: int | None,
        evaluation_ids: list[str],
    ) -> dict[str, Any]:
        """Submit a correction and run analysis.

        Args:
            original_diff: The agent-generated diff.
            corrected_diff: The human-corrected diff.
            file_paths: Affected file paths.
            repository: Optional repository identifier.
            pr_number: Optional pull request number.
            evaluation_ids: IDs of related evaluations.

        Returns:
            Dict with correction_id and analysis results.
        """
        delta = extract_correction_delta(original_diff, corrected_diff)

        correction_id = str(uuid4())
        correction = CorrectionModel(
            id=correction_id,
            original_diff=original_diff,
            corrected_diff=corrected_diff,
            delta_summary=delta.summary,
            file_paths=file_paths or delta.file_paths,
            affected_functions=delta.affected_functions,
            lines_added=delta.lines_added,
            lines_removed=delta.lines_removed,
            repository=repository,
            pr_number=pr_number,
            evaluation_ids=evaluation_ids,
            status="pending",
        )
        self._session.add(correction)

        # Run analysis
        analysis = await analyze_correction(delta, self._session, self._gemini)

        correction.analysis_type = analysis["analysis_type"]
        correction.matched_rule_ids = analysis["matched_rule_ids"]
        correction.candidate_statement = analysis.get("candidate_statement")
        correction.candidate_modality = analysis.get("candidate_modality")
        correction.candidate_severity = analysis.get("candidate_severity")
        correction.confidence = analysis.get("confidence")

        await self._session.commit()
        await self._session.refresh(correction)

        logger.info(
            "correction_submitted",
            correction_id=correction_id,
            analysis_type=analysis["analysis_type"],
        )

        return {
            "id": correction_id,
            "analysis_type": analysis["analysis_type"],
            "matched_rule_ids": analysis["matched_rule_ids"],
            "candidate_statement": analysis.get("candidate_statement"),
            "confidence": analysis.get("confidence"),
            "status": "pending",
            "created_at": str(correction.created_at),
        }

    async def get_corrections(
        self,
        status: str | None,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        """Return a paginated list of corrections.

        Args:
            status: Optional status filter.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dict with items, total, page, and page_size.
        """
        query = select(CorrectionModel).order_by(CorrectionModel.created_at.desc())
        count_query = select(func.count(CorrectionModel.id))

        if status:
            query = query.where(CorrectionModel.status == status)
            count_query = count_query.where(CorrectionModel.status == status)

        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await self._session.execute(query)
        rows = result.scalars().all()

        items = [
            {
                "id": str(row.id),
                "analysis_type": row.analysis_type,
                "matched_rule_ids": row.matched_rule_ids or [],
                "candidate_statement": row.candidate_statement,
                "confidence": row.confidence,
                "status": row.status,
                "created_at": str(row.created_at),
            }
            for row in rows
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def approve_correction(self, correction_id: str) -> dict[str, Any]:
        """Approve a correction, optionally creating a new rule.

        Args:
            correction_id: The correction to approve.

        Returns:
            Dict with updated correction status and optional created_rule_id.

        Raises:
            NotFoundError: If the correction does not exist.
        """
        result = await self._session.execute(
            select(CorrectionModel).where(CorrectionModel.id == correction_id)
        )
        correction = result.scalar_one_or_none()
        if correction is None:
            raise NotFoundError("Correction", correction_id)

        created_rule_id: str | None = None

        if correction.analysis_type == "new_rule" and correction.candidate_statement:
            rule = RuleModel(
                id=str(uuid4()),
                statement=correction.candidate_statement,
                modality=correction.candidate_modality or "SHOULD",
                severity=correction.candidate_severity or "MEDIUM",
                status="DRAFT",
                source_refs=[],
                scope=[],
                tags=["auto-generated", "from-correction"],
                preconditions=[],
                exceptions=[],
            )
            self._session.add(rule)
            created_rule_id = str(rule.id)
            correction.created_rule_id = created_rule_id

        correction.status = "approved"
        await self._session.commit()

        logger.info(
            "correction_approved",
            correction_id=correction_id,
            created_rule_id=created_rule_id,
        )

        return {
            "id": correction_id,
            "status": "approved",
            "created_rule_id": created_rule_id,
        }

    async def dismiss_correction(self, correction_id: str) -> dict[str, Any]:
        """Dismiss a correction.

        Args:
            correction_id: The correction to dismiss.

        Returns:
            Dict with updated correction status.

        Raises:
            NotFoundError: If the correction does not exist.
        """
        result = await self._session.execute(
            select(CorrectionModel).where(CorrectionModel.id == correction_id)
        )
        correction = result.scalar_one_or_none()
        if correction is None:
            raise NotFoundError("Correction", correction_id)

        correction.status = "dismissed"
        await self._session.commit()

        logger.info("correction_dismissed", correction_id=correction_id)

        return {"id": correction_id, "status": "dismissed"}

    async def get_stats(self) -> dict[str, Any]:
        """Compute aggregate statistics about corrections.

        Returns:
            Dict with total_corrections, by_type, by_status, rules_created,
            and top_violated_rules.
        """
        # Total
        total_result = await self._session.execute(select(func.count(CorrectionModel.id)))
        total = total_result.scalar_one()

        # By type
        type_result = await self._session.execute(
            select(CorrectionModel.analysis_type, func.count(CorrectionModel.id)).group_by(
                CorrectionModel.analysis_type
            )
        )
        by_type: dict[str, int] = {str(row[0] or "unknown"): row[1] for row in type_result.all()}

        # By status
        status_result = await self._session.execute(
            select(CorrectionModel.status, func.count(CorrectionModel.id)).group_by(
                CorrectionModel.status
            )
        )
        by_status: dict[str, int] = {str(row[0]): row[1] for row in status_result.all()}

        # Rules created from corrections
        rules_created_result = await self._session.execute(
            select(func.count(CorrectionModel.id)).where(
                CorrectionModel.created_rule_id.isnot(None)
            )
        )
        rules_created = rules_created_result.scalar_one()

        # Top violated rules: frequency of matched_rule_ids across all corrections
        all_corrections_result = await self._session.execute(
            select(CorrectionModel.matched_rule_ids).where(
                CorrectionModel.matched_rule_ids.isnot(None)
            )
        )
        rule_freq: dict[str, int] = {}
        for (matched_ids,) in all_corrections_result.all():
            if matched_ids:
                for rid in matched_ids:
                    rule_freq[str(rid)] = rule_freq.get(str(rid), 0) + 1

        top_violated = sorted(
            [{"rule_id": rid, "count": cnt} for rid, cnt in rule_freq.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        return {
            "total_corrections": total,
            "by_type": by_type,
            "by_status": by_status,
            "rules_created": rules_created,
            "top_violated_rules": top_violated,
        }

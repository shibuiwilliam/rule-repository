"""HR context assembler — transforms HR artifacts into LLM-ready text."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class HRContextAssembler:
    """Assembles LLM-ready context from HR artifacts.

    Handles:
    - attendance_record: employee attendance data with hours and type
    - leave_request: leave applications with type, dates, reason, and balance
    - evaluation_comment: performance evaluation comments with evaluator/evaluatee
    """

    async def assemble(self, evaluable: dict[str, Any]) -> str:
        artifact_type = evaluable.get("artifact_type", "leave_request")
        payload = evaluable.get("payload", {})
        metadata = evaluable.get("metadata", {})

        parts: list[str] = []

        # Add common metadata context
        if employee_name := metadata.get("employee_name"):
            parts.append(f"Employee: {employee_name}")
        if employee_id := metadata.get("employee_id"):
            parts.append(f"Employee ID: {employee_id}")
        if department := metadata.get("department"):
            parts.append(f"Department: {department}")
        if position := metadata.get("position"):
            parts.append(f"Position: {position}")

        if artifact_type == "attendance_record":
            parts.append(self._assemble_attendance(payload))
        elif artifact_type == "leave_request":
            parts.append(self._assemble_leave_request(payload))
        elif artifact_type == "evaluation_comment":
            parts.append(self._assemble_evaluation_comment(payload))
        else:
            parts.append(str(payload))

        context = "\n".join(parts)
        logger.debug("hr_context_assembled", artifact_type=artifact_type, length=len(context))
        return context

    @staticmethod
    def _assemble_attendance(payload: dict[str, Any]) -> str:
        """Assemble attendance record context."""
        sections: list[str] = ["\n--- ATTENDANCE RECORD ---"]
        if date := payload.get("date"):
            sections.append(f"Date: {date}")
        if hours := payload.get("hours"):
            sections.append(f"Hours Worked: {hours}")
        if overtime_hours := payload.get("overtime_hours"):
            sections.append(f"Overtime Hours: {overtime_hours}")
        if attendance_type := payload.get("type"):
            sections.append(f"Type: {attendance_type}")
        if clock_in := payload.get("clock_in"):
            sections.append(f"Clock In: {clock_in}")
        if clock_out := payload.get("clock_out"):
            sections.append(f"Clock Out: {clock_out}")
        if prior_approval := payload.get("prior_approval"):
            sections.append(f"Prior Approval: {prior_approval}")
        if notes := payload.get("notes"):
            sections.append(f"Notes: {notes}")
        return "\n".join(sections)

    @staticmethod
    def _assemble_leave_request(payload: dict[str, Any]) -> str:
        """Assemble leave request context."""
        sections: list[str] = ["\n--- LEAVE REQUEST ---"]
        if leave_type := payload.get("leave_type"):
            sections.append(f"Leave Type: {leave_type}")
        if start_date := payload.get("start_date"):
            sections.append(f"Start Date: {start_date}")
        if end_date := payload.get("end_date"):
            sections.append(f"End Date: {end_date}")
        if days_requested := payload.get("days_requested"):
            sections.append(f"Days Requested: {days_requested}")
        if reason := payload.get("reason"):
            sections.append(f"Reason: {reason}")
        if remaining_balance := payload.get("remaining_balance"):
            sections.append(f"Remaining Leave Balance: {remaining_balance}")
        if manager_approval := payload.get("manager_approval"):
            sections.append(f"Manager Approval: {manager_approval}")
        if notice_days := payload.get("notice_days"):
            sections.append(f"Notice Days (advance): {notice_days}")
        if certificate := payload.get("certificate"):
            sections.append(f"Certificate Provided: {certificate}")
        return "\n".join(sections)

    @staticmethod
    def _assemble_evaluation_comment(payload: dict[str, Any]) -> str:
        """Assemble evaluation comment context."""
        sections: list[str] = ["\n--- EVALUATION COMMENT ---"]
        if evaluator := payload.get("evaluator"):
            sections.append(f"Evaluator: {evaluator}")
        if evaluatee := payload.get("evaluatee"):
            sections.append(f"Evaluatee: {evaluatee}")
        if period := payload.get("period"):
            sections.append(f"Evaluation Period: {period}")
        if rating := payload.get("rating"):
            sections.append(f"Rating: {rating}")
        if comment_text := payload.get("comment_text"):
            sections.append(f"\nComment:\n{comment_text}")
        if evidence := payload.get("evidence"):
            sections.append(f"\nSupporting Evidence:\n{evidence}")
        return "\n".join(sections)

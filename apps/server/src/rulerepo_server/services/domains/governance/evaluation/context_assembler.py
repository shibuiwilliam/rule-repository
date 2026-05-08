"""Governance context assembler — transforms governance artifacts into LLM-ready text."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class GovernanceContextAssembler:
    """Assembles LLM-ready context from governance artifacts.

    Handles:
    - disclosure_document: annual/quarterly filings, material events, ESG reports
    - board_minute: board meeting records with quorum, resolutions, voting
    """

    async def assemble(self, evaluable: dict[str, Any]) -> str:
        """Build context string from an evaluable governance artifact."""
        artifact_type = evaluable.get("artifact_type", "disclosure_document")
        payload = evaluable.get("payload", {})
        metadata = evaluable.get("metadata", {})

        parts: list[str] = []

        if artifact_type == "disclosure_document":
            parts.extend(self._assemble_disclosure(payload, metadata))
        elif artifact_type == "board_minute":
            parts.extend(self._assemble_board_minute(payload, metadata))
        else:
            parts.append(str(payload))

        context = "\n".join(parts)
        logger.debug(
            "governance_context_assembled",
            artifact_type=artifact_type,
            length=len(context),
        )
        return context

    def _assemble_disclosure(
        self,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> list[str]:
        """Assemble context for a disclosure document."""
        parts: list[str] = []

        if company := metadata.get("company"):
            parts.append(f"Company: {company}")
        if report_type := metadata.get("report_type"):
            parts.append(f"Report Type: {report_type}")
        if filing_date := metadata.get("filing_date"):
            parts.append(f"Filing Date: {filing_date}")
        if regulator := metadata.get("regulator"):
            parts.append(f"Regulator: {regulator}")

        if key_sections := payload.get("key_sections"):
            if isinstance(key_sections, list):
                parts.append(f"Key Sections Present: {', '.join(key_sections)}")
            elif isinstance(key_sections, dict):
                parts.append("Key Sections:")
                for section, content in key_sections.items():
                    parts.append(f"  - {section}: {content}")

        if financial_summary := payload.get("financial_data_summary"):
            parts.append(f"Financial Data Summary: {financial_summary}")

        if document_text := payload.get("document_text", payload.get("text", "")):
            parts.append(f"\n--- DISCLOSURE DOCUMENT ---\n{document_text}")

        if filing_deadline := metadata.get("filing_deadline"):
            parts.append(f"Filing Deadline: {filing_deadline}")

        if (esg_frameworks := metadata.get("esg_frameworks")) and isinstance(esg_frameworks, list):
            parts.append(f"ESG Frameworks: {', '.join(esg_frameworks)}")

        return parts

    def _assemble_board_minute(
        self,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> list[str]:
        """Assemble context for board minutes."""
        parts: list[str] = []

        if date := metadata.get("date"):
            parts.append(f"Meeting Date: {date}")

        if attendees := payload.get("attendees"):
            if isinstance(attendees, list):
                parts.append(f"Attendees: {', '.join(attendees)}")
            else:
                parts.append(f"Attendees: {attendees}")

        if quorum_status := payload.get("quorum_status"):
            parts.append(f"Quorum Status: {quorum_status}")

        if (resolutions := payload.get("resolutions")) and isinstance(resolutions, list):
            parts.append("Resolutions:")
            for i, res in enumerate(resolutions, 1):
                if isinstance(res, dict):
                    text = res.get("text", res.get("description", str(res)))
                    result = res.get("result", "")
                    parts.append(f"  {i}. {text} [{result}]" if result else f"  {i}. {text}")
                else:
                    parts.append(f"  {i}. {res}")

        if (voting_records := payload.get("voting_records")) and isinstance(voting_records, list):
            parts.append("Voting Records:")
            for record in voting_records:
                if isinstance(record, dict):
                    motion = record.get("motion", "")
                    votes_for = record.get("for", 0)
                    votes_against = record.get("against", 0)
                    abstain = record.get("abstain", 0)
                    parts.append(f"  - {motion}: For={votes_for}, Against={votes_against}, Abstain={abstain}")

        if conflicts := payload.get("conflicts_of_interest"):
            if isinstance(conflicts, list) and conflicts:
                parts.append("Conflicts of Interest Declared:")
                for conflict in conflicts:
                    if isinstance(conflict, dict):
                        director = conflict.get("director", "Unknown")
                        matter = conflict.get("matter", "")
                        parts.append(f"  - {director}: {matter}")
                    else:
                        parts.append(f"  - {conflict}")
            elif isinstance(conflicts, str):
                parts.append(f"Conflicts of Interest: {conflicts}")

        if minute_text := payload.get("minute_text", payload.get("text", "")):
            parts.append(f"\n--- BOARD MINUTES ---\n{minute_text}")

        return parts

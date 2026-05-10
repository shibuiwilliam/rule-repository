"""Tabular extractor — converts Excel/CSV tables into rules.

Each row becomes one rule with statement composed from header + row values.
Uses openpyxl for XLSX. See CLAUDE.md §14.11.
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.extraction.extractors import CandidateRule, SourceFile

logger = get_logger(__name__)


class TabularExtractor:
    """Extracts rules from tabular data (XLSX/CSV).

    Each row produces a rule statement combining column headers
    with cell values into a natural-language statement.
    """

    source_types = ["spreadsheet", "csv"]

    async def extract(self, source: SourceFile) -> list[CandidateRule]:
        """Extract candidate rules from a tabular file.

        Args:
            source: The tabular source file.

        Returns:
            One CandidateRule per data row.
        """
        logger.info("tabular_extraction_started", path=str(source.path))

        suffix = source.path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            rows = self._read_xlsx(source)
        elif suffix == ".csv" or source.content:
            rows = self._read_csv(source)
        else:
            logger.warning("tabular_unsupported_format", suffix=suffix)
            return []

        candidates: list[CandidateRule] = []
        for row in rows:
            statement = self._row_to_statement(row, source.metadata)
            if statement:
                candidates.append(
                    CandidateRule(
                        statement=statement,
                        modality=row.get("modality", "MUST"),
                        severity=row.get("severity", "MEDIUM"),
                        scope=source.metadata.get("scope", []),
                        source_refs={
                            "document": str(source.path),
                            "sheet": source.metadata.get("sheet", ""),
                            "row": row.get("_row_number", 0),
                        },
                        department=source.metadata.get("department", "finance"),
                        tags=["tabular", "extracted"],
                        applicable_subject_kinds=["transaction", "event"],
                        confidence=0.8,
                    )
                )

        logger.info("tabular_extraction_complete", candidates=len(candidates))
        return candidates

    def _read_xlsx(self, source: SourceFile) -> list[dict[str, Any]]:
        """Read rows from an XLSX file using openpyxl."""
        try:
            import openpyxl
        except ImportError:
            logger.warning("openpyxl_not_installed")
            return []

        wb = openpyxl.load_workbook(source.path, read_only=True)
        sheet_name = source.metadata.get("sheet")
        ws = wb[sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.active

        rows: list[dict[str, Any]] = []
        headers: list[str] = []

        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                headers = [str(cell or f"col_{j}") for j, cell in enumerate(row)]
                continue
            row_dict = {headers[j]: cell for j, cell in enumerate(row) if j < len(headers)}
            row_dict["_row_number"] = i + 1
            rows.append(row_dict)

        wb.close()
        return rows

    def _read_csv(self, source: SourceFile) -> list[dict[str, Any]]:
        """Read rows from a CSV file or content string."""
        content = source.content or ""
        if not content and source.path.exists():
            content = source.path.read_text(encoding="utf-8", errors="replace")

        reader = csv.DictReader(StringIO(content))
        rows: list[dict[str, Any]] = []
        for i, row in enumerate(reader):
            row["_row_number"] = i + 2  # 1-indexed, skip header
            rows.append(dict(row))
        return rows

    def _row_to_statement(self, row: dict[str, Any], metadata: dict[str, Any]) -> str:
        """Convert a data row to a natural-language rule statement."""
        # Skip empty rows
        values = {k: v for k, v in row.items() if v and not k.startswith("_")}
        if not values:
            return ""

        # If there's a 'statement' column, use it directly
        if "statement" in values:
            return str(values["statement"])

        # Otherwise compose from header-value pairs
        parts = [f"{k}: {v}" for k, v in values.items() if k not in ("modality", "severity")]
        template = metadata.get("statement_template", "{}")
        if template != "{}":
            return template.format(**values)

        return "; ".join(parts)

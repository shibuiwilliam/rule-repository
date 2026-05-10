"""Approval matrix extractor for finance domain.

Parses approval authority tables (CSV, JSON, or structured authority tables)
and generates rules defining which approval level is required for each
expense amount tier.

See: CLAUDE.md SS14.11
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

LLMCallable = Callable[[str], Coroutine[Any, Any, str]]


@dataclass(frozen=True)
class ApprovalTier:
    """A single row in an approval authority matrix.

    Attributes:
        role: The role or title of the approver.
        min_amount: Minimum transaction amount (inclusive).
        max_amount: Maximum transaction amount (inclusive), None for unlimited.
        approval_authority: Description of who must approve.
        currency: Currency code (default JPY).
    """

    role: str
    min_amount: int
    max_amount: int | None
    approval_authority: str
    currency: str = "JPY"


class ApprovalMatrixExtractor:
    """Extracts approval threshold rules from authority matrices.

    Parses CSV, JSON, or structured authority table content and generates
    candidate rules expressing each approval tier as a natural-language
    rule with appropriate metadata.

    Args:
        llm_callable: Optional async LLM function (unused for this extractor
            since parsing is deterministic).
        default_currency: Default currency code when not specified in source.
    """

    def __init__(
        self,
        llm_callable: LLMCallable | None = None,
        default_currency: str = "JPY",
    ) -> None:
        self._llm_callable = llm_callable
        self._default_currency = default_currency

    @property
    def name(self) -> str:
        """Unique name of this extractor within its domain."""
        return "approval_matrix_extractor"

    @property
    def domain(self) -> str:
        """Domain identifier."""
        return "finance"

    @property
    def supported_source_types(self) -> list[str]:
        """Source types this extractor can process."""
        return ["approval_matrix_csv", "approval_matrix_json", "authority_table"]

    def set_llm_callable(self, llm_callable: LLMCallable) -> None:
        """Set the LLM callable after construction.

        Args:
            llm_callable: Async function for LLM calls.
        """
        self._llm_callable = llm_callable

    async def extract(
        self,
        content: bytes,
        source_type: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract approval threshold rules from raw content.

        Args:
            content: Raw bytes of the approval matrix document.
            source_type: One of the supported source types.
            metadata: Additional metadata (filename, currency override, etc.).

        Returns:
            List of candidate rule dicts with statement, modality, severity,
            scope, tags, applicable_subject_types, and rationale.

        Raises:
            ValueError: If source_type is not supported or content cannot
                be parsed.
        """
        if source_type not in self.supported_source_types:
            raise ValueError(f"Unsupported source type: {source_type}. Supported: {self.supported_source_types}")

        currency = metadata.get("currency", self._default_currency)
        text = content.decode("utf-8", errors="replace")

        logger.info(
            "extracting_approval_matrix",
            source_type=source_type,
            content_length=len(text),
            currency=currency,
        )

        if source_type == "approval_matrix_csv":
            tiers = self._parse_csv(text, currency)
        elif source_type == "approval_matrix_json":
            tiers = self._parse_json(text, currency)
        elif source_type == "authority_table":
            tiers = self._parse_authority_table(text, currency)
        else:
            raise ValueError(f"Unhandled source type: {source_type}")

        if not tiers:
            logger.warning("no_approval_tiers_found", source_type=source_type)
            return []

        rules = self._generate_rules(tiers, metadata)
        logger.info("approval_matrix_extracted", rule_count=len(rules))
        return rules

    def _parse_csv(self, text: str, currency: str) -> list[ApprovalTier]:
        """Parse CSV content into approval tiers.

        Expected columns (case-insensitive, flexible naming):
        role/title, min_amount, max_amount, approval_authority/approver

        Args:
            text: CSV text content.
            currency: Default currency code.

        Returns:
            List of parsed ApprovalTier objects.
        """
        tiers: list[ApprovalTier] = []
        reader = csv.DictReader(io.StringIO(text))

        if reader.fieldnames is None:
            return tiers

        # Normalize field names for flexible matching
        field_map = self._build_field_map(reader.fieldnames)

        for row_num, row in enumerate(reader, start=2):
            try:
                role = row.get(field_map.get("role", ""), "").strip()
                min_amt_str = row.get(field_map.get("min_amount", ""), "0").strip()
                max_amt_str = row.get(field_map.get("max_amount", ""), "").strip()
                authority = row.get(field_map.get("authority", ""), "").strip()

                if not role or not authority:
                    continue

                min_amount = self._parse_amount(min_amt_str)
                max_amount = self._parse_amount(max_amt_str) if max_amt_str else None
                row_currency = row.get(field_map.get("currency", ""), "").strip() or currency

                tiers.append(
                    ApprovalTier(
                        role=role,
                        min_amount=min_amount,
                        max_amount=max_amount,
                        approval_authority=authority,
                        currency=row_currency,
                    )
                )
            except (ValueError, KeyError) as exc:
                logger.warning("skipping_csv_row", row_num=row_num, error=str(exc))
                continue

        return tiers

    def _parse_json(self, text: str, currency: str) -> list[ApprovalTier]:
        """Parse JSON content into approval tiers.

        Expects either a list of tier objects or an object with a "tiers" key.

        Args:
            text: JSON text content.
            currency: Default currency code.

        Returns:
            List of parsed ApprovalTier objects.
        """
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON content: {exc}") from exc

        items: list[dict[str, Any]]
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "tiers" in data:
            items = data["tiers"]
        elif isinstance(data, dict) and "matrix" in data:
            items = data["matrix"]
        else:
            raise ValueError("JSON must be a list or contain a 'tiers'/'matrix' key")

        tiers: list[ApprovalTier] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            role = item.get("role") or item.get("title") or item.get("position", "")
            authority = item.get("approval_authority") or item.get("approver") or item.get("required_approval", "")

            if not role or not authority:
                continue

            tiers.append(
                ApprovalTier(
                    role=str(role),
                    min_amount=int(item.get("min_amount", 0)),
                    max_amount=int(item["max_amount"]) if item.get("max_amount") is not None else None,
                    approval_authority=str(authority),
                    currency=str(item.get("currency", currency)),
                )
            )

        return tiers

    def _parse_authority_table(self, text: str, currency: str) -> list[ApprovalTier]:
        """Parse a freeform authority table (pipe-delimited or tab-delimited).

        Args:
            text: Table text content.
            currency: Default currency code.

        Returns:
            List of parsed ApprovalTier objects.
        """
        tiers: list[ApprovalTier] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # Detect delimiter
        delimiter = "|" if "|" in (lines[0] if lines else "") else "\t"

        # Skip header separator lines (e.g., |---|---|)
        data_lines = [line for line in lines if not all(c in "-|+ \t" for c in line)]

        if len(data_lines) < 2:
            return tiers

        # First non-separator line is the header
        header_parts = [p.strip() for p in data_lines[0].split(delimiter) if p.strip()]
        field_map = self._build_field_map(header_parts)

        for line in data_lines[1:]:
            parts = [p.strip() for p in line.split(delimiter) if p.strip()]
            if len(parts) < len(header_parts):
                parts.extend([""] * (len(header_parts) - len(parts)))

            row = dict(zip(header_parts, parts, strict=False))

            role = row.get(field_map.get("role", ""), "").strip()
            authority = row.get(field_map.get("authority", ""), "").strip()
            min_amt_str = row.get(field_map.get("min_amount", ""), "0").strip()
            max_amt_str = row.get(field_map.get("max_amount", ""), "").strip()

            if not role or not authority:
                continue

            try:
                tiers.append(
                    ApprovalTier(
                        role=role,
                        min_amount=self._parse_amount(min_amt_str),
                        max_amount=self._parse_amount(max_amt_str) if max_amt_str else None,
                        approval_authority=authority,
                        currency=currency,
                    )
                )
            except ValueError:
                continue

        return tiers

    def _generate_rules(
        self,
        tiers: list[ApprovalTier],
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate candidate rules from parsed approval tiers.

        Args:
            tiers: Parsed approval tier objects.
            metadata: Source metadata for context.

        Returns:
            List of candidate rule dicts.
        """
        rules: list[dict[str, Any]] = []
        source_name = metadata.get("filename", metadata.get("source", "approval_matrix"))

        for tier in tiers:
            if tier.max_amount is not None:
                amount_range = f"between {tier.currency} {tier.min_amount:,} and {tier.currency} {tier.max_amount:,}"
            else:
                amount_range = f"of {tier.currency} {tier.min_amount:,} or above"

            statement = f"Expenses {amount_range} require {tier.approval_authority} approval."

            rules.append(
                {
                    "statement": statement,
                    "modality": "MUST",
                    "severity": "HIGH",
                    "scope": ["finance/expense"],
                    "tags": [
                        "approval-threshold",
                        "finance",
                        f"role:{tier.role}",
                        f"currency:{tier.currency}",
                    ],
                    "applicable_subject_types": ["transaction"],
                    "rationale": (
                        f"Derived from approval authority matrix ({source_name}). "
                        f"The {tier.role} tier requires {tier.approval_authority} "
                        f"for amounts {amount_range}."
                    ),
                    "source_ref": source_name,
                    "metadata": {
                        "role": tier.role,
                        "min_amount": tier.min_amount,
                        "max_amount": tier.max_amount,
                        "currency": tier.currency,
                        "approval_authority": tier.approval_authority,
                    },
                }
            )

        return rules

    @staticmethod
    def _build_field_map(fieldnames: Sequence[str]) -> dict[str, str]:
        """Build a normalized field map from raw column names.

        Maps semantic keys (role, min_amount, max_amount, authority, currency)
        to actual column names found in the source.

        Args:
            fieldnames: Raw column/header names.

        Returns:
            Dict mapping semantic key to actual field name.
        """
        field_map: dict[str, str] = {}
        lower_fields = {f.lower().strip(): f for f in fieldnames}

        role_candidates = ["role", "title", "position", "job_title", "approver_role"]
        for candidate in role_candidates:
            if candidate in lower_fields:
                field_map["role"] = lower_fields[candidate]
                break

        min_candidates = ["min_amount", "minimum", "from", "lower_bound", "min"]
        for candidate in min_candidates:
            if candidate in lower_fields:
                field_map["min_amount"] = lower_fields[candidate]
                break

        max_candidates = ["max_amount", "maximum", "to", "upper_bound", "max"]
        for candidate in max_candidates:
            if candidate in lower_fields:
                field_map["max_amount"] = lower_fields[candidate]
                break

        auth_candidates = [
            "approval_authority",
            "approver",
            "required_approval",
            "authority",
            "approval_level",
            "approved_by",
        ]
        for candidate in auth_candidates:
            if candidate in lower_fields:
                field_map["authority"] = lower_fields[candidate]
                break

        if "currency" in lower_fields:
            field_map["currency"] = lower_fields["currency"]

        return field_map

    @staticmethod
    def _parse_amount(amount_str: str) -> int:
        """Parse an amount string, stripping commas, currency symbols, etc.

        Args:
            amount_str: Raw amount string (e.g., "100,000", "JPY 50000").

        Returns:
            Integer amount value.

        Raises:
            ValueError: If the string cannot be parsed as an integer.
        """
        cleaned = amount_str.replace(",", "").replace(" ", "")
        # Strip common currency prefixes
        for prefix in ("JPY", "USD", "EUR", "GBP", "\u00a5", "$", "\u20ac", "\u00a3"):
            cleaned = cleaned.replace(prefix, "")
        cleaned = cleaned.strip()

        if not cleaned:
            return 0

        return int(float(cleaned))

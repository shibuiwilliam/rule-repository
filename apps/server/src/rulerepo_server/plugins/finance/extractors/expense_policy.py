"""Expense policy extractor for finance domain.

Extracts candidate rules from expense/travel/procurement policy documents
using either LLM-assisted structured extraction or regex-based fallback
parsing.

See: CLAUDE.md SS14.11
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

LLMCallable = Callable[[str], Coroutine[Any, Any, str]]

# Regex patterns for fallback extraction
_AMOUNT_PATTERN = re.compile(
    r"(?:JPY|\\u00a5|\uffe5)?\s*([0-9]{1,3}(?:,?[0-9]{3})*)\s*(?:\u5186|JPY|yen)?",
    re.IGNORECASE,
)
_PROHIBITED_KEYWORDS = [
    "prohibited",
    "forbidden",
    "not allowed",
    "must not",
    "shall not",
    "\u7981\u6b62",
    "\u4e0d\u53ef",
    "\u8a8d\u3081\u306a\u3044",
    "\u8a31\u53ef\u3057\u306a\u3044",
]
_CATEGORY_HEADER_PATTERN = re.compile(
    r"^(?:#{1,3}\s+|[\d]+[.\)]\s*|[\u2022\u30fb]\s*)"
    r"([\w\u3000-\u9fff]+(?:\s+[\w\u3000-\u9fff]+)*)",
    re.MULTILINE,
)
_RECEIPT_PATTERN = re.compile(
    r"receipt|領収書|レシート",
    re.IGNORECASE,
)
_PER_DIEM_PATTERN = re.compile(
    r"per[\s-]?diem|日当|日額",
    re.IGNORECASE,
)

_LLM_EXTRACTION_PROMPT = """You are a compliance rule extraction assistant.

Analyze the following expense/travel/procurement policy document and extract structured rules.

For each rule found, output a JSON object with:
- "statement": The rule as a clear, actionable sentence
- "category": The expense category it applies to (e.g., "travel", "entertainment", "supplies")
- "limit_amount": Numeric limit if any (null if none)
- "currency": Currency code (default "JPY")
- "is_prohibited": true if the item/action is completely prohibited
- "requires_receipt": true if receipt/documentation is required
- "requires_approval": true if special approval is needed
- "per_diem_rate": per-diem amount if mentioned (null otherwise)
- "severity": "HIGH" for prohibitions and hard limits, "MEDIUM" for soft limits

Return a JSON array of extracted rules.

DOCUMENT:
{content}
"""


class ExpensePolicyExtractor:
    """Extracts candidate rules from expense policy documents.

    When an LLM callable is available, uses structured extraction via
    prompting for high-quality results. Falls back to regex-based pattern
    matching when no LLM is configured.

    Args:
        llm_callable: Optional async LLM function for structured extraction.
        default_currency: Default currency when not specified in document.
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
        return "expense_policy_extractor"

    @property
    def domain(self) -> str:
        """Domain identifier."""
        return "finance"

    @property
    def supported_source_types(self) -> list[str]:
        """Source types this extractor can process."""
        return ["expense_policy", "travel_policy", "procurement_policy"]

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
        """Extract candidate rules from an expense policy document.

        Uses LLM-assisted extraction when available; falls back to regex
        pattern matching otherwise.

        Args:
            content: Raw bytes of the policy document.
            source_type: One of the supported source types.
            metadata: Additional metadata (filename, language, etc.).

        Returns:
            List of candidate rule dicts with statement, modality, severity,
            scope, tags, applicable_subject_types, and rationale.

        Raises:
            ValueError: If source_type is not supported.
        """
        if source_type not in self.supported_source_types:
            raise ValueError(f"Unsupported source type: {source_type}. Supported: {self.supported_source_types}")

        text = content.decode("utf-8", errors="replace")
        currency = metadata.get("currency", self._default_currency)

        logger.info(
            "extracting_expense_policy",
            source_type=source_type,
            content_length=len(text),
            has_llm=self._llm_callable is not None,
        )

        if self._llm_callable is not None:
            rules = await self._extract_with_llm(text, source_type, metadata, currency)
        else:
            rules = self._extract_with_regex(text, source_type, metadata, currency)

        logger.info("expense_policy_extracted", rule_count=len(rules))
        return rules

    async def _extract_with_llm(
        self,
        text: str,
        source_type: str,
        metadata: dict[str, Any],
        currency: str,
    ) -> list[dict[str, Any]]:
        """Extract rules using LLM-assisted structured extraction.

        Args:
            text: Document text content.
            source_type: Source type for scope derivation.
            metadata: Source metadata.
            currency: Default currency code.

        Returns:
            List of candidate rule dicts.
        """
        assert self._llm_callable is not None

        prompt = _LLM_EXTRACTION_PROMPT.format(content=text[:25000])

        try:
            response = await self._llm_callable(prompt)
            extracted = self._parse_llm_response(response)
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning(
                "llm_extraction_parse_failed",
                error=str(exc),
                falling_back="regex",
            )
            return self._extract_with_regex(text, source_type, metadata, currency)

        return self._format_llm_results(extracted, source_type, metadata, currency)

    def _parse_llm_response(self, response: str) -> list[dict[str, Any]]:
        """Parse the LLM JSON response.

        Args:
            response: Raw LLM response text.

        Returns:
            List of extracted rule objects.

        Raises:
            json.JSONDecodeError: If response is not valid JSON.
            ValueError: If response structure is unexpected.
        """
        # Try to find JSON array in response
        text = response.strip()
        if text.startswith("```"):
            # Strip markdown code fences
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "rules" in parsed:
            return parsed["rules"]
        raise ValueError("Expected a JSON array or object with 'rules' key")

    def _format_llm_results(
        self,
        extracted: list[dict[str, Any]],
        source_type: str,
        metadata: dict[str, Any],
        currency: str,
    ) -> list[dict[str, Any]]:
        """Format LLM-extracted items into standard candidate rule dicts.

        Args:
            extracted: Raw extracted items from LLM.
            source_type: Source type for scope derivation.
            metadata: Source metadata.
            currency: Default currency.

        Returns:
            List of formatted candidate rule dicts.
        """
        rules: list[dict[str, Any]] = []
        source_name = metadata.get("filename", source_type)
        scope = self._derive_scope(source_type)

        for item in extracted:
            statement = item.get("statement", "")
            if not statement:
                continue

            is_prohibited = item.get("is_prohibited", False)
            modality = "MUST_NOT" if is_prohibited else "MUST"
            severity = item.get("severity", "HIGH" if is_prohibited else "MEDIUM")

            tags = ["finance", source_type]
            category = item.get("category")
            if category:
                tags.append(f"category:{category}")
            if item.get("requires_receipt"):
                tags.append("receipt-required")
            if item.get("requires_approval"):
                tags.append("approval-required")

            rule: dict[str, Any] = {
                "statement": statement,
                "modality": modality,
                "severity": severity,
                "scope": scope,
                "tags": tags,
                "applicable_subject_types": ["transaction"],
                "rationale": f"Extracted from {source_name} via LLM analysis.",
                "source_ref": source_name,
            }

            limit = item.get("limit_amount")
            if limit is not None:
                rule["metadata"] = {
                    "limit_amount": limit,
                    "currency": item.get("currency", currency),
                }

            per_diem = item.get("per_diem_rate")
            if per_diem is not None:
                rule["metadata"] = rule.get("metadata", {})
                rule["metadata"]["per_diem_rate"] = per_diem

            rules.append(rule)

        return rules

    def _extract_with_regex(
        self,
        text: str,
        source_type: str,
        metadata: dict[str, Any],
        currency: str,
    ) -> list[dict[str, Any]]:
        """Extract rules using regex-based pattern matching.

        Identifies amounts, prohibited actions, category headers, receipt
        requirements, and per-diem rates from the document text.

        Args:
            text: Document text content.
            source_type: Source type for scope derivation.
            metadata: Source metadata.
            currency: Default currency code.

        Returns:
            List of candidate rule dicts.
        """
        rules: list[dict[str, Any]] = []
        source_name = metadata.get("filename", source_type)
        scope = self._derive_scope(source_type)
        lines = text.splitlines()

        current_category: str | None = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            # Detect category headers
            header_match = _CATEGORY_HEADER_PATTERN.match(stripped)
            if header_match:
                current_category = header_match.group(1).strip()
                continue

            # Detect prohibited items
            if any(kw in stripped.lower() for kw in _PROHIBITED_KEYWORDS):
                rules.append(
                    self._build_rule(
                        statement=stripped,
                        modality="MUST_NOT",
                        severity="HIGH",
                        scope=scope,
                        tags=self._build_tags(source_type, current_category, prohibited=True),
                        source_name=source_name,
                        category=current_category,
                    )
                )
                continue

            # Detect amount-based rules
            amount_matches = _AMOUNT_PATTERN.findall(stripped)
            if amount_matches:
                rules.append(
                    self._build_rule(
                        statement=stripped,
                        modality="MUST",
                        severity="MEDIUM",
                        scope=scope,
                        tags=self._build_tags(source_type, current_category),
                        source_name=source_name,
                        category=current_category,
                        limit_amount=self._parse_first_amount(amount_matches),
                        currency=currency,
                    )
                )
                continue

            # Detect receipt requirements
            if _RECEIPT_PATTERN.search(stripped):
                # Look for an associated amount on this or adjacent lines
                context_text = "\n".join(lines[max(0, i - 1) : i + 2])
                amounts = _AMOUNT_PATTERN.findall(context_text)
                rules.append(
                    self._build_rule(
                        statement=stripped,
                        modality="MUST",
                        severity="MEDIUM",
                        scope=scope,
                        tags=self._build_tags(source_type, current_category, receipt=True),
                        source_name=source_name,
                        category=current_category,
                        limit_amount=self._parse_first_amount(amounts) if amounts else None,
                        currency=currency,
                    )
                )
                continue

            # Detect per-diem rates
            if _PER_DIEM_PATTERN.search(stripped):
                amounts = _AMOUNT_PATTERN.findall(stripped)
                if amounts:
                    rules.append(
                        self._build_rule(
                            statement=stripped,
                            modality="MUST",
                            severity="MEDIUM",
                            scope=scope,
                            tags=self._build_tags(source_type, current_category, per_diem=True),
                            source_name=source_name,
                            category=current_category,
                            per_diem_rate=self._parse_first_amount(amounts),
                            currency=currency,
                        )
                    )

        return rules

    def _build_rule(
        self,
        *,
        statement: str,
        modality: str,
        severity: str,
        scope: list[str],
        tags: list[str],
        source_name: str,
        category: str | None = None,
        limit_amount: int | None = None,
        per_diem_rate: int | None = None,
        currency: str | None = None,
    ) -> dict[str, Any]:
        """Build a candidate rule dict from extracted data.

        Args:
            statement: The rule statement text.
            modality: Rule modality (MUST, MUST_NOT, SHOULD, etc.).
            severity: Rule severity (HIGH, MEDIUM, LOW).
            scope: Rule scope list.
            tags: Rule tags.
            source_name: Source document name for rationale.
            category: Expense category if detected.
            limit_amount: Amount limit if applicable.
            per_diem_rate: Per-diem rate if applicable.
            currency: Currency code.

        Returns:
            Candidate rule dict.
        """
        rule: dict[str, Any] = {
            "statement": statement,
            "modality": modality,
            "severity": severity,
            "scope": scope,
            "tags": tags,
            "applicable_subject_types": ["transaction"],
            "rationale": f"Extracted from {source_name} via pattern matching.",
            "source_ref": source_name,
        }

        rule_metadata: dict[str, Any] = {}
        if category:
            rule_metadata["category"] = category
        if limit_amount is not None:
            rule_metadata["limit_amount"] = limit_amount
        if per_diem_rate is not None:
            rule_metadata["per_diem_rate"] = per_diem_rate
        if currency:
            rule_metadata["currency"] = currency

        if rule_metadata:
            rule["metadata"] = rule_metadata

        return rule

    @staticmethod
    def _derive_scope(source_type: str) -> list[str]:
        """Derive scope from source type.

        Args:
            source_type: The source type string.

        Returns:
            List of scope strings.
        """
        scope_map = {
            "expense_policy": ["finance/expense"],
            "travel_policy": ["finance/expense", "finance/travel"],
            "procurement_policy": ["finance/procurement"],
        }
        return scope_map.get(source_type, ["finance"])

    @staticmethod
    def _build_tags(
        source_type: str,
        category: str | None = None,
        *,
        prohibited: bool = False,
        receipt: bool = False,
        per_diem: bool = False,
    ) -> list[str]:
        """Build tags list for a candidate rule.

        Args:
            source_type: Source type string.
            category: Expense category if detected.
            prohibited: Whether this is a prohibition.
            receipt: Whether this relates to receipt requirements.
            per_diem: Whether this relates to per-diem rates.

        Returns:
            List of tag strings.
        """
        tags = ["finance", source_type]
        if category:
            tags.append(f"category:{category}")
        if prohibited:
            tags.append("prohibited")
        if receipt:
            tags.append("receipt-required")
        if per_diem:
            tags.append("per-diem")
        return tags

    @staticmethod
    def _parse_first_amount(matches: list[str]) -> int | None:
        """Parse the first matched amount string to an integer.

        Args:
            matches: List of regex match group strings.

        Returns:
            Integer amount or None if parsing fails.
        """
        if not matches:
            return None
        try:
            return int(matches[0].replace(",", ""))
        except (ValueError, IndexError):
            return None

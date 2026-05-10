"""Deterministic expense evaluator for finance domain.

Performs rule-based (non-LLM) checks on expense transactions including
amount thresholds, category validation, duplicate detection, receipt
requirements, cumulative spend limits, entertainment limits, and split
transaction detection.

See: CLAUDE.md SS14.4
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

LLMCallable = Callable[[str], Coroutine[Any, Any, str]]

# Default configuration constants
DEFAULT_RECEIPT_THRESHOLD_JPY = 3000
DEFAULT_ENTERTAINMENT_PER_PERSON_LIMIT_JPY = 5000
DEFAULT_DUPLICATE_WINDOW_DAYS = 7
DEFAULT_SPLIT_DETECTION_WINDOW_DAYS = 3
DEFAULT_SPLIT_MIN_TRANSACTIONS = 3
DEFAULT_VIOLATION_WINDOW_DAYS = 30


@dataclass(frozen=True)
class ExpenseLimits:
    """Configuration for expense evaluation thresholds.

    Attributes:
        receipt_threshold: Amount above which receipts are required.
        category_limits: Per-category monthly spending limits.
        prohibited_categories: Categories that are always denied.
        restricted_categories: Categories requiring additional approval.
        entertainment_per_person_limit: Max per-person entertainment spend.
        duplicate_window_days: Days to look back for duplicate detection.
        split_detection_window_days: Days to look back for split detection.
        split_min_transactions: Min transactions to flag as split.
        currency: Currency code for these limits.
    """

    receipt_threshold: int = DEFAULT_RECEIPT_THRESHOLD_JPY
    category_limits: dict[str, int] = field(default_factory=dict)
    prohibited_categories: list[str] = field(default_factory=list)
    restricted_categories: list[str] = field(default_factory=list)
    entertainment_per_person_limit: int = DEFAULT_ENTERTAINMENT_PER_PERSON_LIMIT_JPY
    duplicate_window_days: int = DEFAULT_DUPLICATE_WINDOW_DAYS
    split_detection_window_days: int = DEFAULT_SPLIT_DETECTION_WINDOW_DAYS
    split_min_transactions: int = DEFAULT_SPLIT_MIN_TRANSACTIONS
    currency: str = "JPY"


@dataclass
class Verdict:
    """Internal verdict representation before serialization.

    Attributes:
        rule_id: ID of the evaluated rule.
        verdict: ALLOW, DENY, or NEEDS_REVIEW.
        confidence: Confidence score 0.0 to 1.0.
        reasoning: Explanation of the verdict.
        remediation_kind: Type of remediation suggested.
        remediation_payload: Kind-specific remediation data.
    """

    rule_id: str
    verdict: str
    confidence: float
    reasoning: str
    remediation_kind: str | None = None
    remediation_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to verdict dict.

        Returns:
            Dict with all verdict fields.
        """
        result: dict[str, Any] = {
            "rule_id": self.rule_id,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }
        if self.remediation_kind:
            result["remediation"] = {
                "kind": self.remediation_kind,
                "auto_applicable": False,
                "payload": self.remediation_payload,
            }
        return result


class ExpenseEvaluator:
    """Deterministic expense transaction evaluator.

    Performs rule-based checks without LLM involvement for fast, consistent
    expense validation. Checks include:
    - Amount threshold validation
    - Category validation (prohibited/restricted)
    - Duplicate detection
    - Receipt requirements
    - Monthly cumulative spend per category
    - Entertainment/gift per-person limits
    - Split transaction detection

    Args:
        limits: Configuration for evaluation thresholds.
        transaction_history: Callable that returns recent transactions
            for the same employee, used for duplicate and cumulative checks.
    """

    def __init__(
        self,
        limits: ExpenseLimits | None = None,
        transaction_history: Callable[[str, int], list[dict[str, Any]]] | None = None,
    ) -> None:
        self._limits = limits or ExpenseLimits()
        self._get_history = transaction_history

    @property
    def name(self) -> str:
        """Unique name of this evaluator within its domain."""
        return "expense_evaluator"

    @property
    def domain(self) -> str:
        """Domain identifier."""
        return "finance"

    @property
    def supported_subject_kinds(self) -> list[str]:
        """SubjectKind values this evaluator can handle."""
        return ["transaction"]

    async def evaluate(
        self,
        subject_payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Evaluate an expense transaction against deterministic rules.

        Runs all checks and returns per-rule verdicts. Each check that
        triggers produces a DENY or NEEDS_REVIEW verdict with appropriate
        remediation.

        Args:
            subject_payload: Transaction data with fields like amount,
                category, vendor, date, receipt_attached, attendees, etc.
            rules: List of finance rule dicts (used for rule_id attribution).
            context: Additional context (employee_id, history, limits override).

        Returns:
            List of verdict dicts.
        """
        amount = subject_payload.get("amount", 0)
        currency = subject_payload.get("currency", self._limits.currency)
        category = subject_payload.get("category", "").lower()
        vendor = subject_payload.get("vendor", subject_payload.get("payee", ""))
        date_str = subject_payload.get("date", "")
        receipt_attached = subject_payload.get("receipt_attached", False)
        attendees = subject_payload.get("attendees")
        employee_id = subject_payload.get("employee_id") or context.get("employee_id", "unknown")

        # Allow limits override from context
        limits = self._resolve_limits(context)

        # Get transaction history if available
        history = self._fetch_history(employee_id, context)

        verdicts: list[Verdict] = []

        logger.info(
            "expense_evaluation_start",
            amount=amount,
            currency=currency,
            category=category,
            vendor=vendor,
            employee_id=employee_id,
        )

        # Check 1: Prohibited categories
        verdict = self._check_prohibited_category(category, limits, rules)
        if verdict:
            verdicts.append(verdict)

        # Check 2: Restricted categories
        verdict = self._check_restricted_category(category, limits, rules)
        if verdict:
            verdicts.append(verdict)

        # Check 3: Amount threshold / approval levels
        verdict = self._check_amount_threshold(amount, rules, context)
        if verdict:
            verdicts.append(verdict)

        # Check 4: Receipt requirements
        verdict = self._check_receipt_required(amount, receipt_attached, limits, rules)
        if verdict:
            verdicts.append(verdict)

        # Check 5: Duplicate detection
        verdict = self._check_duplicates(amount, vendor, date_str, history, limits, rules)
        if verdict:
            verdicts.append(verdict)

        # Check 6: Monthly cumulative spend
        verdict = self._check_cumulative_spend(amount, category, history, limits, rules)
        if verdict:
            verdicts.append(verdict)

        # Check 7: Entertainment per-person limit
        verdict = self._check_entertainment_limit(amount, category, attendees, limits, rules)
        if verdict:
            verdicts.append(verdict)

        # Check 8: Split transaction detection
        verdict = self._check_split_transactions(amount, vendor, date_str, history, limits, rules)
        if verdict:
            verdicts.append(verdict)

        logger.info(
            "expense_evaluation_complete",
            verdict_count=len(verdicts),
            deny_count=sum(1 for v in verdicts if v.verdict == "DENY"),
        )

        return [v.to_dict() for v in verdicts]

    def _resolve_limits(self, context: dict[str, Any]) -> ExpenseLimits:
        """Resolve effective limits from context overrides.

        Args:
            context: Evaluation context possibly containing limit overrides.

        Returns:
            ExpenseLimits with any context overrides applied.
        """
        overrides = context.get("expense_limits")
        if not overrides or not isinstance(overrides, dict):
            return self._limits

        return ExpenseLimits(
            receipt_threshold=overrides.get("receipt_threshold", self._limits.receipt_threshold),
            category_limits=overrides.get("category_limits", self._limits.category_limits),
            prohibited_categories=overrides.get("prohibited_categories", self._limits.prohibited_categories),
            restricted_categories=overrides.get("restricted_categories", self._limits.restricted_categories),
            entertainment_per_person_limit=overrides.get(
                "entertainment_per_person_limit",
                self._limits.entertainment_per_person_limit,
            ),
            duplicate_window_days=overrides.get("duplicate_window_days", self._limits.duplicate_window_days),
            split_detection_window_days=overrides.get(
                "split_detection_window_days", self._limits.split_detection_window_days
            ),
            split_min_transactions=overrides.get("split_min_transactions", self._limits.split_min_transactions),
            currency=overrides.get("currency", self._limits.currency),
        )

    def _fetch_history(
        self,
        employee_id: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Fetch transaction history for duplicate/cumulative checks.

        Args:
            employee_id: Employee identifier.
            context: Context possibly containing inline history.

        Returns:
            List of historical transaction dicts.
        """
        # Prefer inline history from context (for testing/self-contained calls)
        inline = context.get("transaction_history")
        if isinstance(inline, list):
            return inline

        # Use injected history provider
        if self._get_history is not None:
            try:
                return self._get_history(employee_id, DEFAULT_VIOLATION_WINDOW_DAYS)
            except (TypeError, ValueError) as exc:
                logger.warning("history_fetch_failed", error=str(exc))

        return []

    def _check_prohibited_category(
        self,
        category: str,
        limits: ExpenseLimits,
        rules: list[dict[str, Any]],
    ) -> Verdict | None:
        """Check if the expense category is prohibited.

        Args:
            category: Expense category (lowercase).
            limits: Active expense limits.
            rules: Rules list for ID attribution.

        Returns:
            Verdict if violation found, None otherwise.
        """
        if category in [c.lower() for c in limits.prohibited_categories]:
            rule_id = self._find_rule_id(rules, "prohibited", category)
            return Verdict(
                rule_id=rule_id,
                verdict="DENY",
                confidence=1.0,
                reasoning=(
                    f"Category '{category}' is prohibited. "
                    f"Expenses in this category are not allowed under any circumstances."
                ),
                remediation_kind="block",
                remediation_payload={
                    "reason": f"Prohibited category: {category}",
                    "field": "category",
                },
            )
        return None

    def _check_restricted_category(
        self,
        category: str,
        limits: ExpenseLimits,
        rules: list[dict[str, Any]],
    ) -> Verdict | None:
        """Check if the expense category requires additional approval.

        Args:
            category: Expense category (lowercase).
            limits: Active expense limits.
            rules: Rules list for ID attribution.

        Returns:
            Verdict if restriction applies, None otherwise.
        """
        if category in [c.lower() for c in limits.restricted_categories]:
            rule_id = self._find_rule_id(rules, "restricted", category)
            return Verdict(
                rule_id=rule_id,
                verdict="NEEDS_REVIEW",
                confidence=0.9,
                reasoning=(
                    f"Category '{category}' is restricted and requires additional approval from a senior manager."
                ),
                remediation_kind="approval_add",
                remediation_payload={
                    "required_approver_role": "senior_manager",
                    "reason": f"Restricted category: {category}",
                },
            )
        return None

    def _check_amount_threshold(
        self,
        amount: int | float,
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> Verdict | None:
        """Check amount against approval threshold rules.

        Matches against rules that have metadata with min_amount/max_amount.

        Args:
            amount: Transaction amount.
            rules: Rules list containing approval thresholds.
            context: Evaluation context.

        Returns:
            Verdict if approval is missing, None otherwise.
        """
        for rule in rules:
            rule_meta = rule.get("metadata", {})
            if not isinstance(rule_meta, dict):
                continue

            min_amt = rule_meta.get("min_amount")
            max_amt = rule_meta.get("max_amount")

            if min_amt is None:
                continue

            if amount >= min_amt and (max_amt is None or amount <= max_amt):
                approval_authority = rule_meta.get("approval_authority", "manager")
                current_approvals = context.get("current_approvals", [])

                if not self._has_required_approval(current_approvals, approval_authority):
                    return Verdict(
                        rule_id=str(rule.get("id", "threshold_rule")),
                        verdict="DENY",
                        confidence=1.0,
                        reasoning=(
                            f"Amount {amount} requires {approval_authority} approval "
                            f"(threshold: {min_amt}+). No matching approval found."
                        ),
                        remediation_kind="approval_add",
                        remediation_payload={
                            "required_approver_role": approval_authority,
                            "amount": amount,
                            "threshold": min_amt,
                        },
                    )
        return None

    def _check_receipt_required(
        self,
        amount: int | float,
        receipt_attached: bool,
        limits: ExpenseLimits,
        rules: list[dict[str, Any]],
    ) -> Verdict | None:
        """Check if receipt is required but missing.

        Args:
            amount: Transaction amount.
            receipt_attached: Whether a receipt was provided.
            limits: Active expense limits.
            rules: Rules list for ID attribution.

        Returns:
            Verdict if receipt is missing, None otherwise.
        """
        if amount > limits.receipt_threshold and not receipt_attached:
            rule_id = self._find_rule_id(rules, "receipt", "documentation")
            return Verdict(
                rule_id=rule_id,
                verdict="DENY",
                confidence=1.0,
                reasoning=(
                    f"Amount {amount} {limits.currency} exceeds receipt threshold "
                    f"of {limits.receipt_threshold} {limits.currency}. "
                    f"Receipt documentation is required."
                ),
                remediation_kind="field_change",
                remediation_payload={
                    "field": "receipt_attached",
                    "required_value": True,
                    "description": "Attach a receipt for this expense.",
                },
            )
        return None

    def _check_duplicates(
        self,
        amount: int | float,
        vendor: str,
        date_str: str,
        history: list[dict[str, Any]],
        limits: ExpenseLimits,
        rules: list[dict[str, Any]],
    ) -> Verdict | None:
        """Detect potential duplicate transactions.

        Flags if same amount + same vendor within the duplicate window.

        Args:
            amount: Transaction amount.
            vendor: Vendor/payee name.
            date_str: Transaction date string.
            history: Historical transactions.
            limits: Active expense limits.
            rules: Rules list for ID attribution.

        Returns:
            Verdict if duplicate suspected, None otherwise.
        """
        if not history or not vendor:
            return None

        tx_date = self._parse_date(date_str)
        if tx_date is None:
            return None

        window_start = tx_date - timedelta(days=limits.duplicate_window_days)

        duplicates = [
            tx
            for tx in history
            if (
                tx.get("amount") == amount
                and self._normalize_vendor(tx.get("vendor", tx.get("payee", ""))) == self._normalize_vendor(vendor)
                and self._is_within_window(tx.get("date", ""), window_start, tx_date)
            )
        ]

        if duplicates:
            rule_id = self._find_rule_id(rules, "duplicate", "")
            return Verdict(
                rule_id=rule_id,
                verdict="NEEDS_REVIEW",
                confidence=0.85,
                reasoning=(
                    f"Potential duplicate: {len(duplicates)} transaction(s) with "
                    f"same amount ({amount}) and vendor ({vendor}) found within "
                    f"{limits.duplicate_window_days} days."
                ),
                remediation_kind="field_change",
                remediation_payload={
                    "field": "duplicate_justification",
                    "required_value": "non-empty string",
                    "description": ("Provide justification that this is not a duplicate submission."),
                    "duplicate_count": len(duplicates),
                },
            )
        return None

    def _check_cumulative_spend(
        self,
        amount: int | float,
        category: str,
        history: list[dict[str, Any]],
        limits: ExpenseLimits,
        rules: list[dict[str, Any]],
    ) -> Verdict | None:
        """Check monthly cumulative spend against category limits.

        Args:
            amount: Current transaction amount.
            category: Expense category.
            history: Historical transactions.
            limits: Active expense limits.
            rules: Rules list for ID attribution.

        Returns:
            Verdict if limit exceeded, None otherwise.
        """
        if not category or category not in limits.category_limits:
            return None

        monthly_limit = limits.category_limits[category]

        # Sum this month's spend in the same category
        monthly_total = sum(
            tx.get("amount", 0)
            for tx in history
            if tx.get("category", "").lower() == category and self._is_same_month(tx.get("date", ""))
        )

        projected = monthly_total + amount
        if projected > monthly_limit:
            rule_id = self._find_rule_id(rules, "budget", category)
            return Verdict(
                rule_id=rule_id,
                verdict="DENY",
                confidence=0.95,
                reasoning=(
                    f"Monthly cumulative spend in '{category}' would reach "
                    f"{projected} {limits.currency} (limit: {monthly_limit} "
                    f"{limits.currency}). Current month total: {monthly_total}, "
                    f"this transaction: {amount}."
                ),
                remediation_kind="approval_add",
                remediation_payload={
                    "required_approver_role": "department_head",
                    "reason": "Monthly category budget exceeded",
                    "category": category,
                    "monthly_total": monthly_total,
                    "projected_total": projected,
                    "monthly_limit": monthly_limit,
                },
            )
        return None

    def _check_entertainment_limit(
        self,
        amount: int | float,
        category: str,
        attendees: Any,
        limits: ExpenseLimits,
        rules: list[dict[str, Any]],
    ) -> Verdict | None:
        """Check entertainment/gift per-person spending limit.

        Args:
            amount: Transaction amount.
            category: Expense category.
            attendees: Number of attendees or attendee list.
            limits: Active expense limits.
            rules: Rules list for ID attribution.

        Returns:
            Verdict if per-person limit exceeded, None otherwise.
        """
        entertainment_categories = {"entertainment", "gift", "dining", "hospitality"}
        if category not in entertainment_categories:
            return None

        if attendees is None:
            # Cannot verify per-person limit without attendee count
            rule_id = self._find_rule_id(rules, "entertainment", "attendees")
            return Verdict(
                rule_id=rule_id,
                verdict="NEEDS_REVIEW",
                confidence=0.7,
                reasoning=(
                    f"Entertainment expense of {amount} {limits.currency} requires "
                    f"attendee count for per-person limit verification."
                ),
                remediation_kind="field_change",
                remediation_payload={
                    "field": "attendees",
                    "required_value": "integer > 0",
                    "description": "Provide the number of attendees.",
                },
            )

        num_attendees = attendees if isinstance(attendees, int) else len(attendees)
        if num_attendees <= 0:
            return None

        per_person = amount / num_attendees
        if per_person > limits.entertainment_per_person_limit:
            rule_id = self._find_rule_id(rules, "entertainment", "per-person")
            return Verdict(
                rule_id=rule_id,
                verdict="DENY",
                confidence=1.0,
                reasoning=(
                    f"Per-person entertainment cost is {per_person:.0f} {limits.currency} "
                    f"({amount} / {num_attendees} attendees), exceeding limit of "
                    f"{limits.entertainment_per_person_limit} {limits.currency}."
                ),
                remediation_kind="field_change",
                remediation_payload={
                    "field": "amount",
                    "max_allowed": limits.entertainment_per_person_limit * num_attendees,
                    "per_person_limit": limits.entertainment_per_person_limit,
                    "description": (
                        f"Reduce amount to at most "
                        f"{limits.entertainment_per_person_limit * num_attendees} "
                        f"{limits.currency} for {num_attendees} attendees."
                    ),
                },
            )
        return None

    def _check_split_transactions(
        self,
        amount: int | float,
        vendor: str,
        date_str: str,
        history: list[dict[str, Any]],
        limits: ExpenseLimits,
        rules: list[dict[str, Any]],
    ) -> Verdict | None:
        """Detect split transactions to avoid approval thresholds.

        Flags when multiple small transactions to the same vendor occur
        within a short window, suggesting intentional splitting.

        Args:
            amount: Current transaction amount.
            vendor: Vendor/payee name.
            date_str: Transaction date string.
            history: Historical transactions.
            limits: Active expense limits.
            rules: Rules list for ID attribution.

        Returns:
            Verdict if split pattern detected, None otherwise.
        """
        if not history or not vendor:
            return None

        tx_date = self._parse_date(date_str)
        if tx_date is None:
            return None

        window_start = tx_date - timedelta(days=limits.split_detection_window_days)
        normalized_vendor = self._normalize_vendor(vendor)

        recent_same_vendor = [
            tx
            for tx in history
            if (
                self._normalize_vendor(tx.get("vendor", tx.get("payee", ""))) == normalized_vendor
                and self._is_within_window(tx.get("date", ""), window_start, tx_date)
            )
        ]

        # Include current transaction in the count
        if len(recent_same_vendor) + 1 >= limits.split_min_transactions:
            total_amount = sum(tx.get("amount", 0) for tx in recent_same_vendor) + amount
            rule_id = self._find_rule_id(rules, "split", "")
            return Verdict(
                rule_id=rule_id,
                verdict="NEEDS_REVIEW",
                confidence=0.75,
                reasoning=(
                    f"Potential split transaction detected: "
                    f"{len(recent_same_vendor) + 1} transactions to '{vendor}' "
                    f"within {limits.split_detection_window_days} days, "
                    f"totaling {total_amount} {limits.currency}. "
                    f"This may be an attempt to avoid approval thresholds."
                ),
                remediation_kind="block",
                remediation_payload={
                    "reason": "Suspected split transaction pattern",
                    "vendor": vendor,
                    "transaction_count": len(recent_same_vendor) + 1,
                    "combined_total": total_amount,
                    "window_days": limits.split_detection_window_days,
                },
            )
        return None

    @staticmethod
    def _find_rule_id(
        rules: list[dict[str, Any]],
        keyword1: str,
        keyword2: str,
    ) -> str:
        """Find the best matching rule ID for a check type.

        Searches rule statements for matching keywords.

        Args:
            rules: Rules list.
            keyword1: Primary keyword to match.
            keyword2: Secondary keyword to match.

        Returns:
            Rule ID string, or a generated check-type ID if no match.
        """
        for rule in rules:
            statement = rule.get("statement", "").lower()
            if keyword1 in statement or keyword2 in statement:
                return str(rule.get("id", "unknown"))
        return f"check_{keyword1}_{keyword2}".rstrip("_")

    @staticmethod
    def _has_required_approval(
        current_approvals: list[dict[str, Any]],
        required_role: str,
    ) -> bool:
        """Check if the required approval role is present.

        Args:
            current_approvals: List of approval dicts with role/status.
            required_role: Required approver role.

        Returns:
            True if a matching approved entry exists.
        """
        normalized = required_role.lower().replace(" ", "_")
        for approval in current_approvals:
            role = approval.get("role", approval.get("approver_role", "")).lower().replace(" ", "_")
            status = approval.get("status", "").lower()
            if normalized in role and status == "approved":
                return True
        return False

    @staticmethod
    def _normalize_vendor(vendor: str) -> str:
        """Normalize vendor name for comparison.

        Args:
            vendor: Raw vendor name.

        Returns:
            Lowercased, stripped vendor name.
        """
        return vendor.lower().strip()

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        """Parse a date string into a datetime object.

        Supports ISO format and common date formats.

        Args:
            date_str: Date string to parse.

        Returns:
            Parsed datetime or None if parsing fails.
        """
        if not date_str:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d/%m/%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str[: len(fmt) + 5], fmt)
            except (ValueError, IndexError):
                continue
        return None

    @staticmethod
    def _is_within_window(
        date_str: str,
        window_start: datetime,
        window_end: datetime,
    ) -> bool:
        """Check if a date string falls within a window.

        Args:
            date_str: Date string to check.
            window_start: Start of window (inclusive).
            window_end: End of window (inclusive).

        Returns:
            True if date is within window.
        """
        parsed = ExpenseEvaluator._parse_date(date_str)
        if parsed is None:
            return False
        # Strip timezone for comparison
        naive_parsed = parsed.replace(tzinfo=None)
        naive_start = window_start.replace(tzinfo=None)
        naive_end = window_end.replace(tzinfo=None)
        return naive_start <= naive_parsed <= naive_end

    @staticmethod
    def _is_same_month(date_str: str) -> bool:
        """Check if a date string is in the current month.

        Args:
            date_str: Date string to check.

        Returns:
            True if date is in the current calendar month.
        """
        parsed = ExpenseEvaluator._parse_date(date_str)
        if parsed is None:
            return False
        now = datetime.now()
        return parsed.year == now.year and parsed.month == now.month

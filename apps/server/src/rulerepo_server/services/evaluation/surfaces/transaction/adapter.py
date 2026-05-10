"""Transaction surface adapter — evaluates financial transactions.

Provides transaction type detection, field validation, threshold
detection, approval chain analysis, and scope resolution for expenses,
purchase orders, attendance records, payroll, and journal entries.

See CLAUDE.md §14.4 for the Transaction Evaluation Path specification.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rulerepo_server.domain.evaluation import Surface
from rulerepo_server.services.evaluation.surfaces.base import (
    EvaluationSubjectPayload,
    SurfaceAdapter,
)

_HINTS_FILE = Path(__file__).parent / "prompts" / "transaction_hints.txt"

# --------------------------------------------------------------------------
# Transaction type → scope mapping
# --------------------------------------------------------------------------

_TRANSACTION_SCOPE_MAP: dict[str, list[str]] = {
    "expense": ["finance/expense"],
    "expense_claim": ["finance/expense"],
    "entertainment": ["finance/expense", "compliance/anti-bribery"],
    "travel": ["finance/expense", "finance/travel"],
    "purchase_order": ["finance/procurement"],
    "procurement": ["finance/procurement"],
    "invoice": ["finance/invoice"],
    "journal_entry": ["finance/journal"],
    "journal": ["finance/journal"],
    "payroll": ["hr/payroll", "finance/payroll"],
    "bonus": ["hr/compensation", "finance/payroll"],
    "attendance": ["hr/attendance"],
    "overtime": ["hr/attendance", "hr/overtime"],
    "leave": ["hr/leave"],
    "reimbursement": ["finance/expense", "finance/reimbursement"],
    "petty_cash": ["finance/petty-cash"],
    "transfer": ["finance/transfer"],
    "donation": ["finance/donation", "compliance/anti-bribery"],
    "gift": ["compliance/anti-bribery", "finance/expense"],
}

# --------------------------------------------------------------------------
# Required fields per transaction type
# --------------------------------------------------------------------------

_REQUIRED_FIELDS: dict[str, list[str]] = {
    "expense": ["amount", "category", "description"],
    "expense_claim": ["amount", "category", "description", "receipt_attached"],
    "entertainment": ["amount", "counterparty", "attendees", "purpose"],
    "travel": ["amount", "destination", "dates", "purpose"],
    "purchase_order": ["amount", "vendor", "items", "delivery_date"],
    "invoice": ["amount", "vendor", "invoice_number", "due_date"],
    "journal_entry": ["debit_account", "credit_account", "amount", "description"],
    "payroll": ["employee_id", "base_amount", "period"],
    "attendance": ["employee_id", "hours_worked", "date"],
    "overtime": ["employee_id", "overtime_hours", "date", "reason"],
    "leave": ["employee_id", "leave_type", "start_date", "end_date"],
}

# --------------------------------------------------------------------------
# Common threshold tiers (configurable, but sensible defaults)
# --------------------------------------------------------------------------

_DEFAULT_THRESHOLDS: dict[str, dict[str, float]] = {
    "expense": {
        "auto_approve_max_jpy": 10000,
        "manager_approve_max_jpy": 100000,
        "director_approve_max_jpy": 500000,
        "executive_required_above_jpy": 500000,
    },
    "entertainment": {
        "per_person_max_jpy": 5000,
        "total_max_jpy": 50000,
        "executive_required_above_jpy": 100000,
    },
    "purchase_order": {
        "auto_approve_max_jpy": 50000,
        "manager_approve_max_jpy": 500000,
        "director_approve_max_jpy": 5000000,
    },
    "donation": {
        "requires_approval_above_jpy": 10000,
        "executive_required_above_jpy": 100000,
    },
    "gift": {
        "max_per_person_jpy": 5000,
        "requires_approval_above_jpy": 3000,
    },
}


def _detect_transaction_type(payload: dict[str, Any]) -> str:
    """Detect transaction type from payload fields."""
    explicit = payload.get("transaction_type", "")
    if explicit:
        return explicit.lower().replace(" ", "_").replace("-", "_")

    # Heuristic detection from payload content
    if "overtime_hours" in payload.get("facts", {}):
        return "overtime"
    if "leave_type" in payload.get("facts", {}):
        return "leave"
    if "hours_worked" in payload.get("facts", {}):
        return "attendance"
    if "vendor" in payload or "invoice_number" in payload.get("facts", {}):
        return "invoice"
    if "debit_account" in payload.get("facts", {}) or "credit_account" in payload.get("facts", {}):
        return "journal_entry"
    if payload.get("amount") and payload.get("category"):
        return "expense"

    return "unknown"


def _validate_fields(transaction_type: str, payload: dict[str, Any], facts: dict[str, Any]) -> list[str]:
    """Check required fields for the transaction type. Returns list of missing fields."""
    required = _REQUIRED_FIELDS.get(transaction_type, [])
    all_fields = {**payload, **facts}
    return [f for f in required if f not in all_fields or all_fields[f] in (None, "", [])]


def _check_thresholds(transaction_type: str, amount: float, currency: str) -> dict[str, Any]:
    """Check amount against default thresholds. Returns threshold context."""
    thresholds = _DEFAULT_THRESHOLDS.get(transaction_type, {})
    if not thresholds or not amount:
        return {}

    # Normalize to JPY for threshold comparison
    amount_jpy = amount
    if currency.upper() != "JPY":
        # Rough conversion for threshold checks (not for display)
        fx_rates = {"USD": 150, "EUR": 165, "GBP": 190, "CNY": 21}
        rate = fx_rates.get(currency.upper(), 150)
        amount_jpy = amount * rate

    result: dict[str, Any] = {"amount_jpy": amount_jpy, "thresholds_checked": []}
    for threshold_name, threshold_value in sorted(thresholds.items(), key=lambda x: x[1]):
        exceeded = amount_jpy > threshold_value
        result["thresholds_checked"].append(
            {
                "name": threshold_name,
                "value": threshold_value,
                "exceeded": exceeded,
            }
        )
        if exceeded:
            result["highest_exceeded"] = threshold_name
            result["highest_exceeded_value"] = threshold_value

    return result


def _extract_approval_chain(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Extract approval chain from payload if present."""
    chain = payload.get("approval_chain") or payload.get("facts", {}).get("approval_chain")
    if isinstance(chain, list):
        return chain
    approver = payload.get("approver") or payload.get("facts", {}).get("approver")
    if approver:
        return [{"role": "approver", "id": approver, "status": "pending"}]
    return []


class TransactionSurfaceAdapter(SurfaceAdapter):
    """Surface adapter for financial and HR transaction evaluation.

    Handles expense claims, invoices, journal entries, purchase orders,
    attendance records, payroll, and other business transactions subject
    to financial and HR rules.
    """

    @property
    def surface(self) -> Surface:
        return Surface.TRANSACTION

    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a business transaction into a uniform subject.

        Expected payload keys:
            - transaction_type: str (e.g., "expense", "purchase_order", "attendance")
            - amount: float — transaction amount (if financial)
            - currency: str — currency code (default "JPY")
            - description: str — transaction description
            - account_code: str — accounting code
            - category: str — expense/transaction category
            - approver: str — approver identifier
            - approval_chain: list[dict] — full approval chain
            - counterparty: str — other party (vendor, client, etc.)
            - employee_id: str — employee submitting/affected
            - facts: dict — additional structured facts

        Returns:
            EvaluationSubjectPayload with transaction-specific fields.
        """
        transaction_type = _detect_transaction_type(payload)
        amount = payload.get("amount", 0)
        currency = payload.get("currency", "JPY")
        description = payload.get("description", "")
        account_code = payload.get("account_code", "")
        category = payload.get("category", "")

        # Build facts with all relevant context
        facts = dict(payload.get("facts", {}))
        facts["transaction_type"] = transaction_type
        if amount:
            facts["amount"] = amount
            facts["currency"] = currency
        if account_code:
            facts["account_code"] = account_code
        if category:
            facts["category"] = category
        if payload.get("counterparty"):
            facts["counterparty"] = payload["counterparty"]
        if payload.get("employee_id"):
            facts["employee_id"] = payload["employee_id"]

        # Field validation
        missing_fields = _validate_fields(transaction_type, payload, facts)
        if missing_fields:
            facts["missing_required_fields"] = missing_fields

        # Threshold analysis
        if amount:
            threshold_info = _check_thresholds(transaction_type, amount, currency)
            if threshold_info:
                facts["threshold_analysis"] = threshold_info

        # Approval chain
        approval_chain = _extract_approval_chain(payload)
        if approval_chain:
            facts["approval_chain"] = approval_chain

        # Build description
        if not description:
            amount_str = f"{currency} {amount:,.0f}" if amount else "no amount"
            description = f"Transaction ({transaction_type}): {amount_str}"
            if category:
                description += f", category: {category}"
            if payload.get("counterparty"):
                description += f", counterparty: {payload['counterparty']}"
        else:
            amount_str = f"{currency} {amount:,.0f}" if amount else ""
            description = f"Transaction ({transaction_type}){': ' + amount_str if amount_str else ''}\n\n{description}"

        # Identifier
        id_parts = [f"transaction:{transaction_type}"]
        if account_code:
            id_parts.append(f"account:{account_code}")
        elif payload.get("employee_id"):
            id_parts.append(f"employee:{payload['employee_id']}")
        identifier = "/".join(id_parts)

        return EvaluationSubjectPayload(
            surface=Surface.TRANSACTION,
            identifier=identifier,
            description=description,
            payload={
                "transaction_type": transaction_type,
                "amount": amount,
                "currency": currency,
                "account_code": account_code,
                "category": category,
                "counterparty": payload.get("counterparty", ""),
                "approval_chain": approval_chain,
                "missing_fields": missing_fields,
            },
            facts=facts,
            locale=payload.get("locale", "ja"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from transaction type, account code, and category.

        Uses a transaction-type → scope mapping equivalent to the code adapter's
        file-path → language scope mapping.
        """
        scopes: set[str] = set()

        transaction_type = _detect_transaction_type(payload)

        # Map transaction type to scopes
        if transaction_type in _TRANSACTION_SCOPE_MAP:
            scopes.update(_TRANSACTION_SCOPE_MAP[transaction_type])

        # Account code → additional scope
        account_code = payload.get("account_code", "")
        if account_code:
            scopes.add(f"finance/account/{account_code}")

        # Category-based scope
        category = payload.get("category", "").lower()
        if "entertainment" in category or "接待" in category:
            scopes.add("compliance/anti-bribery")
        if "gift" in category or "贈答" in category:
            scopes.add("compliance/anti-bribery")

        # Department scope if present
        department = payload.get("department") or payload.get("facts", {}).get("department")
        if department:
            scopes.add(f"department/{department.lower()}")

        return sorted(scopes) if scopes else ["finance/general"]

    def get_prompt_hints(self) -> str:
        """Return transaction-specific prompt hints."""
        if _HINTS_FILE.exists():
            return _HINTS_FILE.read_text()
        return (
            "You are evaluating a business transaction for compliance with "
            "financial policies, expense rules, and regulatory requirements. "
            "Focus on approval authority, amount limits, documentation, and "
            "segregation of duties."
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        fields = ["facts.employee_name", "facts.employee_id"]
        if payload.get("counterparty"):
            fields.append("counterparty")
        return fields

    @property
    def default_audit_retention_days(self) -> int:
        return 3650  # 10 years for financial records

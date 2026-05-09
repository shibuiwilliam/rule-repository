"""Transaction surface adapter — evaluates financial transactions.

Handles journal entries, expense claims, invoices, purchase orders,
and other financial transactions. See CLAUDE.md §14.2.
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


class TransactionSurfaceAdapter(SurfaceAdapter):
    """Surface adapter for financial transaction evaluation.

    Handles expense claims, invoices, journal entries, purchase orders,
    and other business transactions subject to financial rules.
    """

    @property
    def surface(self) -> Surface:
        return Surface.TRANSACTION

    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a financial transaction into a uniform subject.

        Expected payload keys:
            - transaction_type: str (e.g., "expense_claim", "invoice", "journal_entry")
            - amount: float — transaction amount
            - currency: str — currency code (e.g., "USD", "JPY")
            - description: str — transaction description
            - account_code: str — accounting code
            - approver: str — approver identifier
            - facts: dict — additional structured facts

        Returns:
            EvaluationSubjectPayload with transaction-specific fields.
        """
        transaction_type = payload.get("transaction_type", "unknown")
        amount = payload.get("amount", 0)
        currency = payload.get("currency", "USD")
        description = payload.get("description", "")
        account_code = payload.get("account_code", "")
        approver = payload.get("approver", "")

        if not description:
            description = f"Financial transaction ({transaction_type}): {currency} {amount}"
        else:
            description = f"Financial transaction ({transaction_type}): {currency} {amount}\n\n{description}"

        facts = dict(payload.get("facts", {}))
        facts["transaction_type"] = transaction_type
        facts["amount"] = amount
        facts["currency"] = currency
        if account_code:
            facts["account_code"] = account_code
        if approver:
            facts["approver"] = approver

        identifier = f"transaction:{transaction_type}/{account_code or 'no-account'}"

        return EvaluationSubjectPayload(
            surface=Surface.TRANSACTION,
            identifier=identifier,
            description=description,
            payload={
                "transaction_type": transaction_type,
                "amount": amount,
                "currency": currency,
                "account_code": account_code,
                "approver": approver,
            },
            facts=facts,
            locale=payload.get("locale", "en"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from transaction type and account code."""
        scopes: set[str] = set()

        transaction_type = payload.get("transaction_type", "")
        if "expense" in transaction_type:
            scopes.add("finance/expense")
        elif "invoice" in transaction_type:
            scopes.add("finance/invoice")
        elif "journal" in transaction_type:
            scopes.add("finance/journal")
        elif "purchase" in transaction_type or "procurement" in transaction_type:
            scopes.add("finance/procurement")

        account_code = payload.get("account_code", "")
        if account_code:
            scopes.add(f"finance/account/{account_code}")

        return sorted(scopes) if scopes else ["finance/general"]

    def get_prompt_hints(self) -> str:
        """Return transaction-specific prompt hints."""
        if _HINTS_FILE.exists():
            return _HINTS_FILE.read_text()
        return (
            "You are evaluating a financial transaction for compliance with "
            "accounting standards, expense policies, approval thresholds, and "
            "regulatory requirements. Focus on proper authorization, amount "
            "limits, account code validity, and segregation of duties."
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        return ["facts.vendor_name", "facts.employee_name"]

    @property
    def default_audit_retention_days(self) -> int:
        return 3650  # 10 years for financial records

"""Transaction subject — the unit of evaluation for financial transactions.

See CLAUDE.md §14.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class BusinessTransaction:
    """Subject representing a financial or business transaction.

    Attributes:
        transaction_type: Type of transaction (e.g., "expense_claim", "journal_entry", "invoice").
        amount: Transaction amount.
        currency: Currency code (e.g., "JPY", "USD").
        category: Expense or transaction category.
        department: Originating department.
        approver: Person who approved the transaction.
        vendor: Vendor or counterparty name.
        facts: Additional structured facts.
        description: Narrative description.
        timestamp: When the transaction occurred.
        locale: Locale of the transaction context.
    """

    transaction_type: str
    amount: float = 0.0
    currency: str = "JPY"
    category: str = ""
    department: str = ""
    approver: str = ""
    vendor: str = ""
    facts: dict[str, object] = field(default_factory=dict)
    description: str = ""
    timestamp: datetime | None = None
    locale: str = "en"

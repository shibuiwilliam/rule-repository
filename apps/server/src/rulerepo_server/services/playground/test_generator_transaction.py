"""Test case generator for transaction-type subjects.

Produces realistic compliant and non-compliant transaction samples
for rule testing. See CLAUDE.md §14.13.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class TransactionTestGenerator:
    """Generates test cases for transaction-type rules.

    Produces sample transactions (expenses, attendance, purchase orders)
    that are either compliant or non-compliant with a given rule.
    """

    def __init__(self, gemini_client: Any | None = None) -> None:
        self._gemini = gemini_client

    async def generate(
        self,
        rule_statement: str,
        transaction_type: str = "expense",
        count: int = 2,
    ) -> list[dict[str, Any]]:
        """Generate compliant and non-compliant transaction test cases.

        Args:
            rule_statement: The rule to generate test cases for.
            transaction_type: Type of transaction (expense, attendance, etc.).
            count: Number of test cases per verdict.

        Returns:
            List of test case dicts with subject_type, payload, and expected_verdict.
        """
        logger.info(
            "transaction_test_generation",
            transaction_type=transaction_type,
            count=count,
        )

        test_cases: list[dict[str, Any]] = []

        # Generate a compliant case
        test_cases.append(
            {
                "subject_type": "transaction",
                "transaction_type": transaction_type,
                "payload": _sample_transaction(transaction_type, compliant=True),
                "expected_verdict": "ALLOW",
                "notes": "Auto-generated compliant sample",
            }
        )

        # Generate a non-compliant case
        test_cases.append(
            {
                "subject_type": "transaction",
                "transaction_type": transaction_type,
                "payload": _sample_transaction(transaction_type, compliant=False),
                "expected_verdict": "DENY",
                "expected_remediation_kind": "field_change",
                "notes": "Auto-generated non-compliant sample",
            }
        )

        return test_cases


def _sample_transaction(transaction_type: str, compliant: bool) -> dict[str, Any]:
    """Generate a sample transaction payload."""
    match transaction_type:
        case "expense":
            return {
                "amount_jpy": 3000 if compliant else 150000,
                "category": "transportation",
                "receipt_attached": bool(compliant),
                "description": "Taxi to client meeting",
            }
        case "attendance":
            return {
                "employee_id": "E001",
                "hours_worked": 8.0 if compliant else 16.0,
                "overtime_hours": 0.0 if compliant else 8.0,
                "date": "2026-04-01",
            }
        case "purchase_order":
            return {
                "amount_jpy": 50000 if compliant else 5000000,
                "vendor": "Acme Corp",
                "requires_bidding": not compliant,
            }
        case _:
            return {
                "type": transaction_type,
                "compliant": compliant,
            }

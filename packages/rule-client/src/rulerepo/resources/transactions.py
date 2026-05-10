"""Transactions resource — transaction-specific rule operations."""

from __future__ import annotations

from typing import Any

import httpx

from rulerepo.errors import raise_for_status
from rulerepo.models import RuleList, SearchResult


class TransactionsResource:
    """Transaction-specific operations for rule retrieval and evaluation.

    Provides domain-filtered access to rules applicable to business
    transactions (expenses, purchase orders, attendance, payroll).
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def list_rules(
        self,
        *,
        transaction_type: str | None = None,
        department: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> RuleList:
        """List rules applicable to transactions.

        Args:
            transaction_type: Filter by type (expense, purchase_order,
                attendance, payroll, journal_entry).
            department: Department filter (e.g., "finance", "hr").
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Paginated RuleList filtered for transaction-applicable rules.
        """
        type_to_scope: dict[str, str] = {
            "expense": "finance/expense",
            "purchase_order": "finance/procurement",
            "attendance": "hr/attendance",
            "payroll": "hr/payroll",
            "journal_entry": "finance/accounting",
        }
        type_to_dept: dict[str, str] = {
            "expense": "finance",
            "purchase_order": "finance",
            "attendance": "hr",
            "payroll": "hr",
            "journal_entry": "finance",
        }
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if transaction_type:
            params["scope"] = type_to_scope.get(transaction_type, "finance")
        if department:
            params["department"] = department
        elif transaction_type:
            params["department"] = type_to_dept.get(transaction_type, "finance")
        resp = await self._client.get("/api/v1/rules", params=params)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return RuleList.model_validate(resp.json())

    async def search(
        self,
        query: str,
        *,
        transaction_type: str | None = None,
    ) -> SearchResult:
        """Search for transaction-related rules.

        Args:
            query: Search query (e.g., "expense limit", "overtime cap").
            transaction_type: Optional type filter.

        Returns:
            Search results filtered for transaction rules.
        """
        type_to_scope: dict[str, str] = {
            "expense": "finance/expense",
            "purchase_order": "finance/procurement",
            "attendance": "hr/attendance",
            "payroll": "hr/payroll",
            "journal_entry": "finance/accounting",
        }
        body: dict[str, Any] = {
            "query": query,
            "scope": type_to_scope.get(transaction_type, "finance") if transaction_type else "finance",
        }
        resp = await self._client.post("/api/v1/search/hybrid", json=body)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return SearchResult.model_validate(resp.json())

    async def evaluate(
        self,
        payload: dict[str, Any],
        *,
        transaction_type: str = "other",
        actor_role: str | None = None,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate a transaction against applicable rules.

        Args:
            payload: Transaction record (e.g., {"amount_jpy": 30000,
                "category": "entertainment"}).
            transaction_type: Type (expense, purchase_order, attendance,
                payroll, journal_entry, other).
            actor_role: Role of the submitter (e.g., "manager").
            department: Department context.

        Returns:
            Evaluation result with verdict and field-level remediations.
        """
        body: dict[str, Any] = {**payload, "transaction_type": transaction_type}
        if actor_role:
            body["actor_role"] = actor_role
        if department:
            body["department"] = department

        resp = await self._client.post(
            "/api/v1/evaluate/transaction",
            json=body,
        )
        if resp.status_code >= 400:
            return {"verdict": "NEEDS_CONFIRMATION", "error": f"HTTP {resp.status_code}"}
        return resp.json()

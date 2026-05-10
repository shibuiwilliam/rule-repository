"""Contracts resource — contract-specific rule operations."""

from __future__ import annotations

from typing import Any

import httpx

from rulerepo.errors import raise_for_status
from rulerepo.models import RuleList, SearchResult


class ContractsResource:
    """Contract-specific operations for rule retrieval and evaluation.

    Provides domain-filtered access to rules applicable to contract review,
    with convenience methods for common contract operations.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def list_rules(
        self,
        *,
        contract_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> RuleList:
        """List rules applicable to contracts.

        Args:
            contract_type: Filter by contract type (nda, employment, service,
                procurement, license).
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Paginated RuleList filtered for contract-applicable rules.
        """
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "department": "legal",
        }
        if contract_type:
            params["scope"] = f"legal/contract/{contract_type}"
        resp = await self._client.get("/api/v1/rules", params=params)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return RuleList.model_validate(resp.json())

    async def search(
        self,
        query: str,
        *,
        contract_type: str | None = None,
    ) -> SearchResult:
        """Search for contract-related rules.

        Args:
            query: Search query (e.g., "indemnity clause", "liability cap").
            contract_type: Optional contract type filter.

        Returns:
            Search results filtered for contract rules.
        """
        body: dict[str, Any] = {
            "query": query,
            "scope": f"legal/contract/{contract_type}" if contract_type else "legal/contract",
        }
        resp = await self._client.post("/api/v1/search/hybrid", json=body)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return SearchResult.model_validate(resp.json())

    async def evaluate(
        self,
        clause_text: str,
        *,
        clause_type: str = "general",
        parties: list[str] | None = None,
        governing_law: str | None = None,
        language: str = "ja",
    ) -> dict[str, Any]:
        """Evaluate a contract clause against applicable rules.

        Args:
            clause_text: The clause text to evaluate.
            clause_type: Clause category (indemnity, liability, ip,
                non_compete, termination, confidentiality, general).
            parties: Party names involved.
            governing_law: Governing law jurisdiction.
            language: Contract language (default "ja").

        Returns:
            Evaluation result with verdict and clause-level remediations.
        """
        body: dict[str, Any] = {
            "clause_text": clause_text,
            "clause_type": clause_type,
            "language": language,
        }
        if parties:
            body["parties"] = parties
        if governing_law:
            body["governing_law"] = governing_law

        resp = await self._client.post(
            "/api/v1/evaluate/contract",
            json=body,
        )
        if resp.status_code >= 400:
            return {"verdict": "NEEDS_CONFIRMATION", "error": f"HTTP {resp.status_code}"}
        return resp.json()

"""Communications resource — communication-specific rule operations."""

from __future__ import annotations

from typing import Any

import httpx

from rulerepo.errors import raise_for_status
from rulerepo.models import RuleList, SearchResult


class CommunicationsResource:
    """Communication-specific operations for rule retrieval and evaluation.

    Provides domain-filtered access to rules applicable to business
    communications (emails, Slack messages, press releases, social media).
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def list_rules(
        self,
        *,
        channel: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> RuleList:
        """List rules applicable to communications.

        Args:
            channel: Filter by channel (email, slack, social,
                press_release, customer_facing).
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Paginated RuleList filtered for communication-applicable rules.
        """
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if channel:
            params["scope"] = f"communications/{channel}"
        else:
            params["scope"] = "communications"
        resp = await self._client.get("/api/v1/rules", params=params)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return RuleList.model_validate(resp.json())

    async def search(
        self,
        query: str,
        *,
        channel: str | None = None,
    ) -> SearchResult:
        """Search for communication-related rules.

        Args:
            query: Search query (e.g., "PII disclosure", "disclaimer").
            channel: Optional channel filter.

        Returns:
            Search results filtered for communication rules.
        """
        body: dict[str, Any] = {
            "query": query,
            "scope": f"communications/{channel}" if channel else "communications",
        }
        resp = await self._client.post("/api/v1/search/hybrid", json=body)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return SearchResult.model_validate(resp.json())

    async def evaluate(
        self,
        text: str,
        *,
        channel: str = "email",
        audience: str = "external",
        language: str = "ja",
    ) -> dict[str, Any]:
        """Evaluate a communication against applicable rules.

        Args:
            text: The message content to evaluate.
            channel: Channel (email, slack, social, press_release,
                customer_facing, other).
            audience: Target audience (internal, external, regulatory).
            language: Message language (default "ja").

        Returns:
            Evaluation result with verdict and text-level remediations.
        """
        resp = await self._client.post(
            "/api/v1/evaluate/document",
            json={
                "document_type": "other",
                "content": text,
                "channel": channel,
                "audience": audience,
                "language": language,
            },
        )
        if resp.status_code >= 400:
            return {"verdict": "NEEDS_CONFIRMATION", "error": f"HTTP {resp.status_code}"}
        return resp.json()

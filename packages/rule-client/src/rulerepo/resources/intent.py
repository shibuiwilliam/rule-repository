"""Intent resource — natural-language query interface."""

from __future__ import annotations

from typing import Any

import httpx

from rulerepo.errors import raise_for_status
from rulerepo.models import IntentResult


class IntentResource:
    """Provides the Intent API for natural-language queries."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def ask(self, query: str, context: dict[str, Any] | None = None) -> IntentResult:
        """Send a natural-language query to the Intent API.

        Args:
            query: The question or request in natural language.
            context: Optional context for the query.

        Returns:
            IntentResult with classified intent, result data, and explanation.
        """
        body: dict[str, Any] = {"query": query}
        if context:
            body["context"] = context
        resp = await self._client.post("/api/v1/intent", json=body)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return IntentResult.model_validate(resp.json())

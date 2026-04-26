"""RuleClient — the main entry point for the Rule Repository Python SDK."""

from __future__ import annotations

import httpx

from rulerepo.resources.documents import DocumentsResource
from rulerepo.resources.intent import IntentResource
from rulerepo.resources.rules import RulesResource
from rulerepo.resources.search import SearchResource


class RuleClient:
    """Async client for the Rule Repository API.

    Usage::

        from rulerepo import RuleClient

        async with RuleClient("http://localhost:8000") as client:
            rules = await client.rules.list()
            result = await client.search.hybrid("overtime monthly limit")
            intent = await client.intent.ask("What are the rules for refunding orders?")

    Args:
        server_url: Base URL of the Rule Repository server.
        api_key: Optional API key for authentication.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        headers: dict[str, str] = {}
        if api_key:
            headers["X-API-Key"] = api_key

        self._http = httpx.AsyncClient(
            base_url=server_url,
            headers=headers,
            timeout=timeout,
        )

        self.rules = RulesResource(self._http)
        self.search = SearchResource(self._http)
        self.intent = IntentResource(self._http)
        self.documents = DocumentsResource(self._http)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    async def __aenter__(self) -> RuleClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def health(self) -> dict[str, str]:
        """Check server health.

        Returns:
            Health status dict.
        """
        resp = await self._http.get("/healthz")
        return resp.json()

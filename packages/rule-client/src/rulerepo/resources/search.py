"""Search resource — multi-modal search over the rule corpus."""

from __future__ import annotations

from typing import Any

import httpx

from rulerepo.errors import raise_for_status
from rulerepo.models import SearchResult


class SearchResource:
    """Provides search operations via the REST API."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fulltext(self, query: str, **kwargs: Any) -> SearchResult:
        """BM25 full-text search.

        Args:
            query: Search query text.
            **kwargs: Filters and pagination (scope, modality, severity, tags, page, page_size).

        Returns:
            SearchResult with matching rules and scores.
        """
        return await self._search("/api/v1/search/fulltext", query, **kwargs)

    async def vector(self, query: str, **kwargs: Any) -> SearchResult:
        """Semantic similarity search using embeddings.

        Args:
            query: Natural-language query.
            **kwargs: Filters and pagination.

        Returns:
            SearchResult with matching rules and scores.
        """
        return await self._search("/api/v1/search/vector", query, **kwargs)

    async def hybrid(self, query: str, **kwargs: Any) -> SearchResult:
        """Combined BM25 + vector search.

        Args:
            query: Search query.
            **kwargs: Filters and pagination.

        Returns:
            SearchResult with matching rules and scores.
        """
        return await self._search("/api/v1/search/hybrid", query, **kwargs)

    async def category(self, **kwargs: Any) -> SearchResult:
        """Filter-only search by category fields.

        Args:
            **kwargs: Filter criteria (modality, severity, scope, tags, status, page, page_size).

        Returns:
            SearchResult with matching rules.
        """
        resp = await self._client.post("/api/v1/search/category", json=kwargs)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return SearchResult.model_validate(resp.json())

    async def _search(self, endpoint: str, query: str, **kwargs: Any) -> SearchResult:
        body = {"query": query, **kwargs}
        resp = await self._client.post(endpoint, json=body)
        raise_for_status(resp.status_code, resp.json() if resp.status_code >= 400 else {})
        return SearchResult.model_validate(resp.json())

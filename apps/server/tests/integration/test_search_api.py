"""Integration tests for search API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_fulltext_search(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/search/fulltext",
        json={"query": "overtime hours"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["page"] == 1


async def test_hybrid_search(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/search/hybrid",
        json={"query": "code review policy"},
    )
    assert resp.status_code == 200


async def test_vector_search(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/search/vector",
        json={"query": "deployment requirements"},
    )
    assert resp.status_code == 200


async def test_category_search(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/search/category",
        json={"modality": "MUST", "severity": "HIGH"},
    )
    assert resp.status_code == 200


async def test_search_with_filters(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/search/fulltext",
        json={
            "query": "overtime",
            "modality": "MUST_NOT",
            "severity": "HIGH",
            "scope": ["hr"],
        },
    )
    assert resp.status_code == 200


async def test_search_pagination(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/search/fulltext",
        json={"query": "test", "page": 2, "page_size": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 2
    assert body["page_size"] == 5


async def test_search_validation_empty_query(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/search/fulltext",
        json={"query": ""},
    )
    assert resp.status_code == 422

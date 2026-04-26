"""Integration tests for the Intent API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_intent_endpoint(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/intent",
        json={"query": "What are the rules about overtime?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "intent" in body
    assert "result" in body


async def test_intent_with_context(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/intent",
        json={
            "query": "Is this compliant?",
            "context": {"employee_id": "E001", "hours": 50},
        },
    )
    assert resp.status_code == 200


async def test_intent_validation_empty(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/intent",
        json={"query": ""},
    )
    assert resp.status_code == 422

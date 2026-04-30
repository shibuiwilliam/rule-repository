"""Integration tests for the relationships API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_two_rules(client: AsyncClient) -> tuple[str, str]:
    """Helper to create two rules and return their IDs."""
    r1 = await client.post("/api/v1/rules", json={"statement": "Parent rule about overtime"})
    r2 = await client.post("/api/v1/rules", json={"statement": "Child rule refining overtime"})
    return r1.json()["id"], r2.json()["id"]


async def test_create_relationship(client: AsyncClient) -> None:
    id1, id2 = await _create_two_rules(client)

    resp = await client.post(
        "/api/v1/relationships",
        json={
            "source_id": id1,
            "target_id": id2,
            "relationship_type": "REFINES",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_id"] == id1
    assert body["target_id"] == id2
    assert body["relationship_type"] == "REFINES"


async def test_delete_relationship(client: AsyncClient) -> None:
    id1, id2 = await _create_two_rules(client)

    # Create
    await client.post(
        "/api/v1/relationships",
        json={"source_id": id1, "target_id": id2, "relationship_type": "OVERRIDES"},
    )

    # Delete
    resp = await client.request(
        "DELETE",
        "/api/v1/relationships",
        params={
            "source_id": id1,
            "target_id": id2,
            "relationship_type": "OVERRIDES",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

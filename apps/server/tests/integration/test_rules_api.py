"""Integration tests for the rules REST API — full CRUD lifecycle."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_health_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_api_health(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["version"] == "v1"


async def test_create_rule(client: AsyncClient, sample_rule_data: dict[str, Any]) -> None:
    resp = await client.post("/api/v1/rules", json=sample_rule_data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["statement"] == sample_rule_data["statement"]
    assert body["modality"] == "MUST"
    assert body["severity"] == "HIGH"
    assert "id" in body


async def test_create_rule_validation_error(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/rules", json={"statement": ""})
    assert resp.status_code == 422


async def test_get_rule(client: AsyncClient, sample_rule_data: dict[str, Any]) -> None:
    # Create
    create_resp = await client.post("/api/v1/rules", json=sample_rule_data)
    rule_id = create_resp.json()["id"]

    # Get
    resp = await client.get(f"/api/v1/rules/{rule_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == rule_id
    assert resp.json()["statement"] == sample_rule_data["statement"]


async def test_get_rule_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/rules/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


async def test_list_rules_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_list_rules_with_data(
    client: AsyncClient, sample_rule_data_list: list[dict[str, Any]]
) -> None:
    for data in sample_rule_data_list:
        await client.post("/api/v1/rules", json=data)

    resp = await client.get("/api/v1/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == len(sample_rule_data_list)
    assert len(body["items"]) == len(sample_rule_data_list)


async def test_list_rules_pagination(
    client: AsyncClient, sample_rule_data_list: list[dict[str, Any]]
) -> None:
    for data in sample_rule_data_list:
        await client.post("/api/v1/rules", json=data)

    resp = await client.get("/api/v1/rules?page=1&page_size=2")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2


async def test_update_rule(client: AsyncClient, sample_rule_data: dict[str, Any]) -> None:
    create_resp = await client.post("/api/v1/rules", json=sample_rule_data)
    rule_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/rules/{rule_id}",
        json={"severity": "CRITICAL", "revision_note": "Escalated"},
    )
    assert resp.status_code == 200
    assert resp.json()["severity"] == "CRITICAL"


async def test_retire_rule(client: AsyncClient, sample_rule_data: dict[str, Any]) -> None:
    create_resp = await client.post("/api/v1/rules", json=sample_rule_data)
    rule_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/rules/{rule_id}/retire")
    assert resp.status_code == 200
    assert resp.json()["status"] == "RETIRED"


async def test_get_revisions(client: AsyncClient, sample_rule_data: dict[str, Any]) -> None:
    create_resp = await client.post("/api/v1/rules", json=sample_rule_data)
    rule_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/rules/{rule_id}/revisions")
    assert resp.status_code == 200
    revisions = resp.json()
    assert len(revisions) == 1
    assert revisions[0]["revision_number"] == 1
    assert revisions[0]["change_note"] == "Initial creation"


async def test_get_relationships_empty(client: AsyncClient, sample_rule_data: dict[str, Any]) -> None:
    create_resp = await client.post("/api/v1/rules", json=sample_rule_data)
    rule_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/rules/{rule_id}/relationships")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_graph(client: AsyncClient, sample_rule_data: dict[str, Any]) -> None:
    create_resp = await client.post("/api/v1/rules", json=sample_rule_data)
    rule_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/rules/{rule_id}/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert "nodes" in body
    assert "edges" in body


async def test_create_rule_all_modalities(client: AsyncClient) -> None:
    for modality in ["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"]:
        resp = await client.post(
            "/api/v1/rules",
            json={"statement": f"Test rule with {modality}", "modality": modality},
        )
        assert resp.status_code == 201
        assert resp.json()["modality"] == modality

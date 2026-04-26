"""Tests for the Rule Repository Python SDK."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from rulerepo.client import RuleClient
from rulerepo.errors import NotFoundError, ServerError, raise_for_status
from rulerepo.models import Rule, RuleList, SearchResult


class TestRaiseForStatus:
    def test_2xx_no_raise(self) -> None:
        raise_for_status(200, {})
        raise_for_status(201, {})

    def test_404_raises(self) -> None:
        with pytest.raises(NotFoundError):
            raise_for_status(404, {"error": {"message": "not found", "code": "NOT_FOUND"}})

    def test_500_raises(self) -> None:
        with pytest.raises(ServerError):
            raise_for_status(500, {"error": {"message": "server error", "code": ""}})


class TestRuleClient:
    @respx.mock
    async def test_health(self) -> None:
        respx.get("http://test:8000/healthz").mock(
            return_value=Response(200, json={"status": "ok"})
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.health()
            assert result["status"] == "ok"

    @respx.mock
    async def test_rules_list(self) -> None:
        respx.get("http://test:8000/api/v1/rules").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "abc",
                            "statement": "Test",
                            "modality": "MUST",
                            "severity": "HIGH",
                            "status": "DRAFT",
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "page_size": 20,
                },
            )
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.rules.list()
            assert isinstance(result, RuleList)
            assert result.total == 1
            assert result.items[0].statement == "Test"

    @respx.mock
    async def test_rules_create(self) -> None:
        respx.post("http://test:8000/api/v1/rules").mock(
            return_value=Response(
                201,
                json={
                    "id": "new-id",
                    "statement": "New rule",
                    "modality": "MUST",
                    "severity": "MEDIUM",
                    "status": "DRAFT",
                },
            )
        )
        async with RuleClient("http://test:8000") as client:
            rule = await client.rules.create("New rule")
            assert isinstance(rule, Rule)
            assert rule.id == "new-id"

    @respx.mock
    async def test_search_hybrid(self) -> None:
        respx.post("http://test:8000/api/v1/search/hybrid").mock(
            return_value=Response(
                200,
                json={
                    "items": [],
                    "total": 0,
                    "page": 1,
                    "page_size": 20,
                    "query": "overtime",
                },
            )
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.search.hybrid("overtime")
            assert isinstance(result, SearchResult)
            assert result.query == "overtime"

    @respx.mock
    async def test_rules_get_not_found(self) -> None:
        respx.get("http://test:8000/api/v1/rules/missing").mock(
            return_value=Response(
                404,
                json={"error": {"code": "NOT_FOUND", "message": "Rule not found: missing"}},
            )
        )
        async with RuleClient("http://test:8000") as client:
            with pytest.raises(NotFoundError):
                await client.rules.get("missing")

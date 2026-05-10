"""Tests for domain-specific resources (contracts, transactions, communications)."""

from __future__ import annotations

import respx
from httpx import Response

from rulerepo.client import RuleClient
from rulerepo.models import RuleList, SearchResult

_RULE_LIST_RESPONSE = {
    "items": [
        {
            "id": "rule-1",
            "statement": "Test rule",
            "modality": "MUST",
            "severity": "HIGH",
            "status": "APPROVED",
        }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
}

_SEARCH_RESPONSE = {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 20,
    "query": "test",
}

_EVAL_RESPONSE = {
    "overall_verdict": "ALLOW",
    "rules_evaluated": 1,
    "rules_violated": 0,
    "violations": [],
}


# ---------------------------------------------------------------------------
# ContractsResource
# ---------------------------------------------------------------------------


class TestContractsResource:
    @respx.mock
    async def test_list_rules(self) -> None:
        respx.get("http://test:8000/api/v1/rules").mock(
            return_value=Response(200, json=_RULE_LIST_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.contracts.list_rules(contract_type="nda")
            assert isinstance(result, RuleList)
            assert result.total == 1

    @respx.mock
    async def test_list_rules_no_type(self) -> None:
        respx.get("http://test:8000/api/v1/rules").mock(
            return_value=Response(200, json=_RULE_LIST_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.contracts.list_rules()
            assert isinstance(result, RuleList)

    @respx.mock
    async def test_search(self) -> None:
        respx.post("http://test:8000/api/v1/search/hybrid").mock(
            return_value=Response(200, json=_SEARCH_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.contracts.search("indemnity clause")
            assert isinstance(result, SearchResult)

    @respx.mock
    async def test_evaluate(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/contract").mock(
            return_value=Response(200, json=_EVAL_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.contracts.evaluate(
                "The Receiving Party shall protect...",
                clause_type="confidentiality",
                parties=["Acme Corp", "Beta Inc"],
            )
            assert result["overall_verdict"] == "ALLOW"

    @respx.mock
    async def test_evaluate_error(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/contract").mock(
            return_value=Response(500, json={}),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.contracts.evaluate("clause text")
            assert result["verdict"] == "NEEDS_CONFIRMATION"
            assert "error" in result


# ---------------------------------------------------------------------------
# TransactionsResource
# ---------------------------------------------------------------------------


class TestTransactionsResource:
    @respx.mock
    async def test_list_rules_expense(self) -> None:
        respx.get("http://test:8000/api/v1/rules").mock(
            return_value=Response(200, json=_RULE_LIST_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.transactions.list_rules(transaction_type="expense")
            assert isinstance(result, RuleList)

    @respx.mock
    async def test_list_rules_attendance(self) -> None:
        respx.get("http://test:8000/api/v1/rules").mock(
            return_value=Response(200, json=_RULE_LIST_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.transactions.list_rules(
                transaction_type="attendance",
                department="hr",
            )
            assert isinstance(result, RuleList)

    @respx.mock
    async def test_search(self) -> None:
        respx.post("http://test:8000/api/v1/search/hybrid").mock(
            return_value=Response(200, json=_SEARCH_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.transactions.search(
                "expense limit",
                transaction_type="expense",
            )
            assert isinstance(result, SearchResult)

    @respx.mock
    async def test_evaluate(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/transaction").mock(
            return_value=Response(200, json=_EVAL_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.transactions.evaluate(
                {"amount_jpy": 30000, "category": "entertainment"},
                transaction_type="expense",
                actor_role="manager",
            )
            assert result["overall_verdict"] == "ALLOW"

    @respx.mock
    async def test_evaluate_error(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/transaction").mock(
            return_value=Response(500, json={}),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.transactions.evaluate(
                {"amount_jpy": 1000},
                transaction_type="expense",
            )
            assert result["verdict"] == "NEEDS_CONFIRMATION"


# ---------------------------------------------------------------------------
# CommunicationsResource
# ---------------------------------------------------------------------------


class TestCommunicationsResource:
    @respx.mock
    async def test_list_rules(self) -> None:
        respx.get("http://test:8000/api/v1/rules").mock(
            return_value=Response(200, json=_RULE_LIST_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.communications.list_rules(channel="email")
            assert isinstance(result, RuleList)

    @respx.mock
    async def test_list_rules_no_channel(self) -> None:
        respx.get("http://test:8000/api/v1/rules").mock(
            return_value=Response(200, json=_RULE_LIST_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.communications.list_rules()
            assert isinstance(result, RuleList)

    @respx.mock
    async def test_search(self) -> None:
        respx.post("http://test:8000/api/v1/search/hybrid").mock(
            return_value=Response(200, json=_SEARCH_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.communications.search(
                "PII disclosure",
                channel="email",
            )
            assert isinstance(result, SearchResult)

    @respx.mock
    async def test_evaluate(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/document").mock(
            return_value=Response(200, json=_EVAL_RESPONSE),
        )
        async with RuleClient("http://test:8000") as client:
            result = await client.communications.evaluate(
                "Dear Customer, please find attached...",
                channel="email",
                audience="external",
            )
            assert result["overall_verdict"] == "ALLOW"


# ---------------------------------------------------------------------------
# RuleClient resource initialization
# ---------------------------------------------------------------------------


class TestResourceInitialization:
    def test_client_has_contracts(self) -> None:
        from rulerepo.resources.contracts import ContractsResource

        client = RuleClient("http://test:8000")
        assert isinstance(client.contracts, ContractsResource)

    def test_client_has_transactions(self) -> None:
        from rulerepo.resources.transactions import TransactionsResource

        client = RuleClient("http://test:8000")
        assert isinstance(client.transactions, TransactionsResource)

    def test_client_has_communications(self) -> None:
        from rulerepo.resources.communications import CommunicationsResource

        client = RuleClient("http://test:8000")
        assert isinstance(client.communications, CommunicationsResource)

    def test_legacy_resources_preserved(self) -> None:
        from rulerepo.resources.documents import DocumentsResource
        from rulerepo.resources.intent import IntentResource
        from rulerepo.resources.rules import RulesResource
        from rulerepo.resources.search import SearchResource

        client = RuleClient("http://test:8000")
        assert isinstance(client.rules, RulesResource)
        assert isinstance(client.search, SearchResource)
        assert isinstance(client.intent, IntentResource)
        assert isinstance(client.documents, DocumentsResource)

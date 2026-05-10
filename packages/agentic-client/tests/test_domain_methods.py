"""Tests for domain-specific methods on AgenticRuleClient."""

from __future__ import annotations

import respx
from httpx import Response

from rulerepo_agentic.client import AgenticRuleClient

_EVAL_RESPONSE = {
    "overall_verdict": "ALLOW",
    "rules_evaluated": 2,
    "rules_violated": 0,
    "violations": [],
}

_RULES_RESPONSE = [
    {
        "id": "rule-1",
        "statement": "Test rule",
        "modality": "MUST",
        "severity": "HIGH",
    }
]


# ---------------------------------------------------------------------------
# Rule retrieval methods
# ---------------------------------------------------------------------------


class TestGetApplicableRulesForSurface:
    @respx.mock
    async def test_basic_call(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/applicable-rules").mock(
            return_value=Response(200, json=_RULES_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.get_applicable_rules_for_surface(
                "contract",
                scope="legal/contract",
                department="legal",
            )
            assert len(result) == 1
            assert result[0]["id"] == "rule-1"

    @respx.mock
    async def test_error_returns_empty(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/applicable-rules").mock(
            return_value=Response(500, json={}),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.get_applicable_rules_for_surface("contract")
            assert result == []


class TestGetRulesForContract:
    @respx.mock
    async def test_nda(self) -> None:
        route = respx.post("http://test:8000/api/v1/evaluate/applicable-rules").mock(
            return_value=Response(200, json=_RULES_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.get_rules_for_contract(
                contract_type="nda",
                parties=["Acme", "Beta"],
            )
            assert len(result) == 1
            # Verify the request was made with correct params
            body = route.calls[0].request.content
            assert b"contract" in body
            assert b"legal" in body

    @respx.mock
    async def test_default_type(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/applicable-rules").mock(
            return_value=Response(200, json=_RULES_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.get_rules_for_contract()
            assert len(result) == 1


class TestGetRulesForTransaction:
    @respx.mock
    async def test_expense(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/applicable-rules").mock(
            return_value=Response(200, json=_RULES_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.get_rules_for_transaction(
                transaction_type="expense",
                amount=30000,
            )
            assert len(result) == 1

    @respx.mock
    async def test_attendance(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/applicable-rules").mock(
            return_value=Response(200, json=_RULES_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.get_rules_for_transaction(
                transaction_type="attendance",
            )
            assert len(result) == 1


class TestGetRulesForCommunication:
    @respx.mock
    async def test_email(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/applicable-rules").mock(
            return_value=Response(200, json=_RULES_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.get_rules_for_communication(
                channel="email",
                audience="external",
            )
            assert len(result) == 1


# ---------------------------------------------------------------------------
# Evaluation convenience methods
# ---------------------------------------------------------------------------


class TestEvaluateContract:
    @respx.mock
    async def test_basic(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate").mock(
            return_value=Response(200, json=_EVAL_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.evaluate_contract(
                "The Receiving Party shall protect...",
                contract_type="nda",
            )
            assert result["overall_verdict"] == "ALLOW"

    @respx.mock
    async def test_error(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate").mock(
            return_value=Response(500, json={}),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.evaluate_contract("clause text")
            assert result["verdict"] == "NEEDS_CONFIRMATION"


class TestEvaluateTransaction:
    @respx.mock
    async def test_expense(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate").mock(
            return_value=Response(200, json=_EVAL_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.evaluate_transaction(
                {"amount_jpy": 30000, "category": "entertainment"},
                transaction_type="expense",
            )
            assert result["overall_verdict"] == "ALLOW"


class TestEvaluateCommunication:
    @respx.mock
    async def test_email(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate").mock(
            return_value=Response(200, json=_EVAL_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.evaluate_communication(
                "Dear Customer, please find attached...",
                channel="email",
                audience="external",
            )
            assert result["overall_verdict"] == "ALLOW"


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    @respx.mock
    async def test_legacy_evaluate_still_works(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate").mock(
            return_value=Response(200, json=_EVAL_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.evaluate(
                {"key": "value"},
                intent="test",
                diff="--- a/f.py\n+++ b/f.py",
            )
            assert result["overall_verdict"] == "ALLOW"

    @respx.mock
    async def test_legacy_get_applicable_rules_still_works(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate/applicable-rules").mock(
            return_value=Response(200, json=_RULES_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.get_applicable_rules(["src/main.py"])
            assert len(result) == 1

    @respx.mock
    async def test_legacy_evaluate_subject_still_works(self) -> None:
        respx.post("http://test:8000/api/v1/evaluate").mock(
            return_value=Response(200, json=_EVAL_RESPONSE),
        )
        async with AgenticRuleClient("http://test:8000") as client:
            result = await client.evaluate_subject(
                "hr_event",
                {"hours": 50},
            )
            assert result["overall_verdict"] == "ALLOW"

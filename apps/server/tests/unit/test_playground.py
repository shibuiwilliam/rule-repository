"""Unit tests for Playground service and Snapshot serializer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rulerepo_server.domain.evaluation import Verdict
from rulerepo_server.services.playground.service import PlaygroundService
from rulerepo_server.services.snapshots.serializer import (
    deserialize_snapshot,
    serialize_rules,
)


# ---------------------------------------------------------------------------
# Helpers — Gemini mock
# ---------------------------------------------------------------------------


def _make_gemini_mock(verdict: str = "ALLOW", confidence: float = 0.92) -> MagicMock:
    """Return a mock object that mimics ``genai.Client``.

    The mock supports ``client.models.generate_content(...)`` returning
    a response whose ``.text`` is a JSON verdict string.
    """
    response_payload = json.dumps(
        {
            "verdict": verdict,
            "confidence": confidence,
            "reasoning": "Mock reasoning for test.",
            "issue_description": "",
            "fix_suggestion": None,
            "locations": [],
        }
    )

    response = MagicMock()
    response.text = response_payload

    client = MagicMock()
    client.models.generate_content.return_value = response
    return client


# ---------------------------------------------------------------------------
# PlaygroundService
# ---------------------------------------------------------------------------


class TestPlaygroundEvaluateSandboxReturnsVerdict:
    """When Gemini is available, evaluate_sandbox returns a verdict."""

    async def test_evaluate_sandbox_returns_verdict(self) -> None:
        gemini = _make_gemini_mock(verdict="DENY", confidence=0.85)
        session = AsyncMock()

        svc = PlaygroundService(session=session, gemini=gemini)

        result = await svc.evaluate_sandbox(
            rule_statement="All functions MUST have docstrings.",
            rule_modality="MUST",
            rule_severity="MEDIUM",
            sample_code="def foo():\n    pass",
        )

        assert result["verdict"] == "DENY"
        assert result["confidence"] == pytest.approx(0.85)
        assert "reasoning" in result
        assert isinstance(result["locations"], list)


class TestPlaygroundEvaluateSandboxNoGemini:
    """When no Gemini client is provided, verdict is NEEDS_CONFIRMATION."""

    async def test_evaluate_sandbox_no_gemini_returns_needs_confirmation(self) -> None:
        session = AsyncMock()

        svc = PlaygroundService(session=session, gemini=None)

        result = await svc.evaluate_sandbox(
            rule_statement="Imports MUST be sorted.",
            rule_modality="MUST",
            rule_severity="LOW",
            sample_code="import os\nimport sys",
        )

        assert result["verdict"] == Verdict.NEEDS_CONFIRMATION.value
        assert result["confidence"] == 0.0
        assert "LLM unavailable" in result["reasoning"]


class TestPlaygroundEvaluateSandboxNoAuditLog:
    """Sandbox evaluation must NOT persist anything to an audit log."""

    async def test_evaluate_sandbox_no_audit_log(self) -> None:
        gemini = _make_gemini_mock()
        session = AsyncMock()

        svc = PlaygroundService(session=session, gemini=gemini)

        await svc.evaluate_sandbox(
            rule_statement="No print statements.",
            rule_modality="MUST",
            rule_severity="LOW",
            sample_facts={"narrative": "Code uses logging instead of print."},
        )

        # The service should never call session.add / session.flush / session.commit
        # for sandbox evaluations — those are fire-and-forget.
        session.add.assert_not_called()
        session.flush.assert_not_awaited()
        session.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------


class TestSerializeDeserializeRoundTrip:
    """Serializing rule dicts and deserializing should yield the same data."""

    def test_serialize_deserialize_round_trip(self) -> None:
        rules = [
            {
                "id": "r-001",
                "statement": "All APIs MUST use TLS.",
                "modality": "MUST",
                "severity": "CRITICAL",
                "status": "APPROVED",
                "scope": ["api", "security"],
                "tags": ["tls", "https"],
                "rationale": "Security baseline.",
            },
            {
                "id": "r-002",
                "statement": "Logging SHOULD use structured format.",
                "modality": "SHOULD",
                "severity": "MEDIUM",
                "status": "EFFECTIVE",
                "scope": ["backend"],
                "tags": ["logging"],
                "rationale": "Observability.",
            },
        ]

        snapshot = serialize_rules(rules)
        restored = deserialize_snapshot(snapshot)

        assert len(restored) == 2

        by_id = {r["id"]: r for r in restored}

        for original in rules:
            restored_rule = by_id[original["id"]]
            assert restored_rule["statement"] == original["statement"]
            assert restored_rule["modality"] == original["modality"]
            assert restored_rule["severity"] == original["severity"]
            assert restored_rule["status"] == original["status"]
            assert restored_rule["scope"] == original["scope"]
            assert restored_rule["tags"] == original["tags"]
            assert restored_rule["rationale"] == original["rationale"]


class TestSerializeEmptyList:
    """Serializing an empty list produces an empty dict."""

    def test_serialize_empty_list(self) -> None:
        snapshot = serialize_rules([])
        assert snapshot == {}


class TestDeserializeEmptySnapshot:
    """Deserializing an empty dict produces an empty list."""

    def test_deserialize_empty_snapshot(self) -> None:
        rules = deserialize_snapshot({})
        assert rules == []

"""Unit tests for the Counterexample Generator (Tier 2.4)."""

from __future__ import annotations

import pytest

from rulerepo_server.services.playground.counterexample_generator import generate_counterexamples

# ---------------------------------------------------------------------------
# Heuristic generation
# ---------------------------------------------------------------------------


class TestHeuristicGeneration:
    """Tests for heuristic (no-LLM) counterexample generation."""

    async def test_basic_must_rule(self) -> None:
        rule = {
            "id": "rule-001",
            "statement": "All functions MUST have docstrings.",
            "modality": "MUST",
            "severity": "MEDIUM",
        }
        result = await generate_counterexamples(rule)

        assert "compliant" in result
        assert "violating" in result
        assert "All functions MUST have docstrings." in result["compliant"]
        assert "All functions MUST have docstrings." in result["violating"]

    async def test_must_not_rule(self) -> None:
        rule = {
            "id": "rule-002",
            "statement": "Code MUST NOT contain print statements.",
            "modality": "MUST_NOT",
            "severity": "HIGH",
        }
        result = await generate_counterexamples(rule)

        assert "avoids the prohibited action" in result["compliant"]
        assert "performs the explicitly prohibited action" in result["violating"]

    async def test_should_rule(self) -> None:
        rule = {
            "id": "rule-003",
            "statement": "Imports SHOULD be sorted alphabetically.",
            "modality": "SHOULD",
            "severity": "LOW",
        }
        result = await generate_counterexamples(rule)

        assert "follows the recommended practice" in result["compliant"]
        assert "neglects the recommended practice" in result["violating"]


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------


class TestOutputStructure:
    """Tests for the output dict structure."""

    async def test_has_required_keys(self) -> None:
        rule = {
            "id": "rule-010",
            "statement": "APIs MUST use TLS.",
            "modality": "MUST",
            "severity": "CRITICAL",
        }
        result = await generate_counterexamples(rule)

        assert "compliant" in result
        assert "violating" in result
        assert "rule_id" in result

    async def test_rule_id_is_string(self) -> None:
        rule = {
            "id": "rule-010",
            "statement": "APIs MUST use TLS.",
            "modality": "MUST",
            "severity": "CRITICAL",
        }
        result = await generate_counterexamples(rule)

        assert isinstance(result["rule_id"], str)
        assert result["rule_id"] == "rule-010"

    async def test_compliant_and_violating_are_strings(self) -> None:
        rule = {
            "id": "rule-010",
            "statement": "APIs MUST use TLS.",
            "modality": "MUST",
            "severity": "CRITICAL",
        }
        result = await generate_counterexamples(rule)

        assert isinstance(result["compliant"], str)
        assert isinstance(result["violating"], str)

    async def test_missing_id_defaults_to_empty(self) -> None:
        rule = {
            "statement": "Test rule.",
            "modality": "MUST",
            "severity": "LOW",
        }
        result = await generate_counterexamples(rule)

        assert result["rule_id"] == ""


# ---------------------------------------------------------------------------
# Different modalities
# ---------------------------------------------------------------------------


class TestDifferentModalities:
    """Tests that each modality produces appropriate framing."""

    @pytest.mark.parametrize(
        ("modality", "compliant_fragment", "violating_fragment"),
        [
            ("MUST", "correctly performs the required action", "fails to perform the required action"),
            ("MUST_NOT", "correctly avoids the prohibited action", "performs the explicitly prohibited action"),
            ("SHOULD", "follows the recommended practice", "neglects the recommended practice"),
            (
                "MAY",
                "optionally follows the permitted practice",
                "incorrectly assumes the optional practice is required",
            ),
            ("INFO", "acknowledges the informational guidance", "ignores the informational guidance"),
        ],
    )
    async def test_modality_framing(
        self,
        modality: str,
        compliant_fragment: str,
        violating_fragment: str,
    ) -> None:
        rule = {
            "id": f"rule-{modality.lower()}",
            "statement": "Test statement.",
            "modality": modality,
            "severity": "MEDIUM",
        }
        result = await generate_counterexamples(rule)

        assert compliant_fragment in result["compliant"]
        assert violating_fragment in result["violating"]

    async def test_unknown_modality_defaults_to_must(self) -> None:
        rule = {
            "id": "rule-unknown",
            "statement": "Unknown modality rule.",
            "modality": "UNKNOWN",
            "severity": "LOW",
        }
        result = await generate_counterexamples(rule)

        # Falls back to MUST framing.
        assert "correctly performs the required action" in result["compliant"]
        assert "fails to perform the required action" in result["violating"]

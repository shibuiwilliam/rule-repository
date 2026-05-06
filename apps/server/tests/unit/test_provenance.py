"""Unit tests for the Provenance lineage resolver (Tier 2.5)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from rulerepo_server.services.provenance.lineage_resolver import resolve_lineage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_mock(rules: dict[str, dict[str, Any]]) -> AsyncMock:
    """Create a mock AsyncSession that returns rules from a dict.

    Args:
        rules: Mapping of rule_id -> {"statement": ..., "rationale": ...}.
    """
    session = AsyncMock()

    async def _execute(query: Any, params: dict[str, Any]) -> Any:
        rule_id = params.get("id", "")
        result = MagicMock()
        mapping_result = MagicMock()

        if rule_id in rules:
            row = {
                "id": rule_id,
                "statement": rules[rule_id].get("statement", ""),
                "rationale": rules[rule_id].get("rationale", ""),
            }
            # Make .get() work on the row.
            row_mock = MagicMock()
            row_mock.__getitem__ = lambda self, key: row[key]
            row_mock.get = lambda key, default="": row.get(key, default)
            mapping_result.first.return_value = row_mock
        else:
            mapping_result.first.return_value = None

        result.mappings.return_value = mapping_result
        return result

    session.execute = AsyncMock(side_effect=_execute)
    return session


def _make_graph_repo_mock(
    neighbors: dict[str, list[dict[str, Any]]],
) -> AsyncMock:
    """Create a mock graph repo that returns neighbors per rule.

    Args:
        neighbors: Mapping of rule_id -> list of neighbor dicts.
    """
    repo = AsyncMock()

    async def _get_neighbors(
        rule_id: UUID,
        *,
        rel_types: list[str] | None = None,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        return neighbors.get(str(rule_id), [])

    repo.get_neighbors = AsyncMock(side_effect=_get_neighbors)
    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResolveLineageBasic:
    """Basic lineage resolution tests."""

    async def test_single_rule_no_derivations(self) -> None:
        session = _make_session_mock(
            {"00000000-0000-0000-0000-000000000001": {"statement": "All APIs must use TLS.", "rationale": "Security."}}
        )
        graph_repo = _make_graph_repo_mock({"00000000-0000-0000-0000-000000000001": []})

        result = await resolve_lineage("00000000-0000-0000-0000-000000000001", session, graph_repo)

        assert result["rule_id"] == "00000000-0000-0000-0000-000000000001"
        assert result["statement"] == "All APIs must use TLS."
        assert result["rationale"] == "Security."
        assert result["derived_from"] == []

    async def test_rule_not_found(self) -> None:
        session = _make_session_mock({})
        graph_repo = _make_graph_repo_mock({})

        result = await resolve_lineage("00000000-0000-0000-0000-000000000999", session, graph_repo)

        assert result["rule_id"] == "00000000-0000-0000-0000-000000000999"
        assert result["error"] == "Rule not found"

    async def test_one_level_derivation(self) -> None:
        session = _make_session_mock(
            {
                "00000000-0000-0000-0000-000000000001": {"statement": "Use HTTPS.", "rationale": "Security."},
                "00000000-0000-0000-0000-000000000002": {
                    "statement": "All traffic must be encrypted.",
                    "rationale": "Regulation.",
                },
            }
        )
        graph_repo = _make_graph_repo_mock(
            {
                "00000000-0000-0000-0000-000000000001": [
                    {"target_id": "00000000-0000-0000-0000-000000000002", "rel_type": "DERIVES_FROM"}
                ]
            }
        )

        result = await resolve_lineage("00000000-0000-0000-0000-000000000001", session, graph_repo)

        assert result["rule_id"] == "00000000-0000-0000-0000-000000000001"
        assert len(result["derived_from"]) == 1
        assert result["derived_from"][0]["rule_id"] == "00000000-0000-0000-0000-000000000002"
        assert result["derived_from"][0]["statement"] == "All traffic must be encrypted."


class TestResolveLineageDepthLimiting:
    """Tests for depth-limiting behavior."""

    async def test_depth_clamped_to_max(self) -> None:
        session = _make_session_mock({"00000000-0000-0000-0000-000000000001": {"statement": "Test.", "rationale": ""}})
        graph_repo = _make_graph_repo_mock({"00000000-0000-0000-0000-000000000001": []})

        # Requesting depth > MAX should not error.
        result = await resolve_lineage("00000000-0000-0000-0000-000000000001", session, graph_repo, depth=100)

        assert result["rule_id"] == "00000000-0000-0000-0000-000000000001"
        assert result["derived_from"] == []

    async def test_depth_zero_returns_just_root(self) -> None:
        session = _make_session_mock(
            {
                "00000000-0000-0000-0000-000000000001": {"statement": "Root.", "rationale": ""},
                "00000000-0000-0000-0000-000000000002": {"statement": "Parent.", "rationale": ""},
            }
        )
        graph_repo = _make_graph_repo_mock(
            {
                "00000000-0000-0000-0000-000000000001": [
                    {"target_id": "00000000-0000-0000-0000-000000000002", "rel_type": "DERIVES_FROM"}
                ]
            }
        )

        # depth=1 is the minimum allowed by the API, but the resolver
        # still respects depth=0 internally.
        result = await resolve_lineage("00000000-0000-0000-0000-000000000001", session, graph_repo, depth=0)

        # With depth 0, it fetches the root but does not walk further.
        # The root still appears because we always fetch it from DB.
        assert result["rule_id"] == "00000000-0000-0000-0000-000000000001"


class TestResolveLineageGracefulDegradation:
    """Tests for graceful degradation when Neo4j is unavailable."""

    async def test_no_graph_repo(self) -> None:
        session = _make_session_mock(
            {"00000000-0000-0000-0000-000000000001": {"statement": "Use TLS.", "rationale": "Security."}}
        )

        result = await resolve_lineage("00000000-0000-0000-0000-000000000001", session, graph_repo=None)

        assert result["rule_id"] == "00000000-0000-0000-0000-000000000001"
        assert result["statement"] == "Use TLS."
        assert result["derived_from"] == []

    async def test_graph_repo_raises(self) -> None:
        session = _make_session_mock(
            {"00000000-0000-0000-0000-000000000001": {"statement": "Use TLS.", "rationale": "Security."}}
        )
        graph_repo = AsyncMock()
        graph_repo.get_neighbors = AsyncMock(side_effect=ConnectionError("Neo4j unavailable"))

        result = await resolve_lineage("00000000-0000-0000-0000-000000000001", session, graph_repo)

        assert result["rule_id"] == "00000000-0000-0000-0000-000000000001"
        assert result["derived_from"] == []

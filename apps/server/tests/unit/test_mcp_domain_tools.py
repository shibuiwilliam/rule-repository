"""Tests for domain-specific MCP tool registration.

Verifies that the new cross-organizational MCP tools are registered
and have proper signatures.
"""

from __future__ import annotations

import inspect

from mcp.server.fastmcp import FastMCP

from rulerepo_server.mcp.tools import register_tools


def _get_registered_tools() -> dict[str, dict]:
    """Register tools on a FastMCP instance and return tool metadata."""
    mcp = FastMCP("test")
    register_tools(mcp)
    # FastMCP stores tools in _tool_manager._tools dict
    tools = {}
    for name, tool in mcp._tool_manager._tools.items():
        tools[name] = {
            "name": name,
            "fn": tool.fn,
        }
    return tools


class TestDomainToolRegistration:
    """Verify that domain-specific tools are registered."""

    def test_get_rules_for_contract_review_registered(self) -> None:
        tools = _get_registered_tools()
        assert "get_rules_for_contract_review" in tools

    def test_get_rules_for_transaction_registered(self) -> None:
        tools = _get_registered_tools()
        assert "get_rules_for_transaction" in tools

    def test_get_rules_for_communication_registered(self) -> None:
        tools = _get_registered_tools()
        assert "get_rules_for_communication" in tools

    def test_evaluate_contract_registered(self) -> None:
        tools = _get_registered_tools()
        assert "evaluate_contract" in tools

    def test_evaluate_transaction_registered(self) -> None:
        tools = _get_registered_tools()
        assert "evaluate_transaction" in tools

    def test_evaluate_communication_registered(self) -> None:
        tools = _get_registered_tools()
        assert "evaluate_communication" in tools


class TestDomainToolSignatures:
    """Verify tool parameter signatures match spec."""

    def test_contract_review_params(self) -> None:
        tools = _get_registered_tools()
        sig = inspect.signature(tools["get_rules_for_contract_review"]["fn"])
        params = set(sig.parameters.keys())
        assert "contract_type" in params
        assert "parties" in params
        assert "governing_law" in params
        assert "language" in params

    def test_transaction_params(self) -> None:
        tools = _get_registered_tools()
        sig = inspect.signature(tools["get_rules_for_transaction"]["fn"])
        params = set(sig.parameters.keys())
        assert "transaction_type" in params
        assert "amount" in params
        assert "department" in params
        assert "actor_role" in params

    def test_communication_params(self) -> None:
        tools = _get_registered_tools()
        sig = inspect.signature(tools["get_rules_for_communication"]["fn"])
        params = set(sig.parameters.keys())
        assert "channel" in params
        assert "audience" in params
        assert "content_type" in params

    def test_evaluate_contract_params(self) -> None:
        tools = _get_registered_tools()
        sig = inspect.signature(tools["evaluate_contract"]["fn"])
        params = set(sig.parameters.keys())
        assert "contract_text" in params
        assert "contract_type" in params
        assert "language" in params
        assert "focus_areas" in params

    def test_evaluate_transaction_params(self) -> None:
        tools = _get_registered_tools()
        sig = inspect.signature(tools["evaluate_transaction"]["fn"])
        params = set(sig.parameters.keys())
        assert "transaction_payload" in params
        assert "transaction_type" in params
        assert "actor_role" in params
        assert "department" in params

    def test_evaluate_communication_params(self) -> None:
        tools = _get_registered_tools()
        sig = inspect.signature(tools["evaluate_communication"]["fn"])
        params = set(sig.parameters.keys())
        assert "text" in params
        assert "channel" in params
        assert "audience" in params
        assert "language" in params


class TestLegacyToolsPreserved:
    """Verify existing tools are not removed."""

    def test_search_rules_preserved(self) -> None:
        tools = _get_registered_tools()
        assert "search_rules" in tools

    def test_get_rules_for_context_preserved(self) -> None:
        tools = _get_registered_tools()
        assert "get_rules_for_context" in tools

    def test_evaluate_compliance_preserved(self) -> None:
        tools = _get_registered_tools()
        assert "evaluate_compliance" in tools

    def test_evaluate_subject_preserved(self) -> None:
        tools = _get_registered_tools()
        assert "evaluate_subject" in tools

    def test_discover_rules_preserved(self) -> None:
        tools = _get_registered_tools()
        assert "discover_rules" in tools


class TestDiscoverRulesDescription:
    """Verify discover_rules description was updated."""

    def test_description_is_domain_neutral(self) -> None:
        tools = _get_registered_tools()
        fn = tools["discover_rules"]["fn"]
        docstring = fn.__doc__ or ""
        # Should mention organizational artifacts, not just codebase
        assert "organizational artifacts" in docstring.lower() or "artifacts" in docstring.lower()

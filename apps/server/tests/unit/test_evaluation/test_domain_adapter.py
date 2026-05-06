"""Tests for the EvaluationDomainAdapter Protocol and CodeAdapter."""

from __future__ import annotations

import pytest

from rulerepo_server.services.evaluation.adapters.base import EvaluationDomainAdapter
from rulerepo_server.services.evaluation.adapters.code import CodeAdapter
from rulerepo_server.services.evaluation.adapters.registry import ADAPTERS, get_adapter


class TestEvaluationDomainAdapterProtocol:
    def test_code_adapter_implements_protocol(self) -> None:
        adapter = CodeAdapter()
        assert isinstance(adapter, EvaluationDomainAdapter)

    def test_code_adapter_domain(self) -> None:
        adapter = CodeAdapter()
        assert adapter.domain == "code"


class TestCodeAdapter:
    async def test_parse_with_diff(self) -> None:
        adapter = CodeAdapter()
        payload = {
            "diff": "diff --git a/foo.py b/foo.py\n--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new",
        }
        ctx = await adapter.parse(payload)
        assert ctx["file_paths"] == ["foo.py"]
        assert "python" in ctx["languages"]

    async def test_parse_with_facts(self) -> None:
        adapter = CodeAdapter()
        payload = {"facts": {"action": "deploy", "env": "staging"}, "intent": "deploy to staging"}
        ctx = await adapter.parse(payload)
        assert ctx["intent"] == "deploy to staging"
        assert ctx["facts"]["action"] == "deploy"

    def test_resolve_scopes_from_files(self) -> None:
        adapter = CodeAdapter()
        payload = {"files": [{"path": "src/app.py"}, {"path": "src/index.ts"}]}
        scopes = adapter.resolve_scopes(payload)
        assert "engineering/python" in scopes
        assert "engineering/typescript" in scopes

    def test_resolve_scopes_from_diff(self) -> None:
        adapter = CodeAdapter()
        payload = {
            "diff": "diff --git a/main.go b/main.go\n--- a/main.go\n+++ b/main.go\n@@ -1 +1 @@\n-old\n+new",
        }
        scopes = adapter.resolve_scopes(payload)
        assert "engineering/go" in scopes

    def test_resolve_scopes_explicit(self) -> None:
        adapter = CodeAdapter()
        payload = {"scope": "engineering/custom"}
        scopes = adapter.resolve_scopes(payload)
        assert "engineering/custom" in scopes

    def test_get_prompt_fragments(self) -> None:
        adapter = CodeAdapter()
        fragments = adapter.get_prompt_fragments()
        assert "domain_intro" in fragments
        assert "context_format" in fragments
        assert "code change" in fragments["domain_intro"]


class TestAdapterRegistry:
    def test_get_code_adapter(self) -> None:
        adapter = get_adapter("code")
        assert adapter.domain == "code"

    def test_get_unknown_adapter_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown evaluation domain"):
            get_adapter("unknown_domain")

    def test_all_domains_registered(self) -> None:
        assert "code" in ADAPTERS
        assert "business_event" in ADAPTERS
        assert "document_diff" in ADAPTERS
        assert "documentation" in ADAPTERS

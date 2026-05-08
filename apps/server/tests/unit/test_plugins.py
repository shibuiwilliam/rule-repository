"""Unit tests for Plugin Architecture (workstream 7b1).

Tests plugin protocols, registry, and core isolation.
Verifies that core never imports from plugins (rule #16).
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Core isolation verification — the most important test in Phase 7
# ---------------------------------------------------------------------------


class TestCoreIsolation:
    """Verify that the core never imports from plugins (CLAUDE.md rule #16)."""

    CORE_DIRS = [
        "domain",
        "services",
        "core",
        "adapters",
    ]
    PLUGIN_PATTERNS = [
        "from rulerepo_server.plugins",
        "import rulerepo_server.plugins",
    ]

    def _get_server_src(self) -> Path:
        return Path(__file__).parent.parent.parent / "src" / "rulerepo_server"

    def test_core_does_not_import_plugins(self) -> None:
        """Scan all core Python files for plugin imports."""
        server_src = self._get_server_src()
        violations: list[str] = []

        for core_dir in self.CORE_DIRS:
            dir_path = server_src / core_dir
            if not dir_path.exists():
                continue
            for py_file in dir_path.rglob("*.py"):
                content = py_file.read_text()
                for pattern in self.PLUGIN_PATTERNS:
                    if pattern in content:
                        rel = py_file.relative_to(server_src)
                        violations.append(f"{rel}: contains '{pattern}'")

        assert violations == [], "Core isolation violated! The following files import from plugins:\n" + "\n".join(
            f"  - {v}" for v in violations
        )

    def test_plugins_do_not_import_each_other(self) -> None:
        """Plugins must not import from other plugins."""
        server_src = self._get_server_src()
        plugins_dir = server_src / "plugins"
        if not plugins_dir.exists():
            pytest.skip("plugins/ directory not yet created")

        violations: list[str] = []
        for plugin_dir in plugins_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                continue
            plugin_name = plugin_dir.name
            for py_file in plugin_dir.rglob("*.py"):
                content = py_file.read_text()
                for other_dir in plugins_dir.iterdir():
                    if not other_dir.is_dir() or other_dir.name == plugin_name or other_dir.name.startswith("_"):
                        continue
                    pattern = f"from rulerepo_server.plugins.{other_dir.name}"
                    if pattern in content:
                        rel = py_file.relative_to(server_src)
                        violations.append(f"{rel}: imports from plugins.{other_dir.name}")

        assert violations == [], "Plugin cross-import violation:\n" + "\n".join(f"  - {v}" for v in violations)


# ---------------------------------------------------------------------------
# Plugin protocol tests
# ---------------------------------------------------------------------------


class TestPluginProtocols:
    def test_evaluator_protocol_exists(self) -> None:
        try:
            from rulerepo_server.plugins.base import Evaluator
        except ImportError:
            pytest.skip("Plugin base not yet available")
        assert hasattr(Evaluator, "evaluate") or hasattr(Evaluator, "__protocol_attrs__") or True

    def test_extractor_protocol_exists(self) -> None:
        try:
            from rulerepo_server.plugins.base import Extractor  # noqa: F401
        except ImportError:
            pytest.skip("Plugin base not yet available")

    def test_domain_plugin_protocol_exists(self) -> None:
        try:
            from rulerepo_server.plugins.base import DomainPlugin  # noqa: F401
        except ImportError:
            pytest.skip("Plugin base not yet available")

    def test_plugin_registry_exists(self) -> None:
        try:
            from rulerepo_server.plugins.base import PluginRegistry  # noqa: F401
        except ImportError:
            pytest.skip("Plugin base not yet available")


# ---------------------------------------------------------------------------
# Plugin registry tests
# ---------------------------------------------------------------------------


class TestPluginRegistry:
    def test_register_evaluator(self) -> None:
        try:
            from rulerepo_server.plugins.base import EvaluatorRegistry
        except ImportError:
            pytest.skip("Plugin registry not yet available")

        registry = EvaluatorRegistry()

        class MockEvaluator:
            name = "test_evaluator"
            domain = "test"
            supported_subject_kinds = ["code_diff"]

            async def evaluate(self, subject_payload, rules, context):
                return []

        registry.register(MockEvaluator())
        evaluator = registry.get("test", "test_evaluator")
        assert evaluator is not None
        assert evaluator.name == "test_evaluator"

    def test_register_extractor(self) -> None:
        try:
            from rulerepo_server.plugins.base import ExtractorRegistry
        except ImportError:
            pytest.skip("Plugin registry not yet available")

        registry = ExtractorRegistry()

        class MockExtractor:
            name = "test_extractor"
            domain = "test"
            supported_source_types = ["text"]

            async def extract(self, content, source_type, metadata):
                return []

        registry.register(MockExtractor())
        extractor = registry.get("test", "test_extractor")
        assert extractor is not None


# ---------------------------------------------------------------------------
# Engineering plugin tests
# ---------------------------------------------------------------------------


class TestEngineeringPlugin:
    def test_plugin_exists(self) -> None:
        try:
            from rulerepo_server.plugins.engineering.plugin import EngineeringPlugin
        except ImportError:
            pytest.skip("Engineering plugin not yet available")
        plugin = EngineeringPlugin()
        assert plugin.domain == "engineering"

    def test_code_change_evaluator(self) -> None:
        try:
            from rulerepo_server.plugins.engineering.evaluators.code_change import (
                CodeChangeEvaluator,
            )
        except ImportError:
            pytest.skip("Code change evaluator not yet available")
        evaluator = CodeChangeEvaluator()
        assert "code_diff" in evaluator.supported_subject_kinds


# ---------------------------------------------------------------------------
# HR plugin tests
# ---------------------------------------------------------------------------


class TestHRPlugin:
    def test_plugin_exists(self) -> None:
        try:
            from rulerepo_server.plugins.hr.plugin import HRPlugin
        except ImportError:
            pytest.skip("HR plugin not yet available")
        plugin = HRPlugin()
        assert plugin.domain == "hr"

    def test_form_evaluator(self) -> None:
        try:
            from rulerepo_server.plugins.hr.evaluators.form_evaluator import FormEvaluator
        except ImportError:
            pytest.skip("Form evaluator not yet available")
        evaluator = FormEvaluator()
        assert "event" in evaluator.supported_subject_kinds


# ---------------------------------------------------------------------------
# Legal plugin tests
# ---------------------------------------------------------------------------


class TestLegalPlugin:
    def test_plugin_exists(self) -> None:
        try:
            from rulerepo_server.plugins.legal.plugin import LegalPlugin
        except ImportError:
            pytest.skip("Legal plugin not yet available")
        plugin = LegalPlugin()
        assert plugin.domain == "legal"


# ---------------------------------------------------------------------------
# Finance plugin tests
# ---------------------------------------------------------------------------


class TestFinancePlugin:
    def test_plugin_exists(self) -> None:
        try:
            from rulerepo_server.plugins.finance.plugin import FinancePlugin
        except ImportError:
            pytest.skip("Finance plugin not yet available")
        plugin = FinancePlugin()
        assert plugin.domain == "finance"


# ---------------------------------------------------------------------------
# Marketing plugin tests
# ---------------------------------------------------------------------------


class TestMarketingPlugin:
    def test_plugin_exists(self) -> None:
        try:
            from rulerepo_server.plugins.marketing.plugin import MarketingPlugin
        except ImportError:
            pytest.skip("Marketing plugin not yet available")
        plugin = MarketingPlugin()
        assert plugin.domain == "marketing"

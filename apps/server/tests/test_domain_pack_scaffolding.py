"""Tests for the Domain Pack scaffolding under packages/domain-packs/.

Validates the _core manifest and registry modules, and the engineering pack.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add packages/domain-packs/_core to the import path so we can test it
# without requiring a full package install.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CORE_DIR = _REPO_ROOT / "packages" / "domain-packs" / "_core"
if str(_CORE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR.parent))


from _core.manifest import PackManifest
from _core.registry import (
    AnalyzerEntry,
    DomainPackRegistry,
    PromptEntry,
    TemplateEntry,
    get_pack_registry,
)

ENGINEERING_PACK_YAML = _REPO_ROOT / "packages" / "domain-packs" / "engineering" / "pack.yaml"


# ---------------------------------------------------------------------------
# PackManifest tests
# ---------------------------------------------------------------------------


class TestPackManifest:
    def test_from_yaml_loads_engineering_pack(self):
        manifest = PackManifest.from_yaml(ENGINEERING_PACK_YAML)
        assert manifest.domain == "engineering"
        assert manifest.name == "Software Engineering"
        assert manifest.version == "0.1.0"
        assert manifest.default_modality == "SHOULD"
        assert "code_change" in manifest.preferred_evaluator_subject_kinds
        assert "python_source" in manifest.subject_types
        assert manifest.pack_dir == ENGINEERING_PACK_YAML.parent

    def test_from_yaml_metadata_extensions(self):
        manifest = PackManifest.from_yaml(ENGINEERING_PACK_YAML)
        assert "language" in manifest.metadata_extensions
        assert manifest.metadata_extensions["language"]["type"] == "string"

    def test_from_yaml_description(self):
        manifest = PackManifest.from_yaml(ENGINEERING_PACK_YAML)
        assert "software engineering" in manifest.description.lower()

    def test_from_yaml_missing_file_raises(self, tmp_path):
        import pytest

        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            PackManifest.from_yaml(missing)

    def test_from_yaml_missing_required_field(self, tmp_path):
        import pytest

        bad_yaml = tmp_path / "pack.yaml"
        bad_yaml.write_text("version: '1.0'\n")
        with pytest.raises(KeyError):
            PackManifest.from_yaml(bad_yaml)


# ---------------------------------------------------------------------------
# DomainPackRegistry tests
# ---------------------------------------------------------------------------


class TestDomainPackRegistry:
    def test_register_and_get_prompt(self, tmp_path):
        registry = DomainPackRegistry()
        prompt_file = tmp_path / "eval.txt"
        prompt_file.write_text("test prompt")

        entry = PromptEntry(domain="engineering", purpose="evaluate", template_path=prompt_file)
        registry.register_prompt(entry)

        result = registry.get_prompt("engineering", "evaluate")
        assert result is not None
        assert result.load() == "test prompt"

    def test_get_prompt_returns_none_for_missing(self):
        registry = DomainPackRegistry()
        assert registry.get_prompt("nonexistent", "evaluate") is None

    def test_register_and_get_analyzer(self):
        registry = DomainPackRegistry()
        entry = AnalyzerEntry(domain="legal", name="contract_parser")
        registry.register_analyzer(entry)

        result = registry.get_analyzer("legal", "contract_parser")
        assert result is not None
        assert result.name == "contract_parser"

    def test_get_analyzer_returns_none_for_missing(self):
        registry = DomainPackRegistry()
        assert registry.get_analyzer("nonexistent", "foo") is None

    def test_register_template(self, tmp_path):
        registry = DomainPackRegistry()
        tpl_file = tmp_path / "template.yaml"
        tpl_file.write_text("rules: []")

        entry = TemplateEntry(domain="hr", name="attendance", template_path=tpl_file, rule_count=10)
        registry.register_template(entry)

        assert ("hr", "attendance") in registry.templates
        assert registry.templates[("hr", "attendance")].rule_count == 10

    def test_register_metadata_schema(self):
        registry = DomainPackRegistry()
        schema = {"jurisdiction": {"type": "string", "required": True}}
        registry.register_metadata_schema("legal", schema)

        assert registry.metadata_schemas["legal"] == schema

    def test_list_domains(self, tmp_path):
        registry = DomainPackRegistry()
        prompt_file = tmp_path / "p.txt"
        prompt_file.write_text("")

        registry.register_prompt(PromptEntry(domain="engineering", purpose="eval", template_path=prompt_file))
        registry.register_analyzer(AnalyzerEntry(domain="legal", name="x"))
        registry.register_template(TemplateEntry(domain="hr", name="y", template_path=prompt_file))
        registry.register_metadata_schema("finance", {})

        domains = registry.list_domains()
        assert domains == ["engineering", "finance", "hr", "legal"]

    def test_list_domains_empty(self):
        registry = DomainPackRegistry()
        assert registry.list_domains() == []

    def test_prompt_overwrites_on_same_key(self, tmp_path):
        registry = DomainPackRegistry()
        f1 = tmp_path / "a.txt"
        f1.write_text("first")
        f2 = tmp_path / "b.txt"
        f2.write_text("second")

        registry.register_prompt(PromptEntry(domain="d", purpose="p", template_path=f1))
        registry.register_prompt(PromptEntry(domain="d", purpose="p", template_path=f2))

        assert registry.get_prompt("d", "p").load() == "second"


# ---------------------------------------------------------------------------
# Singleton test
# ---------------------------------------------------------------------------


class TestGetPackRegistry:
    def test_returns_singleton(self):
        r1 = get_pack_registry()
        r2 = get_pack_registry()
        assert r1 is r2

    def test_singleton_is_domain_pack_registry(self):
        r = get_pack_registry()
        assert isinstance(r, DomainPackRegistry)

"""Tests for the DomainPackLoader and pack structure validation.

Verifies that:
- All 9 domain packs are discovered and loadable
- Each pack has the required directory structure
- Pack manifests parse correctly with all fields
- Querying by surface and persona works
- Prompt file discovery works
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rulerepo_server.services.domain_packs.loader import (
    DOMAIN_PACKS_DIR,
    DomainPackLoader,
    PackManifest,
)

# All expected pack names
ALL_PACK_NAMES = {
    "code",
    "communication",
    "contract",
    "expense",
    "hr_attendance",
    "legal",
    "sales",
    "it_security",
    "governance",
}


class TestDomainPackLoader:
    """Test the loader discovers and registers packs correctly."""

    def test_discover_finds_all_packs(self) -> None:
        loader = DomainPackLoader()
        packs = loader.discover()
        names = {p.name for p in packs}
        assert ALL_PACK_NAMES.issubset(names), f"Missing packs: {ALL_PACK_NAMES - names}"

    def test_load_enabled_loads_all_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ENABLED_PACKS", raising=False)
        loader = DomainPackLoader()
        loaded = loader.load_enabled()
        names = {p.name for p in loaded}
        assert ALL_PACK_NAMES.issubset(names)

    def test_load_enabled_respects_filter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENABLED_PACKS", "code,expense")
        loader = DomainPackLoader()
        loaded = loader.load_enabled()
        names = {p.name for p in loaded}
        assert names == {"code", "expense"}

    def test_get_pack_returns_loaded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ENABLED_PACKS", raising=False)
        loader = DomainPackLoader()
        loader.load_enabled()
        pack = DomainPackLoader.get_pack("expense")
        assert pack is not None
        assert pack.name == "expense"

    def test_get_pack_returns_none_for_unknown(self) -> None:
        assert DomainPackLoader.get_pack("nonexistent_pack_xyz") is None

    def test_get_packs_for_surface(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ENABLED_PACKS", raising=False)
        loader = DomainPackLoader()
        loader.load_enabled()
        transaction_packs = DomainPackLoader.get_packs_for_surface("transaction")
        names = {p.name for p in transaction_packs}
        assert "expense" in names
        assert "sales" in names

    def test_get_packs_for_persona(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ENABLED_PACKS", raising=False)
        loader = DomainPackLoader()
        loader.load_enabled()
        legal_packs = DomainPackLoader.get_packs_for_persona("legal")
        names = {p.name for p in legal_packs}
        assert "contract" in names
        assert "legal" in names

    def test_get_prompt_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ENABLED_PACKS", raising=False)
        loader = DomainPackLoader()
        loader.load_enabled()
        prompts = DomainPackLoader.get_prompt_files("expense")
        assert len(prompts) >= 1
        assert all(p.suffix == ".txt" for p in prompts)


class TestPackManifest:
    """Test PackManifest construction and properties."""

    def test_from_dict(self) -> None:
        data = {
            "name": "test_pack",
            "version": "1.0.0",
            "display_name": "Test Pack",
            "description": "A test pack",
            "surfaces": ["code", "document"],
            "persona": "engineering",
            "metadata_schema": {"custom_field": "string"},
        }
        manifest = PackManifest.from_dict(data, Path("/tmp/test"))
        assert manifest.name == "test_pack"
        assert manifest.version == "1.0.0"
        assert manifest.surfaces == ["code", "document"]
        assert manifest.persona == "engineering"
        assert manifest.metadata_schema == {"custom_field": "string"}
        assert manifest.rules_dir == Path("/tmp/test/rules")
        assert manifest.prompts_dir == Path("/tmp/test/prompts")
        assert manifest.analyzers_dir == Path("/tmp/test/analyzers")
        assert manifest.samples_dir == Path("/tmp/test/samples")

    def test_from_dict_defaults(self) -> None:
        data = {"name": "minimal", "version": "0.1.0", "description": "Minimal"}
        manifest = PackManifest.from_dict(data, Path("/tmp/min"))
        assert manifest.display_name == "minimal"
        assert manifest.persona == "admin"
        assert manifest.surfaces == []
        assert manifest.metadata_schema == {}

    def test_has_prompts_false_for_nonexistent(self) -> None:
        manifest = PackManifest.from_dict(
            {"name": "fake", "version": "0.1.0", "description": ""},
            Path("/nonexistent"),
        )
        assert manifest.has_prompts is False

    def test_has_analyzers_false_for_init_only(self) -> None:
        """Analyzers dir with only __init__.py should report False."""
        # Use the code pack which has analyzers/ with only __init__.py
        pack_dir = DOMAIN_PACKS_DIR / "code"
        if not pack_dir.exists():
            pytest.skip("code pack not available")
        manifest = PackManifest.from_dict(
            {"name": "code", "version": "0.1.0", "description": ""},
            pack_dir,
        )
        # Should be False because analyzers/ only has __init__.py, no actual analyzers
        assert manifest.has_analyzers is False


class TestAllPacksStructure:
    """Verify every domain pack has the required directory structure."""

    @pytest.fixture(params=sorted(ALL_PACK_NAMES))
    def pack_dir(self, request: pytest.FixtureRequest) -> Path:
        pack = DOMAIN_PACKS_DIR / request.param
        if not pack.exists():
            pytest.skip(f"Pack {request.param} not found at {pack}")
        return pack

    def test_pack_yaml_exists(self, pack_dir: Path) -> None:
        assert (pack_dir / "pack.yaml").is_file()

    def test_pack_yaml_valid(self, pack_dir: Path) -> None:
        data = yaml.safe_load((pack_dir / "pack.yaml").read_text())
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "surfaces" in data
        assert isinstance(data["surfaces"], list)

    def test_rules_directory_exists(self, pack_dir: Path) -> None:
        rules_dir = pack_dir / "rules"
        assert rules_dir.is_dir(), f"Missing rules/ in {pack_dir.name}"
        yaml_files = list(rules_dir.glob("*.yaml"))
        assert len(yaml_files) >= 1, f"Pack {pack_dir.name} must contain at least one rules file"

    def test_prompts_directory_exists(self, pack_dir: Path) -> None:
        prompts_dir = pack_dir / "prompts"
        assert prompts_dir.is_dir(), f"Missing prompts/ in {pack_dir.name}"
        prompt_files = list(prompts_dir.glob("*.txt"))
        assert len(prompt_files) >= 1, f"Pack {pack_dir.name} must contain at least one prompt"

    def test_samples_directory_exists(self, pack_dir: Path) -> None:
        samples_dir = pack_dir / "samples"
        assert samples_dir.is_dir(), f"Missing samples/ in {pack_dir.name}"
        sample_files = list(samples_dir.iterdir())
        assert len(sample_files) >= 1, f"Pack {pack_dir.name} must contain at least one sample"

    def test_analyzers_directory_exists(self, pack_dir: Path) -> None:
        analyzers_dir = pack_dir / "analyzers"
        assert analyzers_dir.is_dir(), f"Missing analyzers/ in {pack_dir.name}"

    def test_init_py_exists(self, pack_dir: Path) -> None:
        assert (pack_dir / "__init__.py").is_file()

    def test_rules_have_required_fields(self, pack_dir: Path) -> None:
        """Every rule must have statement, modality, and severity."""
        rules_dir = pack_dir / "rules"
        required = {"statement", "modality", "severity"}
        for f in rules_dir.glob("*.yaml"):
            data = yaml.safe_load(f.read_text())
            if not data or "rules" not in data:
                continue
            for i, rule in enumerate(data["rules"]):
                missing = required - set(rule.keys())
                assert not missing, f"{pack_dir.name}/{f.name} rule #{i}: missing fields {missing}"

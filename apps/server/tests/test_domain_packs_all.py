"""Tests for all Domain Pack manifests (engineering + legal, hr, finance, sales, communication).

Validates that every pack.yaml can be loaded, has the required fields, and that
domains are unique across all packs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add packages/domain-packs/_core to the import path so we can test it
# without requiring a full package install.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CORE_DIR = _REPO_ROOT / "packages" / "domain-packs" / "_core"
if str(_CORE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR.parent))

from _core.manifest import PackManifest

ALL_DOMAINS = ["engineering", "legal", "hr", "finance", "sales", "communication"]
PACKS_DIR = _REPO_ROOT / "packages" / "domain-packs"


def _pack_yaml(domain: str) -> Path:
    return PACKS_DIR / domain / "pack.yaml"


# ---------------------------------------------------------------------------
# Loading tests — every pack.yaml must parse successfully
# ---------------------------------------------------------------------------


class TestAllPacksLoadable:
    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_pack_yaml_exists(self, domain: str) -> None:
        path = _pack_yaml(domain)
        assert path.exists(), f"pack.yaml missing for domain '{domain}'"

    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_pack_yaml_loads(self, domain: str) -> None:
        manifest = PackManifest.from_yaml(_pack_yaml(domain))
        assert manifest is not None


# ---------------------------------------------------------------------------
# Required fields tests
# ---------------------------------------------------------------------------


class TestRequiredFields:
    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_domain_matches_directory(self, domain: str) -> None:
        manifest = PackManifest.from_yaml(_pack_yaml(domain))
        assert manifest.domain == domain

    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_name_is_nonempty(self, domain: str) -> None:
        manifest = PackManifest.from_yaml(_pack_yaml(domain))
        assert manifest.name, f"name must not be empty for domain '{domain}'"

    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_version_is_set(self, domain: str) -> None:
        manifest = PackManifest.from_yaml(_pack_yaml(domain))
        assert manifest.version, f"version must not be empty for domain '{domain}'"

    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_description_is_nonempty(self, domain: str) -> None:
        manifest = PackManifest.from_yaml(_pack_yaml(domain))
        assert manifest.description, f"description must not be empty for domain '{domain}'"

    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_subject_types_is_nonempty(self, domain: str) -> None:
        manifest = PackManifest.from_yaml(_pack_yaml(domain))
        assert len(manifest.subject_types) > 0, f"subject_types must not be empty for domain '{domain}'"

    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_default_modality_is_valid(self, domain: str) -> None:
        manifest = PackManifest.from_yaml(_pack_yaml(domain))
        valid_modalities = {"MUST", "MUST_NOT", "SHOULD", "SHOULD_NOT", "MAY"}
        assert manifest.default_modality in valid_modalities, (
            f"default_modality '{manifest.default_modality}' not in {valid_modalities}"
        )

    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_preferred_evaluator_subject_kinds_is_nonempty(self, domain: str) -> None:
        manifest = PackManifest.from_yaml(_pack_yaml(domain))
        assert len(manifest.preferred_evaluator_subject_kinds) > 0, (
            f"preferred_evaluator_subject_kinds must not be empty for domain '{domain}'"
        )

    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_pack_dir_points_to_correct_directory(self, domain: str) -> None:
        manifest = PackManifest.from_yaml(_pack_yaml(domain))
        assert manifest.pack_dir == PACKS_DIR / domain


# ---------------------------------------------------------------------------
# Uniqueness tests
# ---------------------------------------------------------------------------


class TestDomainUniqueness:
    def test_all_domains_are_unique(self) -> None:
        domains: list[str] = []
        for domain in ALL_DOMAINS:
            manifest = PackManifest.from_yaml(_pack_yaml(domain))
            domains.append(manifest.domain)

        assert len(domains) == len(set(domains)), f"Duplicate domains found: {domains}"

    def test_all_names_are_unique(self) -> None:
        names: list[str] = []
        for domain in ALL_DOMAINS:
            manifest = PackManifest.from_yaml(_pack_yaml(domain))
            names.append(manifest.name)

        assert len(names) == len(set(names)), f"Duplicate pack names found: {names}"


# ---------------------------------------------------------------------------
# Structure tests — verify expected files exist in each pack
# ---------------------------------------------------------------------------


class TestPackStructure:
    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_init_py_exists(self, domain: str) -> None:
        init_file = PACKS_DIR / domain / "__init__.py"
        assert init_file.exists(), f"__init__.py missing for domain '{domain}'"

    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_analyzers_init_exists(self, domain: str) -> None:
        init_file = PACKS_DIR / domain / "analyzers" / "__init__.py"
        assert init_file.exists(), f"analyzers/__init__.py missing for domain '{domain}'"

    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_templates_dir_exists(self, domain: str) -> None:
        templates_dir = PACKS_DIR / domain / "templates"
        assert templates_dir.is_dir(), f"templates/ directory missing for domain '{domain}'"

    @pytest.mark.parametrize("domain", ALL_DOMAINS)
    def test_prompts_dir_exists(self, domain: str) -> None:
        prompts_dir = PACKS_DIR / domain / "prompts"
        assert prompts_dir.is_dir(), f"prompts/ directory missing for domain '{domain}'"

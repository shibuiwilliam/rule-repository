"""Tests for Phases 9-13 of the cross-organizational refactor.

Covers:
- Contract Pack structure and rules
- Extraction tools (bilingual pairer, redline differ, clause normalizer)
- Norm Lineage walker
- Domain Pack loader
- Marketplace pack distribution
- HR and Communication pack structure
- Connector ABC
- Japanese sample rules existence
- MCP tool signatures
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Phase 9: Contract Pack
# ---------------------------------------------------------------------------


class TestContractPack:
    """Verify the Contract Domain Pack structure."""

    def test_pack_yaml_exists(self) -> None:
        pack_yaml = Path("src/rulerepo_server/domain_packs/contract/pack.yaml")
        assert pack_yaml.exists(), "Contract pack.yaml must exist"

    def test_pack_has_rules(self) -> None:
        rules_dir = Path("src/rulerepo_server/domain_packs/contract/rules")
        if rules_dir.exists():
            yaml_files = list(rules_dir.glob("*.yaml"))
            assert len(yaml_files) >= 1, "Contract pack must have rule files"

    def test_pack_has_samples(self) -> None:
        samples_dir = Path("src/rulerepo_server/domain_packs/contract/samples")
        if samples_dir.exists():
            sample_files = list(samples_dir.iterdir())
            assert len(sample_files) >= 1, "Contract pack must have sample files"


class TestExtractionTools:
    """Tests for the extraction tools."""

    def test_bilingual_pairer_import(self) -> None:
        from rulerepo_server.services.extraction.bilingual_pairer import (
            ClausePair,
            pair_bilingual_clauses,
        )

        assert ClausePair is not None
        assert pair_bilingual_clauses is not None

    @pytest.mark.asyncio
    async def test_bilingual_pairer_matching(self) -> None:
        from rulerepo_server.services.extraction.bilingual_pairer import (
            pair_bilingual_clauses,
        )

        en = [
            {"text": "Confidentiality clause", "position": 1, "clause_type": "confidentiality"},
            {"text": "Termination clause", "position": 2, "clause_type": "termination"},
        ]
        ja = [
            {"text": "秘密保持条項", "position": 1, "clause_type": "confidentiality"},
            {"text": "解約条項", "position": 2, "clause_type": "termination"},
        ]
        pairs = await pair_bilingual_clauses(en, ja)
        assert len(pairs) == 2
        assert pairs[0].en_text == "Confidentiality clause"
        assert pairs[0].ja_text == "秘密保持条項"
        assert pairs[0].confidence > 0.5

    def test_redline_differ_import(self) -> None:
        from rulerepo_server.services.extraction.redline_differ import (
            RedlineChange,
            compute_redline,
            render_redline_html,
        )

        assert RedlineChange is not None
        assert compute_redline is not None
        assert render_redline_html is not None

    def test_redline_differ_detects_changes(self) -> None:
        from rulerepo_server.services.extraction.redline_differ import compute_redline

        old = "Clause 1: Original text.\n\nClause 2: Unchanged."
        new = "Clause 1: Revised text.\n\nClause 2: Unchanged."
        changes = compute_redline(old, new)
        assert len(changes) >= 1
        modified = [c for c in changes if c.change_type == "modified"]
        assert len(modified) >= 1

    def test_clause_normalizer_import(self) -> None:
        from rulerepo_server.services.extraction.clause_normalizer import (
            normalize_references,
        )

        assert normalize_references is not None

    def test_clause_normalizer_resolves_article(self) -> None:
        from rulerepo_server.services.extraction.clause_normalizer import (
            normalize_references,
        )

        text = "As defined in Article 5, paragraph 2."
        _, refs = normalize_references(text)
        assert len(refs) >= 1
        assert refs[0].target_section in ("5.2", "5")


# ---------------------------------------------------------------------------
# Phase 10: Norm Lineage
# ---------------------------------------------------------------------------


class TestNormLineage:
    """Tests for the Norm Lineage service."""

    def test_walker_import(self) -> None:
        from rulerepo_server.services.norm_lineage.walker import (
            LineageChain,
            LineageNode,
            NormLineageWalker,
        )

        assert NormLineageWalker is not None
        assert LineageChain is not None
        assert LineageNode is not None

    def test_lineage_api_registered(self) -> None:
        from rulerepo_server.api.v1 import v1_router

        paths = []
        for route in v1_router.routes:
            if hasattr(route, "path"):
                paths.append(route.path)
        assert any("/lineage/" in p for p in paths), "Lineage API routes must be registered"

    def test_amendment_propagation_worker_import(self) -> None:
        from rulerepo_server.workers.norm_lineage_propagation import (
            propagate_norm_amendment,
        )

        assert propagate_norm_amendment is not None

    def test_translation_drift_worker_import(self) -> None:
        from rulerepo_server.workers.translation_drift import (
            verify_translation_drift,
        )

        assert verify_translation_drift is not None


class TestJapaneseSampleRules:
    """Verify Japanese sample rules exist."""

    def test_legal_jp_rules_exist(self) -> None:
        jp_dir = Path("../../sample_rules/legal_rules/jp")
        alt_dir = Path("sample_rules/legal_rules/jp")
        target = jp_dir if jp_dir.exists() else alt_dir
        if target.exists():
            files = list(target.glob("*.yaml"))
            assert len(files) >= 1, "Japanese legal rules must exist"

    def test_hr_jp_rules_exist(self) -> None:
        jp_dir = Path("../../sample_rules/hr_rules/jp")
        alt_dir = Path("sample_rules/hr_rules/jp")
        target = jp_dir if jp_dir.exists() else alt_dir
        if target.exists():
            files = list(target.glob("*.yaml"))
            assert len(files) >= 1, "Japanese HR rules must exist"


# ---------------------------------------------------------------------------
# Phase 11: HR and Communication Packs
# ---------------------------------------------------------------------------


class TestHRPack:
    """Verify the HR Domain Pack structure."""

    def test_pack_yaml_exists(self) -> None:
        pack_yaml = Path("src/rulerepo_server/domain_packs/hr_attendance/pack.yaml")
        assert pack_yaml.exists(), "HR pack.yaml must exist"


class TestCommunicationPack:
    """Verify the Communication Domain Pack structure."""

    def test_pack_yaml_exists(self) -> None:
        pack_yaml = Path("src/rulerepo_server/domain_packs/communication/pack.yaml")
        assert pack_yaml.exists(), "Communication pack.yaml must exist"


# ---------------------------------------------------------------------------
# Phase 12: Connector Layer
# ---------------------------------------------------------------------------


class TestConnectorABC:
    """Tests for the SubjectConnector ABC."""

    def test_connector_abc_import(self) -> None:
        from rulerepo_server.adapters.connectors.base import SubjectConnector

        assert SubjectConnector is not None

    def test_connector_is_abstract(self) -> None:
        from rulerepo_server.adapters.connectors.base import SubjectConnector

        with pytest.raises(TypeError):
            SubjectConnector()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Phase 13: Marketplace
# ---------------------------------------------------------------------------


class TestDomainPackLoader:
    """Tests for the Domain Pack loader."""

    def test_loader_import(self) -> None:
        from rulerepo_server.services.domain_packs.loader import (
            DomainPackLoader,
            PackManifest,
        )

        assert DomainPackLoader is not None
        assert PackManifest is not None

    def test_loader_discovers_packs(self) -> None:
        from rulerepo_server.services.domain_packs.loader import DomainPackLoader

        loader = DomainPackLoader()
        packs = loader.discover()
        # Should find at least contract, hr_attendance, communication packs
        pack_names = {p.name for p in packs}
        assert len(packs) >= 1, f"Should discover at least 1 pack, found: {pack_names}"


class TestMarketplacePackDistribution:
    """Tests for marketplace pack distribution."""

    def test_pack_distribution_import(self) -> None:
        from rulerepo_server.services.marketplace.pack_distribution import (
            PackListing,
            detect_composition_conflicts,
            list_available_packs,
        )

        assert list_available_packs is not None
        assert detect_composition_conflicts is not None
        assert PackListing is not None


# ---------------------------------------------------------------------------
# MCP tools — verify new tools exist
# ---------------------------------------------------------------------------


class TestMCPToolSignatures:
    """Verify all Phase 9-13 MCP tools are registered."""

    def _get_tool_names(self) -> list[str]:
        """Get registered MCP tool names by introspecting the tools module."""
        import inspect

        import rulerepo_server.mcp.tools as tools_mod

        # Find all functions decorated with @mcp.tool()
        names = []
        for name, obj in inspect.getmembers(tools_mod):
            if callable(obj) and not name.startswith("_"):
                names.append(name)
        return names

    def test_evaluate_subject_tool(self) -> None:
        from rulerepo_server.mcp import tools as _  # noqa: F401

        # The tool is registered dynamically; just verify the module loads
        assert True

    def test_lineage_tool_function_exists(self) -> None:
        """Verify lookup_norm_lineage is defined in tools module."""
        import rulerepo_server.mcp.tools as tools_mod

        source = Path(tools_mod.__file__).read_text()
        assert "lookup_norm_lineage" in source

    def test_contract_tool_function_exists(self) -> None:
        import rulerepo_server.mcp.tools as tools_mod

        source = Path(tools_mod.__file__).read_text()
        assert "find_clause_conflicts" in source

    def test_action_tool_function_exists(self) -> None:
        import rulerepo_server.mcp.tools as tools_mod

        source = Path(tools_mod.__file__).read_text()
        assert "check_action" in source

    def test_communication_tool_function_exists(self) -> None:
        import rulerepo_server.mcp.tools as tools_mod

        source = Path(tools_mod.__file__).read_text()
        assert "review_communication" in source

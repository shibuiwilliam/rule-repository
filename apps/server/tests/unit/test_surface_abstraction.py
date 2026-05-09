"""Tests for Phase 8 Surface Abstraction.

Covers:
- Surface enum and Actor dataclass (domain model)
- NormTier enum and new Rule fields
- Surface adapter registry
- Surface adapter parse methods
- Import-graph test (core/ must not import from surfaces/)
- EvaluationService.evaluate_subject method signature
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from rulerepo_server.domain.evaluation import Actor, Surface
from rulerepo_server.domain.rule import NormTier, Rule

# ---------------------------------------------------------------------------
# Domain model tests
# ---------------------------------------------------------------------------


class TestSurface:
    """Tests for the Surface enum."""

    def test_surface_values(self) -> None:
        assert Surface.CODE == "code"
        assert Surface.CONTRACT == "contract"
        assert Surface.HUMAN_ACTION == "human_action"
        assert Surface.TRANSACTION == "transaction"
        assert Surface.DOCUMENT == "document"
        assert Surface.MESSAGE == "message"
        assert Surface.GENERIC == "generic"

    def test_surface_count(self) -> None:
        assert len(Surface) == 7

    def test_surface_from_string(self) -> None:
        assert Surface("code") == Surface.CODE
        assert Surface("contract") == Surface.CONTRACT

    def test_surface_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            Surface("invalid_surface")


class TestActor:
    """Tests for the Actor dataclass."""

    def test_human_actor(self) -> None:
        actor = Actor(kind="human", identifier="user:E001")
        assert actor.kind == "human"
        assert actor.identifier == "user:E001"
        assert actor.attributes == {}

    def test_agent_actor(self) -> None:
        actor = Actor(
            kind="agent",
            identifier="agent:claude-code",
            attributes={"trust_level": "high"},
        )
        assert actor.kind == "agent"
        assert actor.attributes["trust_level"] == "high"

    def test_system_actor(self) -> None:
        actor = Actor(kind="system", identifier="sys:ci-pipeline")
        assert actor.kind == "system"

    def test_actor_is_frozen(self) -> None:
        actor = Actor(kind="human", identifier="user:E001")
        with pytest.raises(AttributeError):
            actor.kind = "agent"  # type: ignore[misc]


class TestNormTier:
    """Tests for the NormTier enum."""

    def test_norm_tier_values(self) -> None:
        assert NormTier.LAW == "LAW"
        assert NormTier.REGULATION == "REGULATION"
        assert NormTier.OPERATIONAL_RULE == "OPERATIONAL_RULE"

    def test_norm_tier_count(self) -> None:
        assert len(NormTier) == 6

    def test_norm_tier_ordering(self) -> None:
        tiers = list(NormTier)
        assert tiers[0] == NormTier.LAW
        assert tiers[-1] == NormTier.OPERATIONAL_RULE


class TestRuleSurfaceFields:
    """Tests for the new Phase 8 fields on Rule."""

    def test_default_applies_to_surfaces(self) -> None:
        rule = Rule(statement="test")
        assert rule.applies_to_surfaces == ["generic"]

    def test_default_norm_tier(self) -> None:
        rule = Rule(statement="test")
        assert rule.norm_tier == NormTier.OPERATIONAL_RULE

    def test_default_locale(self) -> None:
        rule = Rule(statement="test")
        assert rule.locale == "en"

    def test_custom_surface_fields(self) -> None:
        rule = Rule(
            statement="No overtime above 45 hours",
            applies_to_surfaces=["human_action", "transaction"],
            norm_tier=NormTier.LAW,
            norm_authority="Labor Standards Act, Article 36",
            locale="ja",
            statement_translations={"en": "No overtime above 45 hours"},
            tech_scope=[],
            org_scope=["hr/attendance"],
        )
        assert "human_action" in rule.applies_to_surfaces
        assert rule.norm_tier == NormTier.LAW
        assert rule.norm_authority == "Labor Standards Act, Article 36"
        assert rule.locale == "ja"
        assert rule.statement_translations["en"] == "No overtime above 45 hours"

    def test_legacy_scope_still_works(self) -> None:
        """Verify the legacy scope field is preserved."""
        rule = Rule(statement="test", scope=["engineering/python"])
        assert rule.scope == ["engineering/python"]


# ---------------------------------------------------------------------------
# Surface adapter tests
# ---------------------------------------------------------------------------


class TestSurfaceRegistry:
    """Tests for the surface adapter registry."""

    def test_all_surfaces_registered(self) -> None:
        from rulerepo_server.services.evaluation.surfaces import list_surfaces

        surfaces = list_surfaces()
        assert len(surfaces) == 7
        surface_values = {s.value for s in surfaces}
        assert surface_values == {"code", "contract", "human_action", "transaction", "document", "message", "generic"}

    def test_get_adapter_by_enum(self) -> None:
        from rulerepo_server.services.evaluation.surfaces import get_surface_adapter

        adapter = get_surface_adapter(Surface.CODE)
        assert adapter.surface == Surface.CODE

    def test_get_adapter_by_string(self) -> None:
        from rulerepo_server.services.evaluation.surfaces import get_surface_adapter

        adapter = get_surface_adapter("contract")
        assert adapter.surface == Surface.CONTRACT

    def test_get_adapter_unknown_raises(self) -> None:
        from rulerepo_server.services.evaluation.surfaces import get_surface_adapter

        with pytest.raises(KeyError, match="Unknown surface"):
            get_surface_adapter("nonexistent")


class TestCodeSurfaceAdapter:
    """Tests for the Code surface adapter."""

    @pytest.mark.asyncio
    async def test_parse_with_diff(self) -> None:
        from rulerepo_server.services.evaluation.surfaces.code import CodeSurfaceAdapter

        adapter = CodeSurfaceAdapter()
        subject = await adapter.parse(
            {
                "diff": "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new",
                "repository": "test-repo",
            }
        )
        assert subject.surface == Surface.CODE
        assert "foo.py" in subject.description
        assert subject.payload["diff"] is not None

    def test_resolve_scopes_python(self) -> None:
        from rulerepo_server.services.evaluation.surfaces.code import CodeSurfaceAdapter

        adapter = CodeSurfaceAdapter()
        scopes = adapter.resolve_scopes({"files": [{"path": "src/main.py"}]})
        assert "engineering/python" in scopes

    def test_prompt_hints(self) -> None:
        from rulerepo_server.services.evaluation.surfaces.code import CodeSurfaceAdapter

        adapter = CodeSurfaceAdapter()
        hints = adapter.get_prompt_hints()
        assert "code change" in hints.lower()

    def test_retention(self) -> None:
        from rulerepo_server.services.evaluation.surfaces.code import CodeSurfaceAdapter

        assert CodeSurfaceAdapter().default_audit_retention_days == 365


class TestContractSurfaceAdapter:
    """Tests for the Contract surface adapter."""

    @pytest.mark.asyncio
    async def test_parse_clause(self) -> None:
        from rulerepo_server.services.evaluation.surfaces.contract import ContractSurfaceAdapter

        adapter = ContractSurfaceAdapter()
        subject = await adapter.parse(
            {
                "clause_text": "The Receiving Party shall protect Confidential Information...",
                "clause_type": "confidentiality",
                "parties": ["Acme Corp", "Beta Inc"],
                "contract_id": "ACME-2025-Q1",
                "position": 3,
            }
        )
        assert subject.surface == Surface.CONTRACT
        assert "confidentiality" in subject.description
        assert subject.payload["clause_type"] == "confidentiality"
        assert "contract:ACME-2025-Q1" in subject.identifier

    def test_resolve_scopes(self) -> None:
        from rulerepo_server.services.evaluation.surfaces.contract import ContractSurfaceAdapter

        adapter = ContractSurfaceAdapter()
        scopes = adapter.resolve_scopes({"clause_type": "indemnity"})
        assert "legal/contract/indemnity" in scopes
        assert "legal/contract" in scopes

    def test_retention_10_years(self) -> None:
        from rulerepo_server.services.evaluation.surfaces.contract import ContractSurfaceAdapter

        assert ContractSurfaceAdapter().default_audit_retention_days == 3650

    def test_pii_fields(self) -> None:
        from rulerepo_server.services.evaluation.surfaces.contract import ContractSurfaceAdapter

        assert "parties" in ContractSurfaceAdapter().pii_fields({})


class TestHumanActionSurfaceAdapter:
    """Tests for the Human Action surface adapter."""

    @pytest.mark.asyncio
    async def test_parse_overtime(self) -> None:
        from rulerepo_server.services.evaluation.surfaces.human_action import HumanActionSurfaceAdapter

        adapter = HumanActionSurfaceAdapter()
        subject = await adapter.parse(
            {
                "action": "register_overtime",
                "actor_id": "E001",
                "actor_department": "engineering",
                "facts": {"hours": 50, "month": "2026-04"},
            }
        )
        assert subject.surface == Surface.HUMAN_ACTION
        assert subject.actor is not None
        assert subject.actor.kind == "human"
        assert subject.actor.identifier == "user:E001"
        assert subject.facts["hours"] == 50

    def test_resolve_scopes_overtime(self) -> None:
        from rulerepo_server.services.evaluation.surfaces.human_action import HumanActionSurfaceAdapter

        adapter = HumanActionSurfaceAdapter()
        scopes = adapter.resolve_scopes({"action": "register_overtime"})
        assert "hr/attendance" in scopes


# ---------------------------------------------------------------------------
# Import graph test — core/ must not import from surfaces/
# ---------------------------------------------------------------------------


class TestImportBoundary:
    """Verify the evaluation core does not import surface-specific code."""

    def test_core_does_not_import_surfaces(self) -> None:
        """Check that no file in services/evaluation/core/ imports
        from services/evaluation/surfaces/."""
        core_dir = Path(
            importlib.util.find_spec("rulerepo_server.services.evaluation.core").submodule_search_locations[0]  # type: ignore[union-attr]
        )
        violations: list[str] = []

        for py_file in core_dir.rglob("*.py"):
            source = py_file.read_text()
            try:
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "surfaces" in node.module:
                        violations.append(f"{py_file.name}:{node.lineno} imports {node.module}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if "surfaces" in alias.name:
                            violations.append(f"{py_file.name}:{node.lineno} imports {alias.name}")

        assert violations == [], "core/ must not import from surfaces/. Violations:\n" + "\n".join(
            f"  - {v}" for v in violations
        )


# ---------------------------------------------------------------------------
# EvaluationService.evaluate_subject signature test
# ---------------------------------------------------------------------------


class TestEvaluationServiceInterface:
    """Verify the EvaluationService has the surface-aware method."""

    def test_evaluate_subject_method_exists(self) -> None:
        from rulerepo_server.services.evaluation.service import EvaluationService

        assert hasattr(EvaluationService, "evaluate_subject")

    def test_evaluate_subject_accepts_surface_param(self) -> None:
        import inspect

        from rulerepo_server.services.evaluation.service import EvaluationService

        sig = inspect.signature(EvaluationService.evaluate_subject)
        param_names = list(sig.parameters.keys())
        assert "surface" in param_names
        assert "subject_payload" in param_names
        assert "mode" in param_names

    def test_legacy_evaluate_still_exists(self) -> None:
        from rulerepo_server.services.evaluation.service import EvaluationService

        assert hasattr(EvaluationService, "evaluate")


# ---------------------------------------------------------------------------
# API endpoint test
# ---------------------------------------------------------------------------


class TestEvaluationEndpoints:
    """Verify the evaluation API has the surface-aware route."""

    def test_surface_route_registered(self) -> None:
        from rulerepo_server.api.v1.evaluation import router

        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/evaluate/{surface}" in paths

    def test_legacy_route_preserved(self) -> None:
        from rulerepo_server.api.v1.evaluation import router

        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/evaluate" in paths

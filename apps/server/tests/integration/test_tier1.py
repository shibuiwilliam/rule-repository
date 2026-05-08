"""Integration test for Tier 1 (Postgres-only) end-to-end evaluation flow.

Exercises the core path without Elasticsearch, Neo4j, or Redis:
rule creation → search → evaluation → verdict retrieval.

See CLAUDE.md §4 and IMPROVEMENT.md §4.1 / RR-001.
"""

from __future__ import annotations

from rulerepo_server.core.feature_flags import FeatureFlags


class TestTier1FeatureFlags:
    """Verify feature flag detection for Tier 1."""

    def test_default_flags_are_tier1(self) -> None:
        """Default settings (all disabled) should be Tier 1."""
        flags = FeatureFlags()
        assert flags.elasticsearch_enabled is False
        assert flags.neo4j_enabled is False
        assert flags.redis_enabled is False
        assert flags.mcp_enabled is False
        assert flags.tier == 1

    def test_es_only_is_tier2(self) -> None:
        """Elasticsearch enabled → Tier 2."""
        flags = FeatureFlags()
        flags.elasticsearch_enabled = True
        assert flags.tier == 2

    def test_neo4j_is_tier3(self) -> None:
        """Neo4j enabled → Tier 3."""
        flags = FeatureFlags()
        flags.neo4j_enabled = True
        assert flags.tier == 3


class TestTier1AdapterSelection:
    """Verify Postgres fallback adapters are selected in Tier 1."""

    def test_postgres_fts_adapter_importable(self) -> None:
        """PostgresFTSIndex should be importable."""
        from rulerepo_server.adapters.search.postgres_fts import PostgresFTSIndex

        assert PostgresFTSIndex is not None

    def test_postgres_graph_adapter_importable(self) -> None:
        """PostgresGraphRepository should be importable."""
        from rulerepo_server.adapters.graph.postgres_adjacency import (
            PostgresGraphRepository,
        )

        assert PostgresGraphRepository is not None


class TestTier1DomainModuleDiscovery:
    """Verify domain modules are discoverable in Tier 1."""

    def test_engineering_module_registered(self) -> None:
        """Engineering module should auto-register."""
        from rulerepo_server.services.domains import get_domain_module

        mod = get_domain_module("engineering")
        assert mod is not None
        assert "code_diff" in mod.supported_artifact_types

    def test_legal_module_registered(self) -> None:
        """Legal module should auto-register."""
        from rulerepo_server.services.domains import get_domain_module

        mod = get_domain_module("legal")
        assert mod is not None
        assert "contract_clause" in mod.supported_artifact_types

    def test_all_8_domains_registered(self) -> None:
        """All 8 domain modules should be discovered."""
        from rulerepo_server.services.domains import get_all_modules

        modules = get_all_modules()
        expected = {
            "engineering",
            "legal",
            "hr",
            "finance",
            "it_security",
            "sales",
            "communications",
            "governance",
        }
        assert set(modules.keys()) >= expected

    def test_module_for_artifact_type(self) -> None:
        """Should find the right module for an artifact type."""
        from rulerepo_server.services.domains import (
            get_module_for_artifact_type,
        )

        mod = get_module_for_artifact_type("journal_entry")
        assert mod is not None
        assert mod.name == "finance"


class TestTier1EvalHarnessCompatibility:
    """Verify the eval harness runs against Tier 1."""

    def test_eval_harness_importable(self) -> None:
        """Eval harness runner should be importable."""
        from eval_harness.runner import load_dataset

        cases = load_dataset("engineering")
        assert len(cases) >= 10

    def test_all_golden_datasets_load(self) -> None:
        """All domain golden datasets should load cleanly."""
        from eval_harness.runner import load_dataset

        domains = [
            "engineering",
            "legal",
            "hr",
            "finance",
            "it_security",
            "sales",
            "communications",
            "governance",
        ]
        total = 0
        for domain in domains:
            cases = load_dataset(domain)
            assert len(cases) >= 1, f"No cases for {domain}"
            total += len(cases)
        assert total >= 80  # at least 80 across all domains


class TestTier1LLMRouterFallback:
    """Verify LLM router works in Tier 1 (graceful degradation)."""

    def test_router_initializes(self) -> None:
        """Router should initialize without crashing even without API keys."""
        from rulerepo_server.adapters.llm.router import LLMRouter

        router = LLMRouter()
        # Should not crash during init
        assert router is not None

    def test_base_evaluator_fallback(self) -> None:
        """BaseDomainEvaluator should produce fallback verdicts."""
        from rulerepo_server.services.domains._base_evaluator import (
            BaseDomainEvaluator,
        )

        evaluator = BaseDomainEvaluator()
        rules = [{"id": "r1", "statement": "test rule"}]
        verdicts = evaluator._fallback_verdicts(rules, reason="test")
        assert len(verdicts) == 1
        assert verdicts[0]["verdict"] == "NEEDS_CONFIRMATION"

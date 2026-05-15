"""Tests for feature flag initialization and defaults."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from rulerepo_server.core.config import Settings
from rulerepo_server.core.feature_flags import FeatureFlags


@pytest.fixture()
def _clear_caches() -> None:
    """Clear lru_cache so each test gets fresh instances."""
    from rulerepo_server.core.config import get_settings
    from rulerepo_server.core.feature_flags import get_feature_flags

    get_settings.cache_clear()
    get_feature_flags.cache_clear()
    yield  # type: ignore[misc]
    get_settings.cache_clear()
    get_feature_flags.cache_clear()


def _make_flags(**overrides: object) -> FeatureFlags:
    """Create FeatureFlags backed by a Settings instance with optional overrides."""
    settings = Settings(**overrides)  # type: ignore[arg-type]
    with patch("rulerepo_server.core.feature_flags.get_settings", return_value=settings):
        return FeatureFlags()


class TestDeferredFeaturesDefaultOff:
    """Deferred Phase 6 features must default to False."""

    def test_marketplace_enabled(self) -> None:
        flags = _make_flags()
        assert flags.marketplace_enabled is False

    def test_gateway_external_intake_enabled(self) -> None:
        flags = _make_flags()
        assert flags.gateway_external_intake_enabled is False

    def test_observability_digest_delivery_enabled(self) -> None:
        flags = _make_flags()
        assert flags.observability_digest_delivery_enabled is False

    def test_agent_trust_auto_promotion_enabled(self) -> None:
        flags = _make_flags()
        assert flags.agent_trust_auto_promotion_enabled is False

    def test_agent_negotiation_enabled(self) -> None:
        flags = _make_flags()
        assert flags.agent_negotiation_enabled is False

    def test_multi_agent_sessions_enabled(self) -> None:
        flags = _make_flags()
        assert flags.multi_agent_sessions_enabled is False

    def test_github_app_enabled(self) -> None:
        flags = _make_flags()
        assert flags.github_app_enabled is False

    def test_gateway_enabled(self) -> None:
        flags = _make_flags()
        assert flags.gateway_enabled is False

    def test_advanced_observability_enabled(self) -> None:
        flags = _make_flags()
        assert flags.advanced_observability_enabled is False


class TestRefocusMigrationTogglesDefaultOn:
    """Refocus migration toggles must default to True (except ABAC)."""

    def test_evaluation_subject_v2_enabled(self) -> None:
        flags = _make_flags()
        assert flags.evaluation_subject_v2_enabled is True

    def test_structured_scope_enabled(self) -> None:
        flags = _make_flags()
        assert flags.structured_scope_enabled is True

    def test_rule_kind_polymorphism_enabled(self) -> None:
        flags = _make_flags()
        assert flags.rule_kind_polymorphism_enabled is True

    def test_domain_packs_enabled(self) -> None:
        flags = _make_flags()
        assert flags.domain_packs_enabled is True

    def test_hybrid_evaluation_enabled(self) -> None:
        flags = _make_flags()
        assert flags.hybrid_evaluation_enabled is True

    def test_persona_routing_enabled(self) -> None:
        flags = _make_flags()
        assert flags.persona_routing_enabled is True

    def test_abac_governance_defaults_off(self) -> None:
        flags = _make_flags()
        assert flags.abac_governance_enabled is False


class TestOverrides:
    """Settings overrides propagate to FeatureFlags."""

    def test_enable_marketplace(self) -> None:
        flags = _make_flags(marketplace_enabled=True)
        assert flags.marketplace_enabled is True

    def test_disable_evaluation_subject_v2(self) -> None:
        flags = _make_flags(evaluation_subject_v2_enabled=False)
        assert flags.evaluation_subject_v2_enabled is False

    def test_enable_abac_governance(self) -> None:
        flags = _make_flags(abac_governance_enabled=True)
        assert flags.abac_governance_enabled is True

    def test_enable_agent_negotiation(self) -> None:
        flags = _make_flags(agent_negotiation_enabled=True)
        assert flags.agent_negotiation_enabled is True


class TestTierDerivation:
    """Tier detection is unaffected by the new flags."""

    def test_tier_1_default(self) -> None:
        flags = _make_flags()
        assert flags.tier == 1

    def test_tier_2_with_elasticsearch(self) -> None:
        flags = _make_flags(elasticsearch_enabled=True)
        assert flags.tier == 2

    def test_tier_3_with_neo4j(self) -> None:
        flags = _make_flags(neo4j_enabled=True)
        assert flags.tier == 3

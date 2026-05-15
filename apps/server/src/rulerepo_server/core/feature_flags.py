"""Tier-aware feature flags derived from environment variables.

Provides runtime detection of which optional infrastructure components
(Elasticsearch, Neo4j, Redis, MCP) are available, and derives the
effective deployment tier from those flags.
"""

from __future__ import annotations

from functools import lru_cache

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class FeatureFlags:
    """Runtime feature detection based on ``*_ENABLED`` env vars.

    Tier derivation:
        - Tier 1: Postgres only (no ES, no Neo4j, no Redis).
        - Tier 2: Postgres + Elasticsearch + Redis.
        - Tier 3: Full stack (+ Neo4j, MCP).
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.elasticsearch_enabled: bool = getattr(settings, "elasticsearch_enabled", False)
        self.neo4j_enabled: bool = getattr(settings, "neo4j_enabled", False)
        self.redis_enabled: bool = getattr(settings, "redis_enabled", False)
        self.mcp_enabled: bool = getattr(settings, "mcp_enabled", False)

        # Cross-Organizational direction (Phase 7)
        self.cross_org_features_enabled: bool = getattr(settings, "cross_org_features_enabled", True)
        self.department_rbac_enabled: bool = getattr(settings, "department_rbac_enabled", True)
        self.assistant_enabled: bool = getattr(settings, "assistant_enabled", True)
        self.compliance_cockpit_enabled: bool = getattr(settings, "compliance_cockpit_enabled", True)
        self.polyglot_verification_enabled: bool = getattr(settings, "polyglot_verification_enabled", True)

        # Opt-in features (default OFF)
        self.multi_agent_sessions_enabled: bool = getattr(settings, "multi_agent_sessions_enabled", False)
        self.github_app_enabled: bool = getattr(settings, "github_app_enabled", False)

        # Frozen features (Phase 6 freeze — default OFF)
        self.gateway_enabled: bool = getattr(settings, "gateway_enabled", False)
        self.advanced_observability_enabled: bool = getattr(settings, "advanced_observability_enabled", False)

        # Deferred subsystems (CLAUDE.md §14.11)
        self.marketplace_enabled: bool = getattr(settings, "marketplace_enabled", False)
        self.gateway_external_intake_enabled: bool = getattr(settings, "gateway_external_intake_enabled", False)
        self.observability_digest_delivery_enabled: bool = getattr(
            settings, "observability_digest_delivery_enabled", False
        )
        self.agent_trust_auto_promotion_enabled: bool = getattr(settings, "agent_trust_auto_promotion_enabled", False)
        self.agent_negotiation_enabled: bool = getattr(settings, "agent_negotiation_enabled", False)

        # Refocus migration toggles
        self.evaluation_subject_v2_enabled: bool = getattr(settings, "evaluation_subject_v2_enabled", True)
        self.structured_scope_enabled: bool = getattr(settings, "structured_scope_enabled", True)
        self.rule_kind_polymorphism_enabled: bool = getattr(settings, "rule_kind_polymorphism_enabled", True)
        self.domain_packs_enabled: bool = getattr(settings, "domain_packs_enabled", True)
        self.hybrid_evaluation_enabled: bool = getattr(settings, "hybrid_evaluation_enabled", True)
        self.persona_routing_enabled: bool = getattr(settings, "persona_routing_enabled", True)
        self.abac_governance_enabled: bool = getattr(settings, "abac_governance_enabled", False)

        # Alert / Digest delivery mode
        self.alert_output_mode: str = getattr(settings, "alert_output_mode", "local")
        self.digest_output_mode: str = getattr(settings, "digest_output_mode", "local")

    @property
    def tier(self) -> int:
        """Return the effective deployment tier (1, 2, or 3)."""
        if self.neo4j_enabled:
            return 3
        if self.elasticsearch_enabled or self.redis_enabled:
            return 2
        return 1

    def log_tier_info(self) -> None:
        """Log the detected tier and enabled components."""
        logger.info(
            "tier_detected",
            tier=self.tier,
            elasticsearch=self.elasticsearch_enabled,
            neo4j=self.neo4j_enabled,
            redis=self.redis_enabled,
            mcp=self.mcp_enabled,
        )


@lru_cache
def get_feature_flags() -> FeatureFlags:
    """Return cached feature flags singleton."""
    return FeatureFlags()

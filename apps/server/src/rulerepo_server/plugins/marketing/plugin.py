"""Marketing domain plugin — content evaluation and compliance.

Registers evaluators, extractors, and feedback sources with the
plugin registry. Covers advertising compliance, claim verification,
brand guideline enforcement, regulatory extraction, and campaign
compliance tracking.

See: PROJECT.md SS6.4, CLAUDE.md SS12.5
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.plugins.base import (
    Evaluator,
    Extractor,
    FactProvider,
    FeedbackSource,
    PersonaView,
)
from rulerepo_server.plugins.marketing.evaluators.content_evaluator import (
    ContentEvaluator,
)
from rulerepo_server.plugins.marketing.evaluators.creative_evaluator import (
    CreativeComplianceEvaluator,
)
from rulerepo_server.plugins.marketing.extractors.brand_guidelines import (
    BrandGuidelinesExtractor,
)
from rulerepo_server.plugins.marketing.extractors.regulatory_advertising import (
    RegulatoryAdvertisingExtractor,
)
from rulerepo_server.plugins.marketing.feedback.campaign_compliance import (
    CampaignComplianceCapture,
)


class MarketingPersonaView:
    """Marketing department dashboard persona view."""

    @property
    def name(self) -> str:
        return "marketing_dashboard"

    @property
    def domain(self) -> str:
        return "marketing"

    @property
    def route_group(self) -> str:
        return "(marketing)"

    def get_navigation_items(self) -> list[dict[str, str]]:
        """Return marketing-specific navigation items."""
        return [
            {"label": "Content Reviews", "href": "/creatives/review", "icon": "image"},
            {"label": "Marketing Rules", "href": "/rules?scope=marketing", "icon": "book"},
            {"label": "Campaign Compliance", "href": "/marketing/campaigns", "icon": "megaphone"},
            {"label": "Claim Tracker", "href": "/marketing/claims", "icon": "check-square"},
        ]

    def get_dashboard_widgets(self) -> list[dict[str, Any]]:
        """Return marketing dashboard widget configurations."""
        return [
            {
                "type": "violation_summary",
                "title": "Content Violations (30d)",
                "config": {"domain": "marketing", "period_days": 30},
            },
            {
                "type": "pending_reviews",
                "title": "Pending Content Reviews",
                "config": {"subject_kinds": ["creative", "document"], "limit": 10},
            },
            {
                "type": "claim_status",
                "title": "Unsubstantiated Claims",
                "config": {"domain": "marketing", "claim_status": "unverified"},
            },
            {
                "type": "channel_compliance",
                "title": "Compliance by Channel",
                "config": {"scope_prefix": "marketing/"},
            },
        ]


class MarketingPlugin:
    """Marketing domain plugin.

    Provides marketing content evaluation against advertising
    regulations, brand guidelines, and claim substantiation
    requirements.
    """

    @property
    def name(self) -> str:
        return "Marketing"

    @property
    def domain(self) -> str:
        return "marketing"

    @property
    def description(self) -> str:
        return (
            "Marketing content evaluation against advertising regulations "
            "(Keihyohou, Yakkihou), brand guidelines, and claim "
            "substantiation requirements."
        )

    def get_evaluators(self) -> list[Evaluator]:
        """Return content and creative compliance evaluators."""
        return [ContentEvaluator(), CreativeComplianceEvaluator()]

    def get_extractors(self) -> list[Extractor]:
        """Return brand guidelines and regulatory advertising extractors."""
        return [BrandGuidelinesExtractor(), RegulatoryAdvertisingExtractor()]

    def get_feedback_sources(self) -> list[FeedbackSource]:
        """Return the campaign compliance feedback source."""
        return [CampaignComplianceCapture()]

    def get_fact_providers(self) -> list[FactProvider]:
        """No external fact providers registered yet."""
        return []

    def get_persona_views(self) -> list[PersonaView]:
        """Return the marketing dashboard persona view."""
        return [MarketingPersonaView()]


def create_plugin() -> MarketingPlugin:
    """Factory function called by the plugin loader.

    Returns:
        A MarketingPlugin instance.
    """
    return MarketingPlugin()

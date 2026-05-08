"""Engineering domain plugin — code review, linter extraction, PR feedback.

Registers the code_change evaluator, code-source extractors (CLAUDE.md,
linter configs), and the PR correction feedback source with the plugin
registry.

See: PROJECT.md SS6.4, CLAUDE.md SS12.1
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
from rulerepo_server.plugins.engineering.evaluators.code_change import (
    CodeChangeEvaluator,
)
from rulerepo_server.plugins.engineering.extractors.claude_md import (
    ClaudeMdExtractor,
)
from rulerepo_server.plugins.engineering.extractors.linter_config import (
    LinterConfigExtractor,
)
from rulerepo_server.plugins.engineering.feedback.pr_capture import (
    PrCorrectionCapture,
)


class EngineeringPersonaView:
    """Engineering department dashboard persona view."""

    @property
    def name(self) -> str:
        return "engineering_dashboard"

    @property
    def domain(self) -> str:
        return "engineering"

    @property
    def route_group(self) -> str:
        return "(dashboard)"

    def get_navigation_items(self) -> list[dict[str, str]]:
        """Return engineering-specific navigation items."""
        return [
            {"label": "Code Reviews", "href": "/evaluations?domain=engineering", "icon": "code"},
            {"label": "Engineering Rules", "href": "/rules?scope=engineering", "icon": "book"},
            {"label": "CI/CD Integration", "href": "/integrations/ci", "icon": "git-branch"},
            {"label": "Code Quality", "href": "/intelligence?domain=engineering", "icon": "bar-chart"},
        ]

    def get_dashboard_widgets(self) -> list[dict[str, Any]]:
        """Return engineering dashboard widget configurations."""
        return [
            {
                "type": "violation_summary",
                "title": "Code Violations (7d)",
                "config": {"domain": "engineering", "period_days": 7},
            },
            {
                "type": "rule_health",
                "title": "Engineering Rule Health",
                "config": {"scope_prefix": "engineering/"},
            },
            {
                "type": "recent_evaluations",
                "title": "Recent Code Evaluations",
                "config": {"subject_kind": "code_diff", "limit": 10},
            },
            {
                "type": "top_violations",
                "title": "Top Violated Rules",
                "config": {"domain": "engineering", "limit": 5},
            },
        ]


class EngineeringPlugin:
    """Engineering domain plugin.

    Provides code-change evaluation, rule extraction from CLAUDE.md
    and linter configs, and PR correction feedback capture.
    """

    @property
    def name(self) -> str:
        return "Engineering"

    @property
    def domain(self) -> str:
        return "engineering"

    @property
    def description(self) -> str:
        return (
            "Code review evaluation, rule extraction from engineering "
            "artifacts (CLAUDE.md, linter configs), and PR correction "
            "feedback for the rule improvement flywheel."
        )

    def get_evaluators(self) -> list[Evaluator]:
        """Return the code change evaluator."""
        return [CodeChangeEvaluator()]

    def get_extractors(self) -> list[Extractor]:
        """Return CLAUDE.md and linter config extractors."""
        return [ClaudeMdExtractor(), LinterConfigExtractor()]

    def get_feedback_sources(self) -> list[FeedbackSource]:
        """Return the PR correction feedback source."""
        return [PrCorrectionCapture()]

    def get_fact_providers(self) -> list[FactProvider]:
        """Engineering does not provide external facts."""
        return []

    def get_persona_views(self) -> list[PersonaView]:
        """Return the engineering dashboard persona view."""
        return [EngineeringPersonaView()]


def create_plugin() -> EngineeringPlugin:
    """Factory function called by the plugin loader.

    Returns:
        An EngineeringPlugin instance.
    """
    return EngineeringPlugin()

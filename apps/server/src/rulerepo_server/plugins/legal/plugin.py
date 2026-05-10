"""Legal domain plugin — document evaluation, clause extraction.

Registers the document evaluator and clause extractor with the
plugin registry. Covers contract review, NDA compliance, and
legal document analysis.

See: PROJECT.md SS6.4, CLAUDE.md SS12.2
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
from rulerepo_server.plugins.legal.evaluators.document_evaluator import (
    DocumentEvaluator,
)
from rulerepo_server.plugins.legal.evaluators.risk_classifier import (
    RiskClassifier,
)
from rulerepo_server.plugins.legal.extractors.clause_extractor import (
    ClauseExtractor,
)
from rulerepo_server.plugins.legal.extractors.contract_template import (
    ContractTemplateExtractor,
)
from rulerepo_server.plugins.legal.feedback.negotiation_history import (
    NegotiationHistoryCapture,
)


class LegalPersonaView:
    """Legal department dashboard persona view."""

    @property
    def name(self) -> str:
        return "legal_dashboard"

    @property
    def domain(self) -> str:
        return "legal"

    @property
    def route_group(self) -> str:
        return "(legal)"

    def get_navigation_items(self) -> list[dict[str, str]]:
        """Return legal-specific navigation items."""
        return [
            {"label": "Contract Reviews", "href": "/contracts/review", "icon": "file-text"},
            {"label": "Legal Rules", "href": "/rules?scope=legal", "icon": "book"},
            {"label": "Clause Library", "href": "/legal/clauses", "icon": "library"},
            {"label": "Compliance Status", "href": "/legal/compliance", "icon": "shield"},
            {"label": "Regulation Tracker", "href": "/legal/regulations", "icon": "globe"},
        ]

    def get_dashboard_widgets(self) -> list[dict[str, Any]]:
        """Return legal dashboard widget configurations."""
        return [
            {
                "type": "violation_summary",
                "title": "Contract Compliance Issues (30d)",
                "config": {"domain": "legal", "period_days": 30},
            },
            {
                "type": "pending_reviews",
                "title": "Pending Contract Reviews",
                "config": {"subject_kinds": ["clause_set", "document"], "limit": 10},
            },
            {
                "type": "regulation_alerts",
                "title": "Regulation Updates",
                "config": {"domain": "legal"},
            },
            {
                "type": "clause_deviation",
                "title": "Standard Clause Deviations",
                "config": {"scope_prefix": "legal/contracts"},
            },
        ]


class LegalPlugin:
    """Legal domain plugin.

    Provides contract and legal document evaluation, and clause
    extraction from contract corpora for building standard clause
    libraries.
    """

    @property
    def name(self) -> str:
        return "Legal"

    @property
    def domain(self) -> str:
        return "legal"

    @property
    def description(self) -> str:
        return (
            "Contract and legal document evaluation against organizational "
            "rules, and clause extraction from contract corpora for building "
            "standard clause libraries."
        )

    def get_evaluators(self) -> list[Evaluator]:
        """Return legal domain evaluators."""
        return [DocumentEvaluator(), RiskClassifier()]

    def get_extractors(self) -> list[Extractor]:
        """Return legal domain extractors."""
        return [ClauseExtractor(), ContractTemplateExtractor()]

    def get_feedback_sources(self) -> list[FeedbackSource]:
        """Return legal domain feedback sources."""
        return [NegotiationHistoryCapture()]

    def get_fact_providers(self) -> list[FactProvider]:
        """No external fact providers registered yet."""
        return []

    def get_persona_views(self) -> list[PersonaView]:
        """Return the legal dashboard persona view."""
        return [LegalPersonaView()]


def create_plugin() -> LegalPlugin:
    """Factory function called by the plugin loader.

    Returns:
        A LegalPlugin instance.
    """
    return LegalPlugin()

"""Finance domain plugin — transaction and expense evaluation.

Registers evaluators, extractors, and feedback sources with the plugin
registry. Covers expense claims, purchase orders, approval matrices,
policy extraction, and audit findings analysis.

See: PROJECT.md SS6.4, CLAUDE.md SS12.4
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
from rulerepo_server.plugins.finance.evaluators.expense_evaluator import (
    ExpenseEvaluator,
)
from rulerepo_server.plugins.finance.evaluators.transaction_evaluator import (
    TransactionEvaluator,
)
from rulerepo_server.plugins.finance.extractors.approval_matrix import (
    ApprovalMatrixExtractor,
)
from rulerepo_server.plugins.finance.extractors.expense_policy import (
    ExpensePolicyExtractor,
)
from rulerepo_server.plugins.finance.feedback.audit_findings import (
    AuditFindingsCapture,
)


class FinancePersonaView:
    """Finance department dashboard persona view."""

    @property
    def name(self) -> str:
        return "finance_dashboard"

    @property
    def domain(self) -> str:
        return "finance"

    @property
    def route_group(self) -> str:
        return "(finance)"

    def get_navigation_items(self) -> list[dict[str, str]]:
        """Return finance-specific navigation items."""
        return [
            {"label": "Expense Reviews", "href": "/transactions", "icon": "dollar-sign"},
            {"label": "Finance Rules", "href": "/rules?scope=finance", "icon": "book"},
            {"label": "Approval Queue", "href": "/finance/approvals", "icon": "check-circle"},
            {"label": "Compliance Reports", "href": "/finance/compliance", "icon": "bar-chart"},
        ]

    def get_dashboard_widgets(self) -> list[dict[str, Any]]:
        """Return finance dashboard widget configurations."""
        return [
            {
                "type": "violation_summary",
                "title": "Finance Violations (30d)",
                "config": {"domain": "finance", "period_days": 30},
            },
            {
                "type": "pending_reviews",
                "title": "Pending Expense Approvals",
                "config": {"subject_kinds": ["transaction"], "limit": 10},
            },
            {
                "type": "spending_trends",
                "title": "Spending by Category",
                "config": {"scope_prefix": "finance/"},
            },
            {
                "type": "threshold_alerts",
                "title": "Budget Threshold Alerts",
                "config": {"domain": "finance", "alert_types": ["budget_limit", "approval_required"]},
            },
        ]


class FinancePlugin:
    """Finance domain plugin.

    Provides transaction and expense claim evaluation against finance
    rules covering approval thresholds, documentation requirements,
    segregation of duties, and anti-bribery controls.
    """

    @property
    def name(self) -> str:
        return "Finance"

    @property
    def domain(self) -> str:
        return "finance"

    @property
    def description(self) -> str:
        return (
            "Financial transaction and expense claim evaluation against "
            "finance rules covering approval thresholds, documentation, "
            "segregation of duties, and anti-bribery compliance. "
            "Includes extraction from approval matrices and expense policies, "
            "plus audit findings feedback for continuous rule improvement."
        )

    def get_evaluators(self) -> list[Evaluator]:
        """Return transaction and expense evaluators."""
        return [TransactionEvaluator(), ExpenseEvaluator()]

    def get_extractors(self) -> list[Extractor]:
        """Return approval matrix and expense policy extractors."""
        return [ApprovalMatrixExtractor(), ExpensePolicyExtractor()]

    def get_feedback_sources(self) -> list[FeedbackSource]:
        """Return the audit findings feedback source."""
        return [AuditFindingsCapture()]

    def get_fact_providers(self) -> list[FactProvider]:
        """No external fact providers registered yet."""
        return []

    def get_persona_views(self) -> list[PersonaView]:
        """Return the finance dashboard persona view."""
        return [FinancePersonaView()]


def create_plugin() -> FinancePlugin:
    """Factory function called by the plugin loader.

    Returns:
        A FinancePlugin instance.
    """
    return FinancePlugin()

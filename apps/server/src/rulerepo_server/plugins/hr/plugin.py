"""HR domain plugin — form evaluation, handbook extraction.

Registers the HR form evaluator and handbook extractor with the
plugin registry. Covers attendance, overtime, leave, compensation,
and conduct evaluation.

See: PROJECT.md SS6.4, CLAUDE.md SS12.3
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
from rulerepo_server.plugins.hr.evaluators.attendance_evaluator import AttendanceEvaluator
from rulerepo_server.plugins.hr.evaluators.form_evaluator import FormEvaluator
from rulerepo_server.plugins.hr.extractors.attendance_system import AttendanceSystemExtractor
from rulerepo_server.plugins.hr.extractors.handbook import HandbookExtractor
from rulerepo_server.plugins.hr.feedback.violation_patterns import ViolationPatternCapture


class HRPersonaView:
    """HR department dashboard persona view."""

    @property
    def name(self) -> str:
        return "hr_dashboard"

    @property
    def domain(self) -> str:
        return "hr"

    @property
    def route_group(self) -> str:
        return "(hr)"

    def get_navigation_items(self) -> list[dict[str, str]]:
        """Return HR-specific navigation items."""
        return [
            {"label": "Event Reviews", "href": "/events", "icon": "calendar"},
            {"label": "HR Rules", "href": "/rules?scope=hr", "icon": "book"},
            {"label": "Overtime Tracking", "href": "/hr/overtime", "icon": "clock"},
            {"label": "Leave Management", "href": "/hr/leave", "icon": "calendar-check"},
            {"label": "Compliance Dashboard", "href": "/hr/compliance", "icon": "shield"},
        ]

    def get_dashboard_widgets(self) -> list[dict[str, Any]]:
        """Return HR dashboard widget configurations."""
        return [
            {
                "type": "violation_summary",
                "title": "HR Violations (30d)",
                "config": {"domain": "hr", "period_days": 30},
            },
            {
                "type": "overtime_heatmap",
                "title": "Overtime Distribution",
                "config": {"scope_prefix": "hr/attendance"},
            },
            {
                "type": "recent_evaluations",
                "title": "Recent HR Events",
                "config": {"subject_kind": "event", "limit": 10},
            },
            {
                "type": "threshold_alerts",
                "title": "Threshold Alerts",
                "config": {"domain": "hr", "alert_types": ["overtime_limit", "leave_balance"]},
            },
        ]


class HRPlugin:
    """HR domain plugin.

    Provides HR form evaluation for overtime, leave, and attendance events,
    and handbook extraction for populating the rule repository from
    existing HR policy documents.
    """

    @property
    def name(self) -> str:
        return "HR"

    @property
    def domain(self) -> str:
        return "hr"

    @property
    def description(self) -> str:
        return (
            "HR event evaluation (overtime, leave, attendance) against "
            "labor and policy rules, and rule extraction from HR handbooks "
            "and policy documents."
        )

    def get_evaluators(self) -> list[Evaluator]:
        """Return HR evaluators (form and attendance)."""
        return [FormEvaluator(), AttendanceEvaluator()]

    def get_extractors(self) -> list[Extractor]:
        """Return HR extractors (handbook and attendance system)."""
        return [HandbookExtractor(), AttendanceSystemExtractor()]

    def get_feedback_sources(self) -> list[FeedbackSource]:
        """Return HR feedback sources (violation pattern capture)."""
        return [ViolationPatternCapture()]

    def get_fact_providers(self) -> list[FactProvider]:
        """No external fact providers registered yet."""
        return []

    def get_persona_views(self) -> list[PersonaView]:
        """Return the HR dashboard persona view."""
        return [HRPersonaView()]


def create_plugin() -> HRPlugin:
    """Factory function called by the plugin loader.

    Returns:
        An HRPlugin instance.
    """
    return HRPlugin()

"""Business event evaluation domain adapter.

Handles structured facts about HR, finance, procurement, or other business
actions. Extracts Subject information and builds EvaluationContext with
business-relevant facts.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext
from rulerepo_server.domain.subject import Subject

# Mapping from event_type prefixes to rule scopes
EVENT_TYPE_SCOPE_MAP: dict[str, str] = {
    "hr/attendance": "hr/attendance",
    "hr/leave": "hr/leave",
    "hr/overtime": "hr/overtime",
    "hr/hiring": "hr/hiring",
    "hr/termination": "hr/termination",
    "hr/compensation": "hr/compensation",
    "hr": "hr/general",
    "finance/expense": "finance/expense",
    "finance/invoice": "finance/invoice",
    "finance/budget": "finance/budget",
    "finance/payment": "finance/payment",
    "finance": "finance/general",
    "procurement/purchase": "procurement/purchase",
    "procurement/vendor": "procurement/vendor",
    "procurement": "procurement/general",
    "compliance/audit": "compliance/audit",
    "compliance/report": "compliance/report",
    "compliance": "compliance/general",
}


class BusinessEventAdapter:
    """Adapter for business event evaluation.

    Parses structured business event payloads into EvaluationContext,
    extracts Subject information, and resolves scopes from event types.
    """

    domain: str = "business_event"

    async def parse(self, payload: dict[str, Any]) -> EvaluationContext:
        """Parse a business event payload into EvaluationContext.

        Expected payload keys:
            - event_type: str (e.g., "hr/overtime")
            - subject: dict with Subject fields (organization_unit, role, etc.)
            - facts: dict of key-value business facts
            - description: str narrative description of the event
            - actor: str who performed the action

        Args:
            payload: Business event payload dict.

        Returns:
            EvaluationContext with facts and narrative populated.
        """
        # Extract subject
        subject = _extract_subject(payload.get("subject", {}))

        # Build facts dict with event metadata
        facts: dict[str, Any] = dict(payload.get("facts", {}))
        facts["event_type"] = payload.get("event_type", "unknown")

        # Include subject fields in facts for LLM context
        if subject.organization_unit:
            facts["subject_organization_unit"] = subject.organization_unit
        if subject.role:
            facts["subject_role"] = subject.role
        if subject.employment_type:
            facts["subject_employment_type"] = subject.employment_type
        if subject.location:
            facts["subject_location"] = subject.location
        if subject.seniority_level is not None:
            facts["subject_seniority_level"] = subject.seniority_level
        if subject.department:
            facts["subject_department"] = subject.department

        # Build narrative
        description = payload.get("description", "")
        event_type = payload.get("event_type", "unknown")
        narrative = description or f"Business event: {event_type}"

        return EvaluationContext(
            facts=facts,
            narrative=narrative,
            intent=description or None,
            actor=payload.get("actor"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from the business event type and subject.

        Args:
            payload: Dict with 'event_type' and optional 'subject' keys.

        Returns:
            Deduplicated list of scope strings.
        """
        scopes: set[str] = set()

        event_type = payload.get("event_type", "")

        # Match event type against scope map (longest prefix first)
        for prefix in sorted(EVENT_TYPE_SCOPE_MAP, key=len, reverse=True):
            if event_type.startswith(prefix):
                scopes.add(EVENT_TYPE_SCOPE_MAP[prefix])
                break

        # Add department-based scope if available
        subject_data = payload.get("subject", {})
        if isinstance(subject_data, dict):
            department = subject_data.get("department")
            if department:
                scopes.add(f"department/{department.lower()}")

        return sorted(scopes) if scopes else ["business/general"]

    def get_prompt_fragments(self) -> dict[str, str]:
        """Return business-event specific prompt fragments.

        Returns:
            Dict with domain_intro and context_format keys.
        """
        return {
            "domain_intro": (
                "You are evaluating a business event for compliance with organizational "
                "rules and policies. Focus on regulatory compliance, internal policy "
                "adherence, and proper authorization."
            ),
            "context_format": (
                "The input describes a business event with structured facts including "
                "the event type, involved subject (employee/entity), and relevant "
                "details. Evaluate whether the described action or situation complies "
                "with the given rules."
            ),
        }


def _extract_subject(data: dict[str, Any] | Any) -> Subject:
    """Extract a Subject from a dict, tolerating missing fields.

    Args:
        data: Dict with Subject field names, or any other value.

    Returns:
        Subject instance with available fields populated.
    """
    if not isinstance(data, dict):
        return Subject()

    seniority = data.get("seniority_level")
    if seniority is not None:
        try:
            seniority = int(seniority)
        except (ValueError, TypeError):
            seniority = None

    return Subject(
        organization_unit=data.get("organization_unit"),
        role=data.get("role"),
        employment_type=data.get("employment_type"),
        location=data.get("location"),
        seniority_level=seniority,
        department=data.get("department"),
    )

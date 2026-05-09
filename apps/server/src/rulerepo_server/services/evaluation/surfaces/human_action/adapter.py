"""Human action surface adapter — evaluates HR events and business actions.

Wraps the existing BusinessEventAdapter with the Surface abstraction.
See CLAUDE.md §14.6.1.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import Actor, Surface
from rulerepo_server.services.evaluation.surfaces.base import (
    EvaluationSubjectPayload,
    SurfaceAdapter,
)


class HumanActionSurfaceAdapter(SurfaceAdapter):
    """Surface adapter for human actions and HR events.

    Handles attendance records, leave requests, overtime registration,
    expense claims, and other business events involving human actors.
    """

    @property
    def surface(self) -> Surface:
        return Surface.HUMAN_ACTION

    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a human action event into a uniform subject.

        Expected payload keys:
            - action: str (e.g., "register_overtime", "submit_leave_request")
            - actor_id: str — employee or person identifier
            - actor_role: str — job role
            - actor_department: str — department
            - facts: dict — structured facts about the action
            - description: str — narrative description

        Returns:
            EvaluationSubjectPayload with HR/business-action fields.
        """
        action = payload.get("action", "unknown_action")
        actor_id = payload.get("actor_id", "unknown")
        description = payload.get("description", "")

        if not description:
            description = f"Human action: {action} by {actor_id}"

        facts = dict(payload.get("facts", {}))
        facts["action"] = action

        actor = None
        if actor_id != "unknown":
            actor = Actor(
                kind="human",
                identifier=f"user:{actor_id}",
                attributes={
                    k: payload[k] for k in ("actor_role", "actor_department", "actor_location") if k in payload
                },
            )

        return EvaluationSubjectPayload(
            surface=Surface.HUMAN_ACTION,
            identifier=f"action:{actor_id}/{action}",
            description=description,
            payload={
                "action": action,
                "actor_id": actor_id,
                "event_type": payload.get("event_type", action),
            },
            facts=facts,
            actor=actor,
            locale=payload.get("locale", "en"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from the action type and department."""
        scopes: set[str] = set()

        action = payload.get("action", "")
        # Map common action prefixes to scopes
        if "overtime" in action or "attendance" in action:
            scopes.add("hr/attendance")
        elif "leave" in action:
            scopes.add("hr/leave")
        elif "expense" in action:
            scopes.add("finance/expense")
        elif "hiring" in action or "termination" in action:
            scopes.add("hr/hiring")

        department = payload.get("actor_department", "")
        if department:
            scopes.add(f"department/{department.lower()}")

        return sorted(scopes) if scopes else ["hr/general"]

    def get_prompt_hints(self) -> str:
        return (
            "You are evaluating a human action or business event for compliance "
            "with HR, labor, or organizational rules. Focus on regulatory "
            "compliance (labor law, employment regulations), internal policy "
            "adherence, and proper authorization. Consider jurisdiction-specific "
            "requirements (e.g., Japanese Labor Standards Act Article 36 for overtime)."
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        return ["actor_id", "facts.employee_name"]  # Employee names are PII

    @property
    def default_audit_retention_days(self) -> int:
        return 2555  # ~7 years for HR records

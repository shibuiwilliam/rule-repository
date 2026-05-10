"""Human action surface adapter — evaluates HR events and business actions.

Provides action type classification, actor context enrichment, temporal
context analysis, authority verification, and department-based scope resolution.

See CLAUDE.md §14.8 for the Universal Business Event Schema.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from rulerepo_server.domain.evaluation import Actor, Surface
from rulerepo_server.services.evaluation.surfaces.base import (
    EvaluationSubjectPayload,
    SurfaceAdapter,
)

_HINTS_FILE = Path(__file__).parent / "prompts" / "action_hints.txt"

# --------------------------------------------------------------------------
# Action type classification
# --------------------------------------------------------------------------

_ACTION_TYPE_MAP: dict[str, str] = {
    # Approvals
    "approve": "approval",
    "approve_expense": "approval",
    "approve_leave": "approval",
    "approve_overtime": "approval",
    "approve_purchase": "approval",
    "authorize": "approval",
    # Submissions
    "submit": "submission",
    "submit_expense": "submission",
    "submit_report": "submission",
    "submit_leave": "submission",
    "request_leave": "submission",
    "clock_in": "submission",
    "clock_out": "submission",
    # Overrides
    "override": "override",
    "force_approve": "override",
    "bypass": "override",
    "waive": "override",
    "exception": "override",
    # Delegations
    "delegate": "delegation",
    "proxy": "delegation",
    "assign": "delegation",
    "transfer_authority": "delegation",
    # Escalations
    "escalate": "escalation",
    "appeal": "escalation",
    "raise_concern": "escalation",
    "whistle_blow": "escalation",
    # HR lifecycle
    "hiring": "lifecycle",
    "termination": "lifecycle",
    "promotion": "lifecycle",
    "transfer": "lifecycle",
    "probation_end": "lifecycle",
    "retirement": "lifecycle",
    # Attendance
    "overtime": "attendance",
    "attendance": "attendance",
    "late_arrival": "attendance",
    "early_departure": "attendance",
    "absence": "attendance",
    # Leave
    "leave": "leave",
    "sick_leave": "leave",
    "annual_leave": "leave",
    "maternity_leave": "leave",
    "childcare_leave": "leave",
    "bereavement_leave": "leave",
}

# Action type → scope mapping
_ACTION_SCOPE_MAP: dict[str, list[str]] = {
    "approval": ["governance/approval"],
    "submission": ["governance/submission"],
    "override": ["governance/override", "compliance/exception"],
    "delegation": ["governance/delegation"],
    "escalation": ["governance/escalation", "compliance/whistleblower"],
    "lifecycle": ["hr/lifecycle"],
    "attendance": ["hr/attendance"],
    "leave": ["hr/leave"],
}

# Department + action → additional scopes
_DEPARTMENT_ACTION_SCOPES: dict[str, dict[str, list[str]]] = {
    "finance": {
        "approval": ["finance/approval-authority"],
        "override": ["finance/override", "compliance/audit"],
    },
    "hr": {
        "lifecycle": ["hr/employment", "compliance/labor-law"],
        "attendance": ["hr/attendance", "compliance/labor-law"],
        "leave": ["hr/leave", "compliance/labor-law"],
    },
    "legal": {
        "approval": ["legal/contract-authority"],
        "delegation": ["legal/delegation"],
    },
    "sales": {
        "override": ["sales/discount-authority", "finance/revenue"],
    },
}

# --------------------------------------------------------------------------
# Authority levels (seniority → permitted action types)
# --------------------------------------------------------------------------

_AUTHORITY_REQUIREMENTS: dict[str, dict[str, int | str]] = {
    "approval": {"min_seniority": 3, "description": "Manager level or above"},
    "override": {"min_seniority": 5, "description": "Director level or above"},
    "delegation": {"min_seniority": 3, "description": "Manager level or above"},
    "escalation": {"min_seniority": 1, "description": "Any employee"},
    "lifecycle": {"min_seniority": 4, "description": "Senior manager or above"},
}

# --------------------------------------------------------------------------
# Temporal context patterns
# --------------------------------------------------------------------------

_BUSINESS_HOURS = (9, 18)  # 9:00-18:00
_JP_FISCAL_YEAR_START_MONTH = 4  # April


def _classify_action(action: str) -> str:
    """Classify action string into an action type category."""
    action_lower = action.lower().replace(" ", "_").replace("-", "_")

    # Direct lookup
    if action_lower in _ACTION_TYPE_MAP:
        return _ACTION_TYPE_MAP[action_lower]

    # Partial match
    for key, action_type in _ACTION_TYPE_MAP.items():
        if key in action_lower:
            return action_type

    return "unknown"


def _enrich_actor_context(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract and enrich actor context from payload."""
    context: dict[str, Any] = {}

    if payload.get("actor_role"):
        context["role"] = payload["actor_role"]
    if payload.get("actor_department"):
        context["department"] = payload["actor_department"]
    if payload.get("actor_location"):
        context["location"] = payload["actor_location"]

    # Seniority (from payload or facts)
    seniority = payload.get("actor_seniority") or payload.get("facts", {}).get("seniority")
    if seniority is not None:
        context["seniority"] = int(seniority)

    # Employment type
    emp_type = payload.get("employment_type") or payload.get("facts", {}).get("employment_type")
    if emp_type:
        context["employment_type"] = emp_type

    # Tenure
    hire_date = payload.get("facts", {}).get("hire_date")
    if hire_date:
        context["hire_date"] = hire_date

    return context


def _analyze_temporal_context(payload: dict[str, Any]) -> dict[str, Any]:
    """Analyze temporal aspects of the action."""
    temporal: dict[str, Any] = {}

    # Parse action timestamp
    timestamp_str = payload.get("timestamp") or payload.get("facts", {}).get("timestamp")
    if timestamp_str:
        try:
            ts = datetime.fromisoformat(timestamp_str) if isinstance(timestamp_str, str) else timestamp_str
            temporal["timestamp"] = ts.isoformat()
            temporal["hour"] = ts.hour
            temporal["is_business_hours"] = _BUSINESS_HOURS[0] <= ts.hour < _BUSINESS_HOURS[1]
            temporal["is_weekend"] = ts.weekday() >= 5
            temporal["day_of_week"] = ts.strftime("%A")

            # Fiscal context
            month = ts.month
            fiscal_quarter = ((month - _JP_FISCAL_YEAR_START_MONTH) % 12) // 3 + 1
            temporal["fiscal_quarter"] = f"Q{fiscal_quarter}"
            temporal["is_fiscal_year_end"] = month == 3  # March = JP fiscal year end
            temporal["is_month_end"] = ts.day >= 25
        except (ValueError, TypeError):
            pass

    # Deadline proximity
    deadline = payload.get("facts", {}).get("deadline")
    if deadline and timestamp_str:
        try:
            dl = datetime.fromisoformat(deadline) if isinstance(deadline, str) else deadline
            ts_parsed = datetime.fromisoformat(timestamp_str) if isinstance(timestamp_str, str) else timestamp_str
            if hasattr(dl, "timestamp") and hasattr(ts_parsed, "timestamp"):
                days_to_deadline = (dl - ts_parsed).days
                temporal["days_to_deadline"] = days_to_deadline
                temporal["deadline_urgent"] = days_to_deadline <= 1
        except (ValueError, TypeError):
            pass

    return temporal


def _check_authority(action_type: str, actor_context: dict[str, Any]) -> dict[str, Any]:
    """Check if the actor has authority for this action type."""
    authority = _AUTHORITY_REQUIREMENTS.get(action_type)
    if not authority:
        return {"authorized": True, "reason": "no_restriction"}

    seniority = actor_context.get("seniority")
    if seniority is None:
        return {"authorized": None, "reason": "seniority_unknown"}

    min_required = authority["min_seniority"]
    return {
        "authorized": seniority >= min_required,
        "reason": authority["description"],
        "actor_seniority": seniority,
        "required_seniority": min_required,
    }


class HumanActionSurfaceAdapter(SurfaceAdapter):
    """Surface adapter for human actions and HR/business events.

    Handles attendance records, leave requests, overtime registration,
    approvals, overrides, delegations, escalations, and other business
    events involving human actors. Provides action classification, actor
    context enrichment, temporal analysis, and authority verification.
    """

    @property
    def surface(self) -> Surface:
        return Surface.HUMAN_ACTION

    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a human action event into a uniform subject.

        Expected payload keys:
            - action: str (e.g., "register_overtime", "approve_expense")
            - actor_id: str — employee or person identifier
            - actor_role: str — job role
            - actor_department: str — department
            - actor_location: str — work location
            - actor_seniority: int — seniority level
            - employment_type: str — full-time, part-time, contract
            - timestamp: str — when the action occurred (ISO format)
            - description: str — narrative description
            - facts: dict — structured facts about the action

        Returns:
            EvaluationSubjectPayload with HR/business-action fields.
        """
        action = payload.get("action", "unknown_action")
        actor_id = payload.get("actor_id", "unknown")
        description = payload.get("description", "")

        # Classify the action
        action_type = _classify_action(action)

        # Enrich actor context
        actor_context = _enrich_actor_context(payload)

        # Temporal analysis
        temporal_context = _analyze_temporal_context(payload)

        # Authority check
        authority_check = _check_authority(action_type, actor_context)

        # Build facts
        facts = dict(payload.get("facts", {}))
        facts["action"] = action
        facts["action_type"] = action_type
        if actor_context:
            facts["actor_context"] = actor_context
        if temporal_context:
            facts["temporal_context"] = temporal_context
        if authority_check:
            facts["authority_check"] = authority_check

        # Build description
        if not description:
            dept_str = f" ({actor_context.get('department', '')})" if actor_context.get("department") else ""
            description = f"Human action: {action} by {actor_id}{dept_str}"
            if temporal_context.get("timestamp"):
                description += f" at {temporal_context['timestamp']}"
            if not authority_check.get("authorized"):
                description += " [AUTHORITY CHECK: may lack required seniority]"

        # Build Actor object
        actor = None
        if actor_id != "unknown":
            actor = Actor(
                kind="human",
                identifier=f"user:{actor_id}",
                attributes={
                    **{k: v for k, v in actor_context.items() if v is not None},
                    "action_type": action_type,
                },
            )

        return EvaluationSubjectPayload(
            surface=Surface.HUMAN_ACTION,
            identifier=f"action:{actor_id}/{action}",
            description=description,
            payload={
                "action": action,
                "action_type": action_type,
                "actor_id": actor_id,
                "event_type": payload.get("event_type", action),
                "actor_context": actor_context,
                "temporal_context": temporal_context,
                "authority_check": authority_check,
            },
            facts=facts,
            actor=actor,
            locale=payload.get("locale", "ja"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from action type, department, and context.

        Uses action_type + department → scope mapping equivalent to the
        code adapter's file-path → language scope mapping.
        """
        scopes: set[str] = set()

        action = payload.get("action", "")
        action_type = _classify_action(action)

        # Map action type to base scopes
        if action_type in _ACTION_SCOPE_MAP:
            scopes.update(_ACTION_SCOPE_MAP[action_type])

        # Department-specific scopes
        department = (payload.get("actor_department") or "").lower()
        if department in _DEPARTMENT_ACTION_SCOPES:
            dept_scopes = _DEPARTMENT_ACTION_SCOPES[department]
            if action_type in dept_scopes:
                scopes.update(dept_scopes[action_type])

        # Always add department scope
        if department:
            scopes.add(f"department/{department}")

        # Specific action-based scopes (kept from original)
        if "overtime" in action or "attendance" in action:
            scopes.add("hr/attendance")
        elif "leave" in action:
            scopes.add("hr/leave")
        elif "expense" in action:
            scopes.add("finance/expense")
        elif "hiring" in action or "termination" in action:
            scopes.add("hr/hiring")

        return sorted(scopes) if scopes else ["hr/general"]

    def get_prompt_hints(self) -> str:
        """Return action-specific prompt hints."""
        if _HINTS_FILE.exists():
            return _HINTS_FILE.read_text()
        return (
            "You are evaluating a human action or business event for compliance "
            "with HR, labor, or organizational rules. Focus on regulatory "
            "compliance, authorization, and proper process."
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        return ["actor_id", "facts.employee_name"]

    @property
    def default_audit_retention_days(self) -> int:
        return 2555  # ~7 years for HR records

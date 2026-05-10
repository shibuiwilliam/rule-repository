"""Domain model for universal business event ingestion.

A BusinessEvent is the canonical envelope that business systems use to push
artifacts to the Rule Repository for evaluation. See PROJECT.md §5.5.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from rulerepo_server.domain.subject import EvaluationSubject


@dataclass(frozen=True)
class ActorRef:
    """Reference to the actor who initiated the event.

    Attributes:
        type: Actor category (employee, system, agent).
        id: Stable identifier (e.g., ``E001``, ``system:payroll``).
        department: Department the actor belongs to.
    """

    type: Literal["employee", "system", "agent"]
    id: str
    department: str | None = None


@dataclass(frozen=True)
class BusinessEvent:
    """A structured business event pushed by an external system.

    The handler resolves scope from ``event_type``, selects rules, dispatches
    to the correct subject evaluator, and returns synchronous verdicts.

    Attributes:
        event_type: Dot-separated event name (e.g., ``finance.expense.submitted``).
        actor: Who initiated the event.
        subject: The evaluation subject embedded in the event.
        occurred_at: When the event happened in the source system.
        correlation_id: The business system's own identifier.
        mode: Evaluation mode.
    """

    event_type: str
    actor: ActorRef
    subject: EvaluationSubject
    occurred_at: datetime
    correlation_id: str
    mode: Literal["preflight", "posthoc", "sidecar"] = "preflight"


# ---------------------------------------------------------------------------
# Event-type to scope mapping
# ---------------------------------------------------------------------------

# Default mapping convention: ``{department}.{action}.{noun}``
DEFAULT_EVENT_SCOPE_MAP: dict[str, list[str]] = {
    "finance.expense.submitted": ["finance/expense", "compliance/anti-bribery"],
    "finance.expense.approved": ["finance/expense"],
    "finance.purchase_order.created": ["finance/procurement"],
    "hr.attendance.registered": ["hr/attendance", "hr/overtime"],
    "hr.overtime.filed": ["hr/overtime"],
    "hr.leave.requested": ["hr/leave"],
    "legal.contract.draft_created": ["legal/contract"],
    "legal.contract.signed": ["legal/contract"],
    "sales.email.drafted": ["sales/communication", "compliance/privacy"],
    "marketing.creative.submitted": ["marketing/compliance"],
    "engineering.pr.opened": ["engineering/code"],
}

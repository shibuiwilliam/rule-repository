"""Human action subject — the unit of evaluation for HR and business events.

See CLAUDE.md §14.6.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class HumanAction:
    """Subject representing a human action or HR event.

    Attributes:
        action: Action identifier (e.g., "register_overtime", "submit_leave_request").
        actor_id: Employee or person identifier.
        actor_role: Job role or title.
        actor_department: Department the actor belongs to.
        facts: Structured facts (hours worked, dates, amounts, etc.).
        description: Narrative description of the action.
        timestamp: When the action occurred.
        locale: Locale of the action context.
    """

    action: str
    actor_id: str
    actor_role: str = ""
    actor_department: str = ""
    facts: dict[str, object] = field(default_factory=dict)
    description: str = ""
    timestamp: datetime | None = None
    locale: str = "en"

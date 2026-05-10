"""Polymorphic Remediation kinds — see PROJECT.md §5.6 and CLAUDE.md §14.6.

Each RemediationKind has typed semantics. Consumers must handle all kinds
exhaustively via ``match`` on ``RemediationKind``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RemediationKind(StrEnum):
    """Discriminator for polymorphic remediation payloads."""

    CODE_EDIT = "code_edit"
    TEXT_REWRITE = "text_rewrite"
    FIELD_CHANGE = "field_change"
    APPROVAL_ADD = "approval_add"
    PROCESS_REROUTE = "process_reroute"
    CLARIFICATION = "clarification"
    BLOCK = "block"


@dataclass(frozen=True)
class PolymorphicRemediation:
    """A typed remediation proposal for fixing a rule violation.

    The ``kind`` field determines the structure of ``payload``.
    ``auto_applicable`` is True only when the kind permits unambiguous
    mechanical fixes and confidence is high.

    Attributes:
        kind: Remediation type.
        auto_applicable: Whether the fix can be applied without human review.
        description: Human-readable explanation.
        payload: Kind-specific structure.
    """

    kind: RemediationKind
    auto_applicable: bool
    description: str
    payload: dict[str, Any] = field(default_factory=dict)

    def validate_payload(self) -> bool:
        """Check that payload contains required fields for the kind."""
        match self.kind:
            case RemediationKind.CODE_EDIT:
                return all(k in self.payload for k in ("file_path", "start_line", "replacement"))
            case RemediationKind.TEXT_REWRITE:
                return all(k in self.payload for k in ("offset_start", "offset_end", "original", "suggested"))
            case RemediationKind.FIELD_CHANGE:
                return all(k in self.payload for k in ("field_path", "current_value", "suggested_value"))
            case RemediationKind.APPROVAL_ADD:
                return "approver" in self.payload
            case RemediationKind.PROCESS_REROUTE:
                return "target_process" in self.payload
            case RemediationKind.CLARIFICATION:
                return "missing_element" in self.payload
            case RemediationKind.BLOCK:
                return True  # No specific payload required

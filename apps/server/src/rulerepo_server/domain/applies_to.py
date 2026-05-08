"""Domain model for rule applicability — what kind of artifact a rule evaluates.

Formalizes the ``applicable_subject_types`` field into a typed ``AppliesTo``
object.  The ``artifact_type`` field drives domain-module dispatch: the
evaluation orchestrator filters by artifact type *before* embedding-based
ranking to prevent cross-domain contamination.

See PROJECT.md §5.1 and IMPROVEMENT.md §3.1.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class ArtifactType(str, enum.Enum):
    """All recognized artifact types across domains.

    Each domain module declares which artifact types it handles via
    ``DomainModule.supported_artifact_types``.
    """

    # Engineering
    CODE_DIFF = "code_diff"
    CODE_FILE = "code_file"

    # Legal
    CONTRACT_CLAUSE = "contract_clause"
    CONTRACT_DOCUMENT = "contract_document"

    # Finance
    JOURNAL_ENTRY = "journal_entry"
    EXPENSE_REQUEST = "expense_request"
    PO_REQUEST = "po_request"
    INVOICE = "invoice"

    # HR
    ATTENDANCE_RECORD = "attendance_record"
    LEAVE_REQUEST = "leave_request"
    EVALUATION_COMMENT = "evaluation_comment"

    # Sales / Marketing
    AD_COPY = "ad_copy"
    DISCOUNT_REQUEST = "discount_request"
    QUOTE = "quote"

    # IT Security
    IAC_PLAN = "iac_plan"
    ACCESS_REQUEST = "access_request"

    # Communications
    EMAIL_MESSAGE = "email_message"
    CHAT_MESSAGE = "chat_message"

    # Governance
    DISCLOSURE_DOCUMENT = "disclosure_document"
    BOARD_MINUTE = "board_minute"

    # Generic fallback
    FREE_TEXT = "free_text"


@dataclass(frozen=True)
class AppliesTo:
    """Declares what kind of artifacts a rule evaluates.

    Args:
        artifact_types: One or more artifact types this rule applies to.
            A rule may declare multiple types for cross-domain applicability.
        artifact_schema_ref: Optional JSON Schema URI for structured artifacts.
        triggering_events: Events that trigger evaluation (e.g., on_create,
            on_submit, on_publish).
    """

    artifact_types: list[str] = field(default_factory=lambda: ["code_diff"])
    artifact_schema_ref: str | None = None
    triggering_events: list[str] = field(default_factory=list)

"""Contract clause subject — the unit of evaluation for the contract surface.

See CLAUDE.md §14.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ContractClause:
    """Subject representing a contract clause for evaluation.

    Attributes:
        text: The clause text to evaluate.
        position: Clause position in the document (0-indexed).
        clause_type: Classification (e.g., "confidentiality", "indemnity",
            "termination", "liability", "ip", "payment").
        parties: Parties to the contract.
        document_id: Source document reference.
        contract_id: Contract identifier.
        locale: Language of the clause (default "en").
        governing_law: Applicable governing law jurisdiction.
        effective_date: Contract effective date if known.
        facts: Additional structured facts.
        timestamp: When the clause was submitted for evaluation.
    """

    text: str = ""
    position: int = 0
    clause_type: str = "general"
    parties: list[str] = field(default_factory=list)
    document_id: str = ""
    contract_id: str = ""
    locale: str = "en"
    governing_law: str = ""
    effective_date: str = ""
    facts: dict[str, object] = field(default_factory=dict)
    timestamp: datetime | None = None

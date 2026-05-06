"""Domain models for document/contract evaluation.

Per CLAUDE.md Tier 2: ContractType, PartyRole, and ContractScope define
the metadata needed for document diff evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ContractType(StrEnum):
    """Types of contracts supported by the document_diff adapter."""

    NDA = "nda"
    MSA = "msa"
    SOW = "sow"
    DPA = "dpa"
    LEASE = "lease"
    SALES = "sales"
    OTHER = "other"


class PartyRole(StrEnum):
    """Role of the evaluating party in the contract."""

    DISCLOSING = "disclosing"
    RECEIVING = "receiving"
    BOTH = "both"


@dataclass(frozen=True)
class ContractScope:
    """Metadata defining the scope and context of a contract evaluation.

    Attributes:
        contract_type: Type of contract (NDA, MSA, etc.).
        governing_law: Jurisdiction or governing law (e.g., "japan", "us-delaware").
        counterparty_country: Country of the counterparty.
        party_role: Role of the evaluating party.
        language: Language of the contract text (e.g., "en", "ja").
    """

    contract_type: ContractType | None = None
    governing_law: str | None = None
    counterparty_country: str | None = None
    party_role: PartyRole | None = None
    language: str | None = None

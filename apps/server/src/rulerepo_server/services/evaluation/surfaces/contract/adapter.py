"""Contract surface adapter — evaluates contract clauses against rules.

Provides clause hierarchy detection (Japanese 条/項/号 and Western
Article/Section/Clause structures), party extraction, governing law
detection, and contract-type-based scope resolution.

See CLAUDE.md §14.3 for the Contract Pack specification.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from rulerepo_server.domain.evaluation import Surface
from rulerepo_server.services.evaluation.surfaces.base import (
    EvaluationSubjectPayload,
    SurfaceAdapter,
)

_HINTS_FILE = Path(__file__).parent / "prompts" / "contract_hints.txt"

# --------------------------------------------------------------------------
# Contract type → scope mapping (equivalent to code's file-path → scope)
# --------------------------------------------------------------------------

_CONTRACT_TYPE_SCOPE_MAP: dict[str, list[str]] = {
    "nda": ["legal/confidentiality", "legal/contract"],
    "confidentiality": ["legal/confidentiality", "legal/contract"],
    "employment": ["hr/employment", "legal/contract"],
    "service": ["legal/service-level", "legal/contract"],
    "sla": ["legal/service-level", "legal/contract"],
    "procurement": ["finance/procurement", "legal/contract"],
    "purchase": ["finance/procurement", "legal/contract"],
    "license": ["legal/ip", "legal/contract"],
    "ip": ["legal/ip", "legal/contract"],
    "lease": ["legal/real-estate", "legal/contract"],
    "loan": ["finance/lending", "legal/contract"],
    "partnership": ["legal/partnership", "legal/contract"],
    "joint_venture": ["legal/partnership", "legal/contract"],
    "settlement": ["legal/dispute", "legal/contract"],
    "consulting": ["legal/service-level", "finance/procurement"],
    "distribution": ["legal/distribution", "legal/contract"],
    "agency": ["legal/agency", "legal/contract"],
    "franchise": ["legal/franchise", "legal/contract"],
    "merger": ["legal/ma", "finance/corporate"],
    "acquisition": ["legal/ma", "finance/corporate"],
}

# Clause type → risk level classification
_HIGH_RISK_CLAUSE_TYPES = frozenset(
    {
        "indemnity",
        "liability",
        "limitation_of_liability",
        "termination",
        "non_compete",
        "exclusivity",
        "liquidated_damages",
        "guarantee",
        "warranty",
        "ip_assignment",
        "change_of_control",
    }
)
_MEDIUM_RISK_CLAUSE_TYPES = frozenset(
    {
        "payment",
        "pricing",
        "intellectual_property",
        "audit",
        "data_protection",
        "insurance",
        "subcontracting",
        "assignment",
    }
)

# --------------------------------------------------------------------------
# Japanese clause hierarchy patterns
# --------------------------------------------------------------------------

_JP_ARTICLE_RE = re.compile(r"第\s*(\d+)\s*条")
_JP_PARAGRAPH_RE = re.compile(r"第?\s*(\d+)\s*項")
_JP_ITEM_RE = re.compile(r"第?\s*(\d+)\s*号")

# Western clause hierarchy patterns
_WEST_ARTICLE_RE = re.compile(r"(?:Article|ARTICLE|Art\.?)\s+(\d+)", re.IGNORECASE)
_WEST_SECTION_RE = re.compile(r"(?:Section|SECTION|Sec\.?)\s+(\d+[\.\d]*)", re.IGNORECASE)
_WEST_CLAUSE_RE = re.compile(r"(?:Clause|CLAUSE|Cl\.?)\s+(\d+[\.\d]*)", re.IGNORECASE)

# Governing law detection patterns (multiple patterns to cover different structures)
_GOVERNING_LAW_PATTERNS: list[re.Pattern[str]] = [
    # English: "governed by X", "subject to X"
    re.compile(r"(?:governed?\s+by|subject\s+to)\s+(?:the\s+laws?\s+of\s+)?([^\n,;.]+)", re.IGNORECASE),
    # Japanese: "X法に準拠" or "X法を準拠法とする"
    re.compile(r"([^\s、。,]+法)に準拠", re.IGNORECASE),
    # Japanese: "準拠法はX" or "準拠法:X"
    re.compile(r"準拠法[\s:\uff1aはを]*([^\n,;。]+)", re.IGNORECASE),
    # Japanese: "適用法令はX"
    re.compile(r"適用法令[\s:\uff1aはを]*([^\n,;。]+)", re.IGNORECASE),
]

# Party detection patterns
_PARTY_PATTERNS = [
    re.compile(r"(?:between|among)\s+(.+?)\s+(?:and|及び)\s+(.+?)(?:\s*[\uff08(]|[,;。\n])", re.IGNORECASE),
    re.compile(r"(?:甲|Party\s*A)[\s:\uff1a]*(.+?)(?:\n|[,;。])", re.IGNORECASE),
    re.compile(r"(?:乙|Party\s*B)[\s:\uff1a]*(.+?)(?:\n|[,;。])", re.IGNORECASE),
]


def _detect_clause_hierarchy(text: str) -> dict[str, Any]:
    """Detect clause numbering structure from text.

    Returns a dict with detected hierarchy components:
    - system: "japanese" or "western" or "unknown"
    - article: article number if found
    - paragraph/section: paragraph/section number if found
    - item/clause: item/clause number if found
    - reference: human-readable clause reference string
    """
    result: dict[str, Any] = {"system": "unknown", "reference": ""}

    # Try Japanese structure first
    jp_article = _JP_ARTICLE_RE.search(text)
    if jp_article:
        result["system"] = "japanese"
        result["article"] = int(jp_article.group(1))
        ref_parts = [f"第{jp_article.group(1)}条"]

        jp_para = _JP_PARAGRAPH_RE.search(text[jp_article.end() :])
        if jp_para:
            result["paragraph"] = int(jp_para.group(1))
            ref_parts.append(f"第{jp_para.group(1)}項")

        jp_item = _JP_ITEM_RE.search(text[jp_article.end() :])
        if jp_item:
            result["item"] = int(jp_item.group(1))
            ref_parts.append(f"第{jp_item.group(1)}号")

        result["reference"] = " ".join(ref_parts)
        return result

    # Try Western structure
    west_article = _WEST_ARTICLE_RE.search(text)
    if west_article:
        result["system"] = "western"
        result["article"] = west_article.group(1)
        ref_parts = [f"Article {west_article.group(1)}"]

        west_section = _WEST_SECTION_RE.search(text)
        if west_section:
            result["section"] = west_section.group(1)
            ref_parts.append(f"Section {west_section.group(1)}")

        west_clause = _WEST_CLAUSE_RE.search(text)
        if west_clause:
            result["clause"] = west_clause.group(1)
            ref_parts.append(f"Clause {west_clause.group(1)}")

        result["reference"] = ", ".join(ref_parts)
        return result

    # Fallback: check for numbered patterns like "3.2.1"
    numbered = re.search(r"(\d+(?:\.\d+)+)", text[:200])
    if numbered:
        result["system"] = "numbered"
        result["reference"] = numbered.group(1)

    return result


def _extract_parties(text: str, payload_parties: list[str]) -> list[str]:
    """Extract contracting parties from text or payload."""
    if payload_parties:
        return payload_parties

    parties: list[str] = []
    for pattern in _PARTY_PATTERNS:
        match = pattern.search(text)
        if match:
            for group in match.groups():
                cleaned = group.strip().rstrip("\uff08(\uff09)")
                if cleaned and len(cleaned) < 100:
                    parties.append(cleaned)

    return parties


def _detect_governing_law(text: str) -> str | None:
    """Detect governing law from clause text."""
    for pattern in _GOVERNING_LAW_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip().rstrip("。.、")
    return None


def _classify_risk_level(clause_type: str) -> str:
    """Classify clause risk level based on type."""
    normalized = clause_type.lower().replace(" ", "_").replace("-", "_")
    if normalized in _HIGH_RISK_CLAUSE_TYPES:
        return "high"
    if normalized in _MEDIUM_RISK_CLAUSE_TYPES:
        return "medium"
    return "low"


class ContractSurfaceAdapter(SurfaceAdapter):
    """Surface adapter for contract clause evaluation.

    Handles clause text, clause type, parties, and contract metadata.
    Provides clause hierarchy detection, party extraction, governing law
    detection, and contract-type-based scope resolution.
    """

    @property
    def surface(self) -> Surface:
        return Surface.CONTRACT

    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a contract clause evaluation request.

        Expected payload keys:
            - clause_text: str — the clause to evaluate
            - clause_type: str (e.g., "indemnity", "termination", "confidentiality")
            - contract_type: str (e.g., "nda", "employment", "service")
            - parties: list[str] — parties to the contract
            - contract_id: str — contract identifier
            - position: int — clause position in the document
            - locale: str — language of the clause (default "ja")
            - document_id: str — source document reference
            - governing_law: str — explicit governing law
            - contract_value: str | float — total contract value
            - effective_date: str — contract effective date

        Returns:
            EvaluationSubjectPayload with contract-specific fields.
        """
        clause_text = payload.get("clause_text", "")
        clause_type = payload.get("clause_type", "general")
        contract_type = payload.get("contract_type", "general")
        contract_id = payload.get("contract_id", "unknown")

        # Detect clause hierarchy from text
        hierarchy = _detect_clause_hierarchy(clause_text)

        # Extract parties
        parties = _extract_parties(clause_text, payload.get("parties", []))

        # Detect governing law (from payload or text)
        governing_law = payload.get("governing_law") or _detect_governing_law(clause_text)

        # Classify risk
        risk_level = _classify_risk_level(clause_type)

        parties_str = ", ".join(parties) if parties else "unspecified parties"
        clause_ref = hierarchy.get("reference", f"position {payload.get('position', 0)}")
        description = (
            f"Contract clause ({clause_type}, risk: {risk_level}) "
            f"at {clause_ref} between {parties_str}:\n\n{clause_text}"
        )

        facts: dict[str, Any] = {
            "clause_type": clause_type,
            "contract_type": contract_type,
            "risk_level": risk_level,
            "hierarchy": hierarchy,
        }
        if payload.get("contract_value"):
            facts["contract_value"] = payload["contract_value"]
        if governing_law:
            facts["governing_law"] = governing_law
        if payload.get("effective_date"):
            facts["effective_date"] = payload["effective_date"]
        if parties:
            facts["parties"] = parties
        if hierarchy.get("reference"):
            facts["clause_reference"] = hierarchy["reference"]

        return EvaluationSubjectPayload(
            surface=Surface.CONTRACT,
            identifier=f"contract:{contract_id}/clause:{payload.get('position', 0)}",
            description=description,
            payload={
                "clause_text": clause_text,
                "clause_type": clause_type,
                "contract_type": contract_type,
                "parties": parties,
                "position": payload.get("position", 0),
                "document_id": payload.get("document_id"),
                "hierarchy": hierarchy,
                "risk_level": risk_level,
            },
            facts=facts,
            locale=payload.get("locale", "ja"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from contract type, clause type, and governing law.

        Uses a contract-type → scope mapping equivalent to the code adapter's
        file-path → language scope mapping.
        """
        scopes: set[str] = set()

        # Map contract type to scopes
        contract_type = payload.get("contract_type", "").lower().replace(" ", "_").replace("-", "_")
        if contract_type in _CONTRACT_TYPE_SCOPE_MAP:
            scopes.update(_CONTRACT_TYPE_SCOPE_MAP[contract_type])

        # Map clause type to additional scopes
        clause_type = payload.get("clause_type", "").lower().replace(" ", "_").replace("-", "_")
        if clause_type:
            scopes.add(f"legal/clause/{clause_type}")

        # Add jurisdiction scope if governing law is present
        governing_law = payload.get("governing_law", "")
        if governing_law:
            law_lower = governing_law.lower()
            if "日本" in law_lower or "japan" in law_lower:
                scopes.add("jurisdiction/jp")
            elif "england" in law_lower or "uk" in law_lower:
                scopes.add("jurisdiction/uk")
            elif "new york" in law_lower or "delaware" in law_lower:
                scopes.add("jurisdiction/us")
            elif "singapore" in law_lower:
                scopes.add("jurisdiction/sg")

        # Always include base legal/contract scope
        scopes.add("legal/contract")

        return sorted(scopes)

    def get_prompt_hints(self) -> str:
        """Return contract-specific prompt hints."""
        if _HINTS_FILE.exists():
            return _HINTS_FILE.read_text()
        return (
            "You are evaluating a contract clause for compliance with legal and "
            "organizational rules. Focus on legal risks, missing protections, "
            "non-standard terms, and regulatory compliance."
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        return ["parties"]  # Party names may contain natural person names

    @property
    def default_audit_retention_days(self) -> int:
        return 3650  # 10 years for legal documents

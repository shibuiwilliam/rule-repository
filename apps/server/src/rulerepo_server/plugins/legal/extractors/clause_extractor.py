"""Contract clause extractor — extracts standard clauses from contracts.

Parses contract documents to identify clauses, classify them by type,
and produce candidate rules representing organizational standards
for each clause type.

See: CLAUDE.md SS16.4
"""

from __future__ import annotations

import re
from typing import Any

# Common clause type patterns
_CLAUSE_TYPE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "confidentiality": [
        re.compile(r"\b(confidential|non-disclosure|nda|proprietary\s+information)\b", re.IGNORECASE),
    ],
    "indemnification": [
        re.compile(r"\b(indemnif|hold\s+harmless|defend\s+and\s+indemnify)\b", re.IGNORECASE),
    ],
    "limitation_of_liability": [
        re.compile(r"\b(limitation\s+of\s+liability|liability\s+(cap|limit)|consequential\s+damages)\b", re.IGNORECASE),
    ],
    "termination": [
        re.compile(r"\b(terminat|cancellat|right\s+to\s+terminate)\b", re.IGNORECASE),
    ],
    "governing_law": [
        re.compile(r"\b(governing\s+law|applicable\s+law|jurisdiction|venue)\b", re.IGNORECASE),
    ],
    "intellectual_property": [
        re.compile(
            r"\b(intellectual\s+property|ip\s+rights|copyright|patent|trademark|work\s+product)\b", re.IGNORECASE
        ),
    ],
    "warranty": [
        re.compile(r"\b(warrant|guarantee|representation|as[\s-]is)\b", re.IGNORECASE),
    ],
    "payment": [
        re.compile(r"\b(payment|compensation|fees|invoice|billing|net\s+\d+)\b", re.IGNORECASE),
    ],
    "non_compete": [
        re.compile(r"\b(non[\s-]?compet|restrictive\s+covenant|non[\s-]?solicitation)\b", re.IGNORECASE),
    ],
    "force_majeure": [
        re.compile(r"\b(force\s+majeure|act\s+of\s+god|unforeseeable|beyond\s+control)\b", re.IGNORECASE),
    ],
    "data_protection": [
        re.compile(r"\b(data\s+protection|personal\s+data|privacy|gdpr|appi|data\s+processing)\b", re.IGNORECASE),
    ],
    "dispute_resolution": [
        re.compile(r"\b(dispute\s+resolution|arbitration|mediation|litigation)\b", re.IGNORECASE),
    ],
    "assignment": [
        re.compile(r"\b(assign|transfer|successor|delegate)\b", re.IGNORECASE),
    ],
    "entire_agreement": [
        re.compile(r"\b(entire\s+agreement|complete\s+agreement|supersede|merger\s+clause)\b", re.IGNORECASE),
    ],
    "amendment": [
        re.compile(r"\b(amend|modif|waiver|written\s+consent)\b", re.IGNORECASE),
    ],
}

# Scope mapping for clause types
_CLAUSE_SCOPE_MAP: dict[str, list[str]] = {
    "confidentiality": ["legal/contracts/nda", "legal/confidentiality"],
    "indemnification": ["legal/contracts/liability"],
    "limitation_of_liability": ["legal/contracts/liability"],
    "termination": ["legal/contracts/termination"],
    "governing_law": ["legal/contracts/jurisdiction"],
    "intellectual_property": ["legal/ip"],
    "warranty": ["legal/contracts/warranty"],
    "payment": ["legal/contracts/payment", "finance"],
    "non_compete": ["legal/employment", "hr/compliance"],
    "force_majeure": ["legal/contracts/force-majeure"],
    "data_protection": ["legal/privacy", "compliance/data-protection"],
    "dispute_resolution": ["legal/contracts/disputes"],
    "assignment": ["legal/contracts/assignment"],
    "entire_agreement": ["legal/contracts/general"],
    "amendment": ["legal/contracts/general"],
}


def _detect_clause_type(text: str) -> str:
    """Detect the clause type from its text content.

    Args:
        text: Clause text.

    Returns:
        Clause type string, or 'general' if no specific type detected.
    """
    for clause_type, patterns in _CLAUSE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(text):
                return clause_type
    return "general"


def _split_into_clauses(text: str) -> list[dict[str, Any]]:
    """Split a contract into individual clauses.

    Detects clause boundaries from numbered sections, article headers,
    and section breaks.

    Args:
        text: Full contract text.

    Returns:
        List of clause dicts with 'text', 'heading', and 'index' keys.
    """
    clauses: list[dict[str, Any]] = []

    # Pattern for clause/section headers
    header_re = re.compile(
        r"^(?:"
        r"(?:Article|Section|Clause|Part)\s+\d+[\.:]\s*(.+)|"
        r"(\d+[\.:]\d*[\.:]*)\s*(.+)|"
        r"#{1,4}\s+(.+)"
        r")$",
        re.IGNORECASE | re.MULTILINE,
    )

    current_heading = "Preamble"
    current_lines: list[str] = []
    clause_index = 0

    for line in text.split("\n"):
        match = header_re.match(line.strip())
        if match:
            if current_lines:
                clause_text = "\n".join(current_lines).strip()
                if clause_text:
                    clauses.append(
                        {
                            "text": clause_text,
                            "heading": current_heading,
                            "index": clause_index,
                        }
                    )
                    clause_index += 1
            # Extract heading from whichever group matched
            groups = match.groups()
            current_heading = next((g for g in groups if g is not None), line.strip())
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        clause_text = "\n".join(current_lines).strip()
        if clause_text:
            clauses.append(
                {
                    "text": clause_text,
                    "heading": current_heading,
                    "index": clause_index,
                }
            )

    return clauses


def _extract_normative_statements(clause_text: str) -> list[str]:
    """Extract normative statements from a clause.

    Args:
        clause_text: Text of a single clause.

    Returns:
        List of normative statement strings.
    """
    normative_re = re.compile(
        r"\b(shall|must|will|agrees?\s+to|is\s+required\s+to|"
        r"shall\s+not|must\s+not|may\s+not|is\s+prohibited)\b",
        re.IGNORECASE,
    )

    statements: list[str] = []
    sentences = re.split(r"(?<=[.;])\s+", clause_text)

    for sentence in sentences:
        sentence = sentence.strip()
        if normative_re.search(sentence) and len(sentence) > 20:
            statements.append(sentence)

    return statements


class ClauseExtractor:
    """Extracts standard clause rules from contract documents.

    Parses contracts into individual clauses, classifies each clause
    by type, and extracts normative statements as candidate rules
    representing organizational contracting standards.
    """

    @property
    def name(self) -> str:
        return "clause_extractor"

    @property
    def domain(self) -> str:
        return "legal"

    @property
    def supported_source_types(self) -> list[str]:
        return ["pdf", "text", "contract", "docx_text"]

    async def extract(
        self,
        content: bytes,
        source_type: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract clause-based rule candidates from a contract document.

        Args:
            content: Raw bytes of the contract (text or pre-extracted PDF/DOCX text).
            source_type: Source type.
            metadata: Additional metadata (filename, contract_type, jurisdiction, ...).

        Returns:
            List of candidate rule dicts.
        """
        text = content.decode("utf-8", errors="replace")
        contract_type = metadata.get("contract_type", "general")
        jurisdiction = metadata.get("jurisdiction", "global")
        filename = metadata.get("filename", "contract")

        clauses = _split_into_clauses(text)
        candidates: list[dict[str, Any]] = []

        for clause in clauses:
            clause_type = _detect_clause_type(clause["text"])
            scopes = _CLAUSE_SCOPE_MAP.get(clause_type, ["legal/contracts"])
            normative_statements = _extract_normative_statements(clause["text"])

            for statement in normative_statements:
                # Determine modality from statement language
                lower = statement.lower()
                if any(kw in lower for kw in ("shall not", "must not", "may not", "prohibited")):
                    modality = "MUST_NOT"
                elif any(kw in lower for kw in ("shall", "must", "required")):
                    modality = "MUST"
                elif "should" in lower:
                    modality = "SHOULD"
                else:
                    modality = "MUST"

                candidates.append(
                    {
                        "statement": statement,
                        "modality": modality,
                        "severity": "HIGH"
                        if clause_type
                        in (
                            "confidentiality",
                            "limitation_of_liability",
                            "data_protection",
                            "indemnification",
                        )
                        else "MEDIUM",
                        "scope": scopes,
                        "jurisdiction": jurisdiction,
                        "legal_force": "contractual",
                        "rationale": (
                            f"Extracted from {clause_type} clause in "
                            f"{contract_type} contract '{filename}'. "
                            f"Section: {clause['heading']}."
                        ),
                        "source": {
                            "type": source_type,
                            "filename": filename,
                            "section": clause["heading"],
                            "clause_type": clause_type,
                            "clause_index": clause["index"],
                            "original_text": statement,
                        },
                        "tags": [
                            "auto-extracted",
                            "contract",
                            clause_type,
                            contract_type,
                        ],
                        "applicable_subject_types": ["clause_set", "document"],
                    }
                )

        return candidates

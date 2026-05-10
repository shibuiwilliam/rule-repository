"""Contract template extractor — identifies standard vs negotiable clauses.

Parses contract template documents (standard forms, model agreements) to
identify clauses as "standard" (always present, non-negotiable) or
"negotiable" (varies per deal), then generates MUST/SHOULD rules with
appropriate boundary conditions.

See: CLAUDE.md SS14.11, PROJECT.md SS6.4
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Clause hierarchy patterns (English + Japanese)
# ---------------------------------------------------------------------------

_ARTICLE_PATTERNS: list[re.Pattern[str]] = [
    # Japanese: 第1条, 第2条...
    re.compile(r"^第(\d+)条[\s\.\uff1a:]*(.*)$", re.MULTILINE),
    # English: Article 1, Article 2...
    re.compile(r"^Article\s+(\d+)[\s\.\uff1a:]*(.*)$", re.IGNORECASE | re.MULTILINE),
    # Numbered: 1. Title, 2. Title...
    re.compile(r"^(\d+)\.\s+(.+)$", re.MULTILINE),
    # Section headers
    re.compile(r"^Section\s+(\d+)[\s\.\uff1a:]*(.*)$", re.IGNORECASE | re.MULTILINE),
]

_SUBSECTION_PATTERNS: list[re.Pattern[str]] = [
    # Japanese: 第1項, 1項
    re.compile(r"^\s*(?:第)?(\d+)項[\s\.\uff1a:]*(.*)$", re.MULTILINE),
    # English subsections: 1.1, 1.2...
    re.compile(r"^\s*(\d+\.\d+)[\s\.]*(.*)$", re.MULTILINE),
    # Lettered subsections: (a), (b)...
    re.compile(r"^\s*\(([a-z])\)\s+(.*)$", re.MULTILINE),
]

# ---------------------------------------------------------------------------
# Standard vs Negotiable classification signals
# ---------------------------------------------------------------------------

_STANDARD_INDICATORS: list[re.Pattern[str]] = [
    re.compile(r"\b(shall\s+always|must\s+include|mandatory|non-negotiable)\b", re.IGNORECASE),
    re.compile(r"\b(required\s+in\s+all|minimum\s+requirement|standard\s+clause)\b", re.IGNORECASE),
    re.compile(r"\b(不変|必須|標準条項|変更不可)\b"),
    re.compile(r"\b(governing\s+law|dispute\s+resolution|data\s+protection)\b", re.IGNORECASE),
    re.compile(r"\b(indemnification|limitation\s+of\s+liability|confidentiality)\b", re.IGNORECASE),
]

_NEGOTIABLE_INDICATORS: list[re.Pattern[str]] = [
    re.compile(r"\b(may\s+be\s+adjusted|negotiable|subject\s+to\s+discussion)\b", re.IGNORECASE),
    re.compile(r"\b(optional|as\s+agreed|to\s+be\s+determined|TBD)\b", re.IGNORECASE),
    re.compile(r"\b(協議|調整可能|任意|別途協議)\b"),
    re.compile(r"\[[\s]*[^\]]*\s*\]", re.IGNORECASE),  # Bracketed placeholders [...]
    re.compile(r"\b(payment\s+terms|delivery\s+schedule|service\s+level)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Clause type detection (scope assignment)
# ---------------------------------------------------------------------------

_CLAUSE_TYPE_KEYWORDS: dict[str, list[re.Pattern[str]]] = {
    "confidentiality": [
        re.compile(r"\b(confidential|秘密保持|non-disclosure|NDA)\b", re.IGNORECASE),
    ],
    "indemnification": [
        re.compile(r"\b(indemnif|補償|hold\s+harmless)\b", re.IGNORECASE),
    ],
    "liability": [
        re.compile(r"\b(liability|責任|損害賠償|consequential)\b", re.IGNORECASE),
    ],
    "termination": [
        re.compile(r"\b(terminat|解除|解約|cancellation)\b", re.IGNORECASE),
    ],
    "ip_rights": [
        re.compile(r"\b(intellectual\s+property|知的財産|IP|著作権|patent)\b", re.IGNORECASE),
    ],
    "payment": [
        re.compile(r"\b(payment|支払|対価|invoice|billing)\b", re.IGNORECASE),
    ],
    "governing_law": [
        re.compile(r"\b(governing\s+law|準拠法|jurisdiction|裁判管轄)\b", re.IGNORECASE),
    ],
    "data_protection": [
        re.compile(r"\b(data\s+protection|個人情報|privacy|APPI|GDPR)\b", re.IGNORECASE),
    ],
    "non_compete": [
        re.compile(r"\b(non[\s-]?compet|競業禁止|restrictive\s+covenant)\b", re.IGNORECASE),
    ],
    "force_majeure": [
        re.compile(r"\b(force\s+majeure|不可抗力|act\s+of\s+god)\b", re.IGNORECASE),
    ],
    "warranty": [
        re.compile(r"\b(warrant|保証|guarantee|瑕疵担保)\b", re.IGNORECASE),
    ],
    "assignment": [
        re.compile(r"\b(assign|譲渡|transfer\s+of\s+rights)\b", re.IGNORECASE),
    ],
}

_SCOPE_MAP: dict[str, list[str]] = {
    "confidentiality": ["legal/contract/confidentiality"],
    "indemnification": ["legal/contract/indemnification"],
    "liability": ["legal/contract/liability"],
    "termination": ["legal/contract/termination"],
    "ip_rights": ["legal/contract/ip"],
    "payment": ["legal/contract/payment"],
    "governing_law": ["legal/contract/jurisdiction"],
    "data_protection": ["legal/contract/data-protection"],
    "non_compete": ["legal/contract/non-compete"],
    "force_majeure": ["legal/contract/force-majeure"],
    "warranty": ["legal/contract/warranty"],
    "assignment": ["legal/contract/assignment"],
}

# ---------------------------------------------------------------------------
# Boundary condition extraction
# ---------------------------------------------------------------------------

_BOUNDARY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("duration", re.compile(r"\b(\d+)\s*(years?|months?|days?|年|月|日)\b", re.IGNORECASE)),
    ("monetary_cap", re.compile(r"\b(\d[\d,]*)\s*(円|JPY|USD|\$|万円)\b", re.IGNORECASE)),
    ("percentage", re.compile(r"\b(\d+(?:\.\d+)?)\s*%\b")),
    ("notice_period", re.compile(r"\b(\d+)\s*(days?|months?|日|月)\s*(prior\s+)?notice\b", re.IGNORECASE)),
]


def _detect_clause_type(text: str) -> str:
    """Detect the clause type from text content.

    Args:
        text: Clause text content.

    Returns:
        Clause type string, or 'general' if undetected.
    """
    for clause_type, patterns in _CLAUSE_TYPE_KEYWORDS.items():
        for pattern in patterns:
            if pattern.search(text):
                return clause_type
    return "general"


def _classify_negotiability(text: str) -> str:
    """Classify a clause as standard or negotiable.

    Args:
        text: Clause text content.

    Returns:
        'standard' or 'negotiable'.
    """
    standard_score = sum(1 for p in _STANDARD_INDICATORS if p.search(text))
    negotiable_score = sum(1 for p in _NEGOTIABLE_INDICATORS if p.search(text))

    if standard_score > negotiable_score:
        return "standard"
    if negotiable_score > standard_score:
        return "negotiable"
    # Default: standard for high-risk types, negotiable otherwise
    clause_type = _detect_clause_type(text)
    if clause_type in ("confidentiality", "indemnification", "liability", "data_protection", "governing_law"):
        return "standard"
    return "negotiable"


def _extract_boundaries(text: str) -> list[dict[str, str]]:
    """Extract boundary conditions from clause text.

    Args:
        text: Clause text.

    Returns:
        List of boundary dicts with 'type' and 'value' keys.
    """
    boundaries: list[dict[str, str]] = []
    for boundary_type, pattern in _BOUNDARY_PATTERNS:
        matches = pattern.findall(text)
        for match in matches:
            value = " ".join(part for part in match if part) if isinstance(match, tuple) else match
            boundaries.append({"type": boundary_type, "value": value})
    return boundaries


def _split_template_into_clauses(text: str) -> list[dict[str, Any]]:
    """Split a contract template into clauses using hierarchy patterns.

    Args:
        text: Full template text.

    Returns:
        List of clause dicts with 'text', 'heading', 'article_number', 'index'.
    """
    # Find all article boundaries
    boundaries: list[tuple[int, str, str]] = []
    for pattern in _ARTICLE_PATTERNS:
        for match in pattern.finditer(text):
            boundaries.append((match.start(), match.group(1), match.group(2).strip()))

    boundaries.sort(key=lambda x: x[0])

    if not boundaries:
        # Fallback: treat entire text as one clause
        return [{"text": text, "heading": "Document", "article_number": "1", "index": 0}]

    clauses: list[dict[str, Any]] = []
    for i, (start, number, heading) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        clause_text = text[start:end].strip()
        clauses.append(
            {
                "text": clause_text,
                "heading": heading or f"Article {number}",
                "article_number": number,
                "index": i,
            }
        )

    return clauses


class ContractTemplateExtractor:
    """Extracts rules from contract template documents.

    Identifies standard (non-negotiable) vs negotiable clauses and
    generates MUST rules for standard clauses and SHOULD rules with
    boundary conditions for negotiable ones.
    """

    @property
    def name(self) -> str:
        return "contract_template_extractor"

    @property
    def domain(self) -> str:
        return "legal"

    @property
    def supported_source_types(self) -> list[str]:
        return ["contract_template", "standard_form", "model_agreement"]

    async def extract(
        self,
        content: bytes,
        source_type: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract rule candidates from a contract template.

        Args:
            content: Raw bytes of the template document (text/markdown).
            source_type: Source type (must be in supported_source_types).
            metadata: Additional metadata (filename, template_name, jurisdiction).

        Returns:
            List of candidate rule dicts.

        Raises:
            ValueError: If content cannot be decoded.
        """
        text = content.decode("utf-8", errors="replace")
        template_name = metadata.get("template_name", metadata.get("filename", "unknown"))
        jurisdiction = metadata.get("jurisdiction", "global")

        logger.info(
            "extracting_contract_template",
            template_name=template_name,
            source_type=source_type,
            content_length=len(text),
        )

        clauses = _split_template_into_clauses(text)
        candidates: list[dict[str, Any]] = []

        for clause in clauses:
            clause_text = clause["text"]
            clause_type = _detect_clause_type(clause_text)
            negotiability = _classify_negotiability(clause_text)
            boundaries = _extract_boundaries(clause_text)
            scope = _SCOPE_MAP.get(clause_type, ["legal/contract/general"])

            if negotiability == "standard":
                candidate = self._build_standard_rule(
                    clause=clause,
                    clause_type=clause_type,
                    scope=scope,
                    boundaries=boundaries,
                    template_name=template_name,
                    jurisdiction=jurisdiction,
                )
            else:
                candidate = self._build_negotiable_rule(
                    clause=clause,
                    clause_type=clause_type,
                    scope=scope,
                    boundaries=boundaries,
                    template_name=template_name,
                    jurisdiction=jurisdiction,
                )

            candidates.append(candidate)

        logger.info(
            "contract_template_extraction_complete",
            template_name=template_name,
            total_clauses=len(clauses),
            candidates_generated=len(candidates),
        )

        return candidates

    def _build_standard_rule(
        self,
        clause: dict[str, Any],
        clause_type: str,
        scope: list[str],
        boundaries: list[dict[str, str]],
        template_name: str,
        jurisdiction: str,
    ) -> dict[str, Any]:
        """Build a MUST rule for a standard (non-negotiable) clause.

        Args:
            clause: Parsed clause dict.
            clause_type: Detected clause type.
            scope: Scope list for the rule.
            boundaries: Extracted boundary conditions.
            template_name: Name of the source template.
            jurisdiction: Applicable jurisdiction.

        Returns:
            Candidate rule dict.
        """
        protection_summary = self._summarize_protections(clause["text"], boundaries)
        statement = f"Contract must include {clause_type.replace('_', ' ')} clause with {protection_summary}"

        return {
            "statement": statement,
            "modality": "MUST",
            "severity": "HIGH",
            "scope": scope,
            "applicable_subject_types": ["clause_set"],
            "tags": ["auto-extracted", "contract-template", "standard-clause", clause_type],
            "rationale": (
                f"Standard non-negotiable clause from template '{template_name}'. "
                f"Article {clause['article_number']}: {clause['heading']}. "
                f"Jurisdiction: {jurisdiction}."
            ),
            "preconditions": [
                f"Contract is subject to {jurisdiction} jurisdiction",
                f"Template: {template_name}",
            ],
            "source": {
                "type": "contract_template",
                "template_name": template_name,
                "article_number": clause["article_number"],
                "heading": clause["heading"],
                "clause_type": clause_type,
                "negotiability": "standard",
            },
            "boundaries": boundaries,
        }

    def _build_negotiable_rule(
        self,
        clause: dict[str, Any],
        clause_type: str,
        scope: list[str],
        boundaries: list[dict[str, str]],
        template_name: str,
        jurisdiction: str,
    ) -> dict[str, Any]:
        """Build a SHOULD rule with boundary conditions for a negotiable clause.

        Args:
            clause: Parsed clause dict.
            clause_type: Detected clause type.
            scope: Scope list for the rule.
            boundaries: Extracted boundary conditions.
            template_name: Name of the source template.
            jurisdiction: Applicable jurisdiction.

        Returns:
            Candidate rule dict.
        """
        boundary_desc = self._describe_boundaries(boundaries)
        statement = f"Contract should include {clause_type.replace('_', ' ')} clause"
        if boundary_desc:
            statement += f" within boundaries: {boundary_desc}"

        return {
            "statement": statement,
            "modality": "SHOULD",
            "severity": "MEDIUM",
            "scope": scope,
            "applicable_subject_types": ["clause_set"],
            "tags": ["auto-extracted", "contract-template", "negotiable-clause", clause_type],
            "rationale": (
                f"Negotiable clause from template '{template_name}'. "
                f"Article {clause['article_number']}: {clause['heading']}. "
                f"Terms may be adjusted within stated boundaries. "
                f"Jurisdiction: {jurisdiction}."
            ),
            "preconditions": [
                f"Contract is subject to {jurisdiction} jurisdiction",
                f"Template: {template_name}",
            ],
            "source": {
                "type": "contract_template",
                "template_name": template_name,
                "article_number": clause["article_number"],
                "heading": clause["heading"],
                "clause_type": clause_type,
                "negotiability": "negotiable",
            },
            "boundaries": boundaries,
        }

    @staticmethod
    def _summarize_protections(text: str, boundaries: list[dict[str, str]]) -> str:
        """Summarize minimum protections from clause text and boundaries.

        Args:
            text: Clause text.
            boundaries: Extracted boundaries.

        Returns:
            Human-readable protection summary.
        """
        parts: list[str] = []

        for boundary in boundaries:
            if boundary["type"] == "duration":
                parts.append(f"duration limit of {boundary['value']}")
            elif boundary["type"] == "monetary_cap":
                parts.append(f"cap of {boundary['value']}")
            elif boundary["type"] == "notice_period":
                parts.append(f"notice period of {boundary['value']}")
            elif boundary["type"] == "percentage":
                parts.append(f"threshold of {boundary['value']}%")

        if not parts:
            parts.append("minimum required protections as specified")

        return "; ".join(parts)

    @staticmethod
    def _describe_boundaries(boundaries: list[dict[str, str]]) -> str:
        """Describe boundary conditions in human-readable form.

        Args:
            boundaries: Extracted boundaries.

        Returns:
            Description string, or empty if no boundaries.
        """
        if not boundaries:
            return ""

        descriptions: list[str] = []
        for boundary in boundaries:
            descriptions.append(f"{boundary['type']}: {boundary['value']}")
        return ", ".join(descriptions)

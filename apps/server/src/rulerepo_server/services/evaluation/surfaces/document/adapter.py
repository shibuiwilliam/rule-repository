"""Document surface adapter — evaluates documents and policies.

Handles internal policies, compliance documents, governance disclosures,
and other organizational documents. See CLAUDE.md §14.2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rulerepo_server.domain.evaluation import Surface
from rulerepo_server.services.evaluation.surfaces.base import (
    EvaluationSubjectPayload,
    SurfaceAdapter,
)

_HINTS_FILE = Path(__file__).parent / "prompts" / "document_hints.txt"


class DocumentSurfaceAdapter(SurfaceAdapter):
    """Surface adapter for document and policy evaluation.

    Handles internal policies, compliance documents, governance disclosures,
    reports, and other organizational documents subject to normative rules.
    """

    @property
    def surface(self) -> Surface:
        return Surface.DOCUMENT

    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a document evaluation request into a uniform subject.

        Expected payload keys:
            - content: str — the document text or section content
            - document_type: str (e.g., "policy", "disclosure", "report")
            - title: str — document title
            - section: str — section identifier or heading
            - author: str — document author
            - facts: dict — additional structured facts

        Returns:
            EvaluationSubjectPayload with document-specific fields.
        """
        content = payload.get("content", "")
        document_type = payload.get("document_type", "general")
        title = payload.get("title", "Untitled")
        section = payload.get("section", "")
        author = payload.get("author", "")

        description = f"Document ({document_type}): {title}"
        if section:
            description += f" — Section: {section}"
        description += f"\n\n{content}"

        facts = dict(payload.get("facts", {}))
        if author:
            facts["author"] = author
        facts["document_type"] = document_type

        section_part = f"/section:{section}" if section else ""
        identifier = f"document:{document_type}/{title}{section_part}"

        return EvaluationSubjectPayload(
            surface=Surface.DOCUMENT,
            identifier=identifier,
            description=description,
            payload={
                "content": content,
                "document_type": document_type,
                "title": title,
                "section": section,
                "author": author,
            },
            facts=facts,
            locale=payload.get("locale", "en"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from document type."""
        scopes: set[str] = set()

        document_type = payload.get("document_type", "")
        if "policy" in document_type:
            scopes.add("compliance/policy")
        elif "disclosure" in document_type:
            scopes.add("governance/disclosure")
        elif "report" in document_type:
            scopes.add("governance/report")
        elif "regulation" in document_type:
            scopes.add("compliance/regulation")

        return sorted(scopes) if scopes else ["governance/document"]

    def get_prompt_hints(self) -> str:
        """Return document-specific prompt hints."""
        if _HINTS_FILE.exists():
            return _HINTS_FILE.read_text()
        return (
            "You are evaluating an organizational document for compliance with "
            "governance standards, disclosure requirements, and internal policies. "
            "Focus on completeness, accuracy, required sections, proper approvals, "
            "and regulatory alignment. Suggest specific textual corrections where "
            "applicable."
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        return ["facts.author"]

    @property
    def default_audit_retention_days(self) -> int:
        return 3650  # 10 years for governance documents

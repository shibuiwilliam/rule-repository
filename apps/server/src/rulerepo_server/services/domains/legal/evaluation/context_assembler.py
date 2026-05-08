"""Legal context assembler — transforms contract artifacts into LLM-ready text."""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class LegalContextAssembler:
    """Assembles LLM-ready context from legal artifacts.

    Handles:
    - contract_clause: individual clause text with parties and metadata
    - contract_document: full document with structure
    """

    async def assemble(self, evaluable: dict[str, Any]) -> str:
        artifact_type = evaluable.get("artifact_type", "contract_clause")
        payload = evaluable.get("payload", {})
        metadata = evaluable.get("metadata", {})

        parts: list[str] = []

        # Add metadata context
        if parties := metadata.get("parties"):
            parts.append(f"Parties: {', '.join(parties) if isinstance(parties, list) else parties}")
        if contract_type := metadata.get("contract_type"):
            parts.append(f"Contract Type: {contract_type}")
        if jurisdiction := metadata.get("jurisdiction"):
            parts.append(f"Jurisdiction: {jurisdiction}")
        if governing_law := metadata.get("governing_law"):
            parts.append(f"Governing Law: {governing_law}")

        # Add the artifact content
        if artifact_type == "contract_clause":
            if clause_title := payload.get("clause_title"):
                parts.append(f"Clause Title: {clause_title}")
            if clause_text := payload.get("clause_text", payload.get("clause", "")):
                parts.append(f"\n--- CLAUSE TEXT ---\n{clause_text}")
            if redline := payload.get("redline"):
                parts.append(f"\n--- REDLINE CHANGES ---\n{redline}")

        elif artifact_type == "contract_document":
            if document_text := payload.get("document_text", payload.get("document", "")):
                parts.append(f"\n--- DOCUMENT ---\n{document_text}")
            if summary := payload.get("summary"):
                parts.append(f"\nSummary: {summary}")

        else:
            # Fallback for unknown types
            parts.append(str(payload))

        context = "\n".join(parts)
        logger.debug("legal_context_assembled", artifact_type=artifact_type, length=len(context))
        return context

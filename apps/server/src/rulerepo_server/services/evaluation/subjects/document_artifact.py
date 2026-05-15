"""Context assembler for DocumentArtifactSubject.

Extracts context from documents and document sections under review,
such as contracts, marketing assets, and policy drafts.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation_subject import DocumentArtifactSubject


async def assemble_context(subject: DocumentArtifactSubject) -> dict[str, Any]:
    """Assemble evaluation context from a document artifact subject."""
    context: dict[str, Any] = {
        "kind": "document_artifact",
        "document_id": subject.document_id,
        "sections": subject.sections,
        "intent": subject.intent,
    }
    if subject.actor_id:
        context["actor_id"] = subject.actor_id
    if subject.metadata:
        context["metadata"] = subject.metadata
    return context

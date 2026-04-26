"""REST API routes for document upload and rule extraction."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.files.storage import LocalFileStorage
from rulerepo_server.adapters.gemini.client import get_gemini_client
from rulerepo_server.adapters.postgres.models import DocumentModel, ExtractionModel
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.deps import get_rule_service
from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.extraction import CandidateReviewRequest
from rulerepo_server.schemas.rule import RuleCreate
from rulerepo_server.services.extraction.pipeline import ExtractionPipeline
from rulerepo_server.services.rule_service import RuleService

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Upload a document for rule extraction."""
    file_bytes = await file.read()
    filename = file.filename or "unnamed"
    mime_type = file.content_type or "application/octet-stream"

    storage = LocalFileStorage()
    doc_id = await storage.store(file_bytes, filename, mime_type)

    doc_model = DocumentModel(
        id=uuid4(),
        filename=filename,
        mime_type=mime_type,
        size_bytes=len(file_bytes),
        storage_path=storage.get_storage_path(doc_id),
        uploaded_at=datetime.now(timezone.utc),
    )
    session.add(doc_model)
    await session.flush()

    return {
        "document_id": str(doc_model.id),
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": len(file_bytes),
        "uploaded_at": doc_model.uploaded_at,
    }


@router.post("/{document_id}/extract")
async def extract_rules(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Trigger rule extraction on an uploaded document."""
    # Load document
    result = await session.execute(select(DocumentModel).where(DocumentModel.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFoundError("Document", str(document_id))

    # Read file
    storage = LocalFileStorage()
    file_bytes, _ = await storage.retrieve(str(doc.id))

    # Run extraction with audit logging (CLAUDE.md §9.6)
    try:
        from rulerepo_server.adapters.postgres.audit_repo import AuditLogRepository

        gemini = get_gemini_client()
        audit_repo = AuditLogRepository(session)
        pipeline = ExtractionPipeline(gemini, audit_repo=audit_repo)
        extraction_result = await pipeline.extract_from_document(
            file_bytes, doc.mime_type, doc.filename, document_id=str(document_id)
        )
    except Exception as exc:
        logger.warning("extraction_failed", document_id=str(document_id), error=str(exc))
        extraction_result = {
            "extraction_id": str(uuid4()),
            "candidates": [],
            "model_id": "unavailable",
        }

    # Store extraction result
    extraction = ExtractionModel(
        id=UUID(extraction_result["extraction_id"]),
        document_id=document_id,
        candidates=extraction_result["candidates"],
        model_id=extraction_result["model_id"],
        status="PENDING_REVIEW",
    )
    session.add(extraction)
    await session.flush()

    return {
        "extraction_id": str(extraction.id),
        "document_id": str(document_id),
        "candidates": extraction_result["candidates"],
        "model_id": extraction_result["model_id"],
        "extracted_at": extraction.extracted_at,
    }


@router.get("/extractions/{extraction_id}")
async def get_extraction(
    extraction_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get extraction results by ID."""
    result = await session.execute(
        select(ExtractionModel).where(ExtractionModel.id == extraction_id)
    )
    extraction = result.scalar_one_or_none()
    if extraction is None:
        raise NotFoundError("Extraction", str(extraction_id))

    return {
        "extraction_id": str(extraction.id),
        "document_id": str(extraction.document_id),
        "candidates": extraction.candidates,
        "model_id": extraction.model_id,
        "status": extraction.status,
        "extracted_at": extraction.extracted_at,
    }


@router.post("/extractions/{extraction_id}/review")
async def review_extraction(
    extraction_id: UUID,
    review: CandidateReviewRequest,
    session: AsyncSession = Depends(get_db_session),
    rule_service: RuleService = Depends(get_rule_service),
) -> dict:
    """Review extraction results — approve or edit candidates to create rules."""
    result = await session.execute(
        select(ExtractionModel).where(ExtractionModel.id == extraction_id)
    )
    extraction = result.scalar_one_or_none()
    if extraction is None:
        raise NotFoundError("Extraction", str(extraction_id))

    candidates = extraction.candidates
    created_rules = []

    # Process approved candidates as-is
    for idx in review.approved_indices:
        if idx < len(candidates):
            candidate = candidates[idx]
            rule_data = RuleCreate(
                statement=candidate["statement"],
                modality=candidate.get("modality", "MUST"),
                severity=candidate.get("severity", "MEDIUM"),
                scope=candidate.get("scope", []),
                tags=candidate.get("tags", []),
                rationale=candidate.get("rationale", ""),
            )
            rule = await rule_service.create_rule(rule_data, actor="extraction_pipeline")
            created_rules.append(rule)

    # Process edited candidates
    for idx_str, edit in review.edits.items():
        rule = await rule_service.create_rule(edit, actor="extraction_pipeline")
        created_rules.append(rule)

    # Update extraction status
    extraction.status = "REVIEWED"
    await session.flush()

    return {
        "extraction_id": str(extraction_id),
        "status": "REVIEWED",
        "rules_created": len(created_rules),
        "rule_ids": [r["id"] for r in created_rules],
    }

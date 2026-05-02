"""REST API routes for document upload and rule extraction."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.files.storage import LocalFileStorage
from rulerepo_server.adapters.gemini.client import get_gemini_client
from rulerepo_server.adapters.postgres.models import DocumentModel, ExtractionModel
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.deps import get_rule_service
from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.rule import RuleStatus
from rulerepo_server.schemas.extraction import CandidateReviewRequest
from rulerepo_server.schemas.rule import RuleCreate, SourceRefSchema
from rulerepo_server.services.extraction.pipeline import ExtractionPipeline
from rulerepo_server.services.rule_service import RuleService

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """List all registered documents with pagination."""
    from sqlalchemy import func

    offset = (page - 1) * page_size
    query = select(DocumentModel).order_by(DocumentModel.uploaded_at.desc())
    if project_id:
        query = query.where(DocumentModel.project_id == project_id)
    query = query.offset(offset).limit(page_size)
    result = await session.execute(query)
    docs = list(result.scalars().all())

    count_query = select(func.count()).select_from(DocumentModel)
    if project_id:
        count_query = count_query.where(DocumentModel.project_id == project_id)
    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    return {
        "items": [
            {
                "id": str(d.id),
                "filename": d.filename,
                "mime_type": d.mime_type,
                "size_bytes": d.size_bytes,
                "uploaded_at": d.uploaded_at,
                "uploaded_by": d.uploaded_by,
            }
            for d in docs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{document_id}")
async def get_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get a single document's metadata and content."""
    result = await session.execute(select(DocumentModel).where(DocumentModel.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFoundError("Document", str(document_id))

    # Try to read text content from storage
    content_text: str | None = None
    if hasattr(doc, "content_text") and doc.content_text:
        content_text = doc.content_text
    elif doc.mime_type in ("text/plain", "text/markdown", "application/octet-stream"):
        try:
            storage = LocalFileStorage()
            file_bytes, _ = await storage.retrieve(str(doc.id))
            content_text = file_bytes.decode("utf-8", errors="replace")
        except Exception:
            pass

    # Get extractions for this document
    ext_result = await session.execute(
        select(ExtractionModel)
        .where(ExtractionModel.document_id == document_id)
        .order_by(ExtractionModel.extracted_at.desc())
    )
    extractions = list(ext_result.scalars().all())

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "mime_type": doc.mime_type,
        "size_bytes": doc.size_bytes,
        "uploaded_at": doc.uploaded_at,
        "uploaded_by": doc.uploaded_by,
        "content_text": content_text,
        "extractions": [
            {
                "id": str(e.id),
                "status": e.status,
                "model_id": e.model_id,
                "candidates_count": len(e.candidates) if e.candidates else 0,
                "extracted_at": e.extracted_at,
            }
            for e in extractions
        ],
    }


@router.post("/upload")
async def upload_document(
    file: UploadFile,
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Upload a document for rule extraction."""
    file_bytes = await file.read()
    filename = file.filename or "unnamed"
    mime_type = file.content_type or "application/octet-stream"

    storage = LocalFileStorage()
    doc_id = await storage.store(file_bytes, filename, mime_type)

    # Extract text content for searchability (text/markdown stored directly,
    # PDFs could be OCR'd later — for now store None for binary formats)
    content_text: str | None = None
    text_types = ("text/plain", "text/markdown", "text/x-markdown", "application/octet-stream")
    text_extensions = (".md", ".txt", ".markdown", ".rst")
    if mime_type in text_types or any(filename.lower().endswith(ext) for ext in text_extensions):
        try:
            content_text = file_bytes.decode("utf-8", errors="replace")
        except Exception:
            pass

    from rulerepo_server.adapters.postgres.models import DEFAULT_PROJECT_ID

    doc_model = DocumentModel(
        id=UUID(doc_id),
        project_id=project_id or DEFAULT_PROJECT_ID,
        filename=filename,
        mime_type=mime_type,
        size_bytes=len(file_bytes),
        storage_path=storage.get_storage_path(doc_id),
        uploaded_at=datetime.now(UTC),
        content_text=content_text,
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
    result = await session.execute(select(ExtractionModel).where(ExtractionModel.id == extraction_id))
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
    result = await session.execute(select(ExtractionModel).where(ExtractionModel.id == extraction_id))
    extraction = result.scalar_one_or_none()
    if extraction is None:
        raise NotFoundError("Extraction", str(extraction_id))

    candidates = extraction.candidates
    created_rules = []

    # Load the document to inherit its project_id
    doc_result = await session.execute(select(DocumentModel).where(DocumentModel.id == extraction.document_id))
    document = doc_result.scalar_one_or_none()
    doc_project_id = str(document.project_id) if document else None

    # Process approved candidates — mark as APPROVED since human explicitly approved
    for idx in review.approved_indices:
        if idx < len(candidates):
            candidate = candidates[idx]
            source_ref = {
                "document_id": str(extraction.document_id),
                "section": candidate.get("source_section", ""),
                "page": candidate.get("source_page"),
            }
            rule_data = RuleCreate(
                statement=candidate["statement"],
                modality=candidate.get("modality", "MUST"),
                severity=candidate.get("severity", "MEDIUM"),
                status=RuleStatus.APPROVED,
                scope=candidate.get("scope", []),
                tags=candidate.get("tags", []),
                rationale=candidate.get("rationale", ""),
                context=candidate.get("context", ""),
                preconditions=candidate.get("preconditions", []),
                exceptions=candidate.get("exceptions", []),
                following_examples=candidate.get("following_examples", []),
                violation_examples=candidate.get("violation_examples", []),
                source_refs=[SourceRefSchema(**source_ref)],
            )
            rule = await rule_service.create_rule(rule_data, actor="extraction_pipeline", project_id=doc_project_id)
            created_rules.append(rule)

    # Process edited candidates — also mark as APPROVED
    for _idx_str, edit in review.edits.items():
        edit.status = RuleStatus.APPROVED  # type: ignore[assignment]
        rule = await rule_service.create_rule(edit, actor="extraction_pipeline", project_id=doc_project_id)
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

"""REST API routes for search operations."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import DocumentModel, RuleModel
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.deps import get_search_service
from rulerepo_server.schemas.search import (
    CategorySearchQuery,
    ContextSearchQuery,
    DocumentSearchQuery,
    SearchQuery,
    SourceDocSearchQuery,
)
from rulerepo_server.services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/fulltext")
async def fulltext_search(
    query: SearchQuery,
    project_id: str | None = Query(default=None),
    service: SearchService = Depends(get_search_service),
) -> dict:
    """BM25 full-text search over rule statements."""
    filters = _build_filters(query)
    if project_id:
        filters["project_id"] = project_id
    return await service.fulltext_search(query.query, filters=filters, page=query.page, page_size=query.page_size)


@router.post("/vector")
async def vector_search(
    query: SearchQuery,
    project_id: str | None = Query(default=None),
    service: SearchService = Depends(get_search_service),
) -> dict:
    """Semantic similarity search using embeddings."""
    filters = _build_filters(query)
    if project_id:
        filters["project_id"] = project_id
    return await service.vector_search(query.query, filters=filters, page=query.page, page_size=query.page_size)


@router.post("/hybrid")
async def hybrid_search(
    query: SearchQuery,
    project_id: str | None = Query(default=None),
    service: SearchService = Depends(get_search_service),
) -> dict:
    """Combined BM25 + vector hybrid search."""
    filters = _build_filters(query)
    if project_id:
        filters["project_id"] = project_id
    return await service.hybrid_search(query.query, filters=filters, page=query.page, page_size=query.page_size)


@router.post("/category")
async def category_search(
    query: CategorySearchQuery,
    project_id: str | None = Query(default=None),
    service: SearchService = Depends(get_search_service),
) -> dict:
    """Filter-only search by category fields (no free-text query)."""
    filters: dict = {}
    if query.modality:
        filters["modality"] = query.modality.value
    if query.severity:
        filters["severity"] = query.severity.value
    if query.status:
        filters["status"] = query.status
    if query.scope:
        filters["scope"] = query.scope
    if query.tags:
        filters["tags"] = query.tags
    if project_id:
        filters["project_id"] = project_id
    return await service.category_search(filters=filters, page=query.page, page_size=query.page_size)


@router.post("/context")
async def context_search(
    query: ContextSearchQuery,
    project_id: str | None = Query(default=None),
    service: SearchService = Depends(get_search_service),
) -> dict:
    """Context search — given facts about a situation, find applicable rules.

    PROJECT.md §6.1: "given a body of facts, return applicable rules."
    """
    return await service.context_search(
        query.facts,
        scope=query.scope,
        page=query.page,
        page_size=query.page_size,
        project_id=project_id,
    )


@router.post("/documents")
async def document_search(
    query: DocumentSearchQuery,
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Search documents by filename and content using PostgreSQL full-text search.

    Uses ts_rank over a tsvector of (filename || content_text) for relevance scoring.
    Falls back to ILIKE on filename if the full-text index misses.
    """

    search_term = query.query.strip()
    tsquery = " & ".join(search_term.split())  # "code conduct" → "code & conduct"

    # Full-text search with ts_rank for scoring
    rank_expr = func.ts_rank(
        func.to_tsvector(
            "english",
            func.coalesce(DocumentModel.filename, "") + " " + func.coalesce(DocumentModel.content_text, ""),
        ),
        func.to_tsquery("english", tsquery),
    )

    # Also match via ILIKE as fallback (catches partial matches ts misses)
    ilike_pattern = f"%{search_term}%"
    search_conditions = sa.or_(
        func.to_tsvector(
            "english",
            func.coalesce(DocumentModel.filename, "") + " " + func.coalesce(DocumentModel.content_text, ""),
        ).op("@@")(func.to_tsquery("english", tsquery)),
        DocumentModel.filename.ilike(ilike_pattern),
        DocumentModel.content_text.ilike(ilike_pattern) if True else sa.false(),
    )

    # Build final where clause with optional project_id filter
    conditions = [search_conditions]
    if project_id:
        conditions.append(DocumentModel.project_id == project_id)
    where_clause = sa.and_(*conditions)

    count_result = await session.execute(select(func.count()).select_from(DocumentModel).where(where_clause))
    total = count_result.scalar_one()

    offset = (query.page - 1) * query.page_size
    result = await session.execute(
        select(DocumentModel, rank_expr.label("rank"))
        .where(where_clause)
        .order_by(rank_expr.desc(), DocumentModel.uploaded_at.desc())
        .offset(offset)
        .limit(query.page_size)
    )
    rows = result.all()

    # For each document, count how many rules were extracted from it
    items = []
    for row in rows:
        doc = row[0]
        rank = row[1]

        # Count rules that reference this document
        rule_count_result = await session.execute(
            select(func.count())
            .select_from(RuleModel)
            .where(RuleModel.source_refs.contains([{"document_id": str(doc.id)}]))
        )
        rules_extracted = rule_count_result.scalar_one()

        # Build content snippet (first 300 chars of content_text)
        snippet = ""
        if doc.content_text:
            snippet = doc.content_text[:300].replace("\n", " ").strip()
            if len(doc.content_text) > 300:
                snippet += "..."

        items.append(
            {
                "id": str(doc.id),
                "filename": doc.filename,
                "mime_type": doc.mime_type,
                "size_bytes": doc.size_bytes,
                "uploaded_at": doc.uploaded_at,
                "uploaded_by": doc.uploaded_by,
                "content_snippet": snippet,
                "rules_extracted": rules_extracted,
                "relevance": round(float(rank), 4),
            }
        )

    return {
        "items": items,
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "query": query.query,
    }


@router.post("/by-source-document")
async def search_rules_by_source_document(
    query: SourceDocSearchQuery,
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Find all rules extracted from a specific source document.

    Searches the rules table for rules whose source_refs JSONB array
    contains an entry with the given document_id. Also returns the
    source document metadata.
    """
    containment = [{"document_id": query.document_id}]

    # Fetch the source document info
    doc_result = await session.execute(select(DocumentModel).where(DocumentModel.id == UUID(query.document_id)))
    source_doc = doc_result.scalar_one_or_none()
    doc_info = None
    if source_doc:
        doc_info = {
            "id": str(source_doc.id),
            "filename": source_doc.filename,
            "mime_type": source_doc.mime_type,
            "size_bytes": source_doc.size_bytes,
            "uploaded_at": source_doc.uploaded_at,
        }

    # Build filter conditions
    conditions = [RuleModel.source_refs.contains(containment)]
    if project_id:
        conditions.append(RuleModel.project_id == project_id)
    where = sa.and_(*conditions)

    count_result = await session.execute(select(func.count()).select_from(RuleModel).where(where))
    total = count_result.scalar_one()

    offset = (query.page - 1) * query.page_size
    result = await session.execute(
        select(RuleModel).where(where).order_by(RuleModel.created_at.desc()).offset(offset).limit(query.page_size)
    )
    rules = list(result.scalars().all())

    return {
        "source_document": doc_info,
        "items": [
            {
                "rule": {
                    "id": str(r.id),
                    "statement": r.statement,
                    "modality": r.modality,
                    "severity": r.severity,
                    "status": r.status,
                    "scope": r.scope,
                    "tags": r.tags,
                    "rationale": r.rationale,
                    "source_refs": r.source_refs,
                    "created_at": r.created_at,
                },
                "score": 1.0,
            }
            for r in rules
        ],
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "query": query.document_id,
    }


def _build_filters(query: SearchQuery) -> dict:
    """Build ES filter dict from search query parameters."""
    filters: dict = {}
    if query.modality:
        filters["modality"] = query.modality.value
    if query.severity:
        filters["severity"] = query.severity.value
    if query.scope:
        filters["scope"] = query.scope
    if query.tags:
        filters["tags"] = query.tags
    return filters

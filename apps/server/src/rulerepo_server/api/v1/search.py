"""REST API routes for search operations."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import DocumentModel, RuleModel
from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.deps import get_search_service
from rulerepo_server.schemas.search import (
    CategorySearchQuery,
    ContextSearchQuery,
    DocumentSearchModeQuery,
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
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    service: SearchService = Depends(get_search_service),
) -> dict:
    """BM25 full-text search over rule statements."""
    filters = _build_filters(query, accept_language)
    if project_id:
        filters["project_id"] = project_id
    return await service.fulltext_search(query.query, filters=filters, page=query.page, page_size=query.page_size)


@router.post("/vector")
async def vector_search(
    query: SearchQuery,
    project_id: str | None = Query(default=None),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    service: SearchService = Depends(get_search_service),
) -> dict:
    """Semantic similarity search using embeddings."""
    filters = _build_filters(query, accept_language)
    if project_id:
        filters["project_id"] = project_id
    return await service.vector_search(query.query, filters=filters, page=query.page, page_size=query.page_size)


@router.post("/hybrid")
async def hybrid_search(
    query: SearchQuery,
    project_id: str | None = Query(default=None),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
    service: SearchService = Depends(get_search_service),
) -> dict:
    """Combined BM25 + vector hybrid search."""
    filters = _build_filters(query, accept_language)
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


@router.post("/documents/fulltext")
async def search_documents_fulltext(
    body: DocumentSearchModeQuery,
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Full-text BM25 search on document filenames and content."""
    from rulerepo_server.adapters.elasticsearch.client import get_es_client
    from rulerepo_server.adapters.elasticsearch.document_index import ElasticsearchDocumentIndex

    es_doc_index = ElasticsearchDocumentIndex(get_es_client())
    filters = {}
    if project_id:
        filters["project_id"] = project_id

    hits, total = await es_doc_index.search_fulltext(
        body.query,
        filters=filters,
        page=body.page,
        page_size=body.page_size,
    )
    items = _build_document_results(hits)
    return {"items": items, "total": total, "page": body.page, "page_size": body.page_size, "query": body.query}


@router.post("/documents/vector")
async def search_documents_vector(
    body: DocumentSearchModeQuery,
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Semantic vector search on document embeddings."""
    from rulerepo_server.adapters.elasticsearch.client import get_es_client
    from rulerepo_server.adapters.elasticsearch.document_index import ElasticsearchDocumentIndex
    from rulerepo_server.adapters.gemini.embeddings import generate_embedding
    from rulerepo_server.core.deps import _get_optional_gemini

    gemini = _get_optional_gemini()
    if not gemini:
        return {
            "items": [],
            "total": 0,
            "page": body.page,
            "page_size": body.page_size,
            "query": body.query,
            "error": "Gemini unavailable for vector search",
        }

    embedding = await generate_embedding(gemini, body.query)
    es_doc_index = ElasticsearchDocumentIndex(get_es_client())
    filters = {}
    if project_id:
        filters["project_id"] = project_id

    hits, total = await es_doc_index.search_vector(
        embedding,
        filters=filters,
        page=body.page,
        page_size=body.page_size,
    )
    items = _build_document_results(hits)
    return {"items": items, "total": total, "page": body.page, "page_size": body.page_size, "query": body.query}


@router.post("/documents/hybrid")
async def search_documents_hybrid(
    body: DocumentSearchModeQuery,
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Hybrid BM25 + vector search on documents."""
    from rulerepo_server.adapters.elasticsearch.client import get_es_client
    from rulerepo_server.adapters.elasticsearch.document_index import ElasticsearchDocumentIndex
    from rulerepo_server.adapters.gemini.embeddings import generate_embedding
    from rulerepo_server.core.deps import _get_optional_gemini

    gemini = _get_optional_gemini()
    embedding = []
    if gemini:
        try:
            embedding = await generate_embedding(gemini, body.query)
        except Exception:
            pass

    es_doc_index = ElasticsearchDocumentIndex(get_es_client())
    filters = {}
    if project_id:
        filters["project_id"] = project_id

    if embedding:
        hits, total = await es_doc_index.search_hybrid(
            body.query,
            embedding,
            filters=filters,
            page=body.page,
            page_size=body.page_size,
        )
    else:
        hits, total = await es_doc_index.search_fulltext(
            body.query,
            filters=filters,
            page=body.page,
            page_size=body.page_size,
        )
    items = _build_document_results(hits)
    return {"items": items, "total": total, "page": body.page, "page_size": body.page_size, "query": body.query}


def _build_document_results(hits: list[tuple[str, float, dict]]) -> list[dict]:
    """Convert ES hits to API response items."""
    items = []
    for doc_id, score, source in hits:
        highlight = source.pop("highlight", {})
        snippet = ""
        if "content_text" in highlight:
            snippet = " ... ".join(highlight["content_text"])
        elif source.get("content_text"):
            snippet = source["content_text"][:300]

        items.append(
            {
                "document_id": doc_id,
                "filename": source.get("filename", ""),
                "mime_type": source.get("mime_type", ""),
                "size_bytes": source.get("size_bytes", 0),
                "uploaded_by": source.get("uploaded_by", ""),
                "uploaded_at": source.get("uploaded_at", ""),
                "snippet": snippet,
                "score": score,
            }
        )
    return items


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


@router.post("/temporal")
async def temporal_search(
    as_of: str = Query(..., description="ISO 8601 timestamp — return rules effective at this time"),
    q: str = Query(default="", description="Optional text query"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Search for rules effective at a given timestamp."""
    from datetime import datetime as dt

    try:
        ts = dt.fromisoformat(as_of.replace("Z", "+00:00"))
    except ValueError:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "query": as_of,
            "error": "Invalid timestamp",
        }

    stmt = (
        select(RuleModel)
        .where(RuleModel.status.in_(["EFFECTIVE", "APPROVED"]))
        .where(
            sa.or_(
                RuleModel.effective_period["valid_from"].astext.cast(sa.DateTime) <= ts,
                RuleModel.effective_period["valid_from"].is_(sa.null()),
            )
        )
    )
    if project_id:
        stmt = stmt.where(RuleModel.project_id == project_id)
    if q:
        stmt = stmt.where(RuleModel.statement.ilike(f"%{q}%"))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(stmt)
    rules = list(result.scalars().all())
    return {
        "items": [{"rule": {"id": str(r.id), "statement": r.statement, "scope": r.scope}, "score": 1.0} for r in rules],
        "total": len(rules),
        "page": page,
        "page_size": page_size,
        "query": as_of,
    }


@router.post("/citation")
async def citation_search(
    source: str = Query(..., description="External source identifier to search for"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Search for rules referencing a particular external source."""
    stmt = select(RuleModel).where(RuleModel.source_refs.cast(sa.Text).ilike(f"%{source}%"))
    if project_id:
        stmt = stmt.where(RuleModel.project_id == project_id)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(stmt)
    rules = list(result.scalars().all())
    return {
        "items": [
            {"rule": {"id": str(r.id), "statement": r.statement, "source_refs": r.source_refs}, "score": 1.0}
            for r in rules
        ],
        "total": len(rules),
        "page": page,
        "page_size": page_size,
        "query": source,
    }


@router.post("/subject")
async def subject_search(
    role: str | None = Query(default=None),
    location: str | None = Query(default=None),
    employment_type: str | None = Query(default=None),
    department: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Search for rules applicable to a specific subject profile."""
    stmt = select(RuleModel).where(RuleModel.status.in_(["EFFECTIVE", "APPROVED"]))
    if project_id:
        stmt = stmt.where(RuleModel.project_id == project_id)

    # Filter by scope patterns matching subject fields
    scope_patterns = []
    if role:
        scope_patterns.append(f"%{role}%")
    if location:
        scope_patterns.append(f"%{location}%")
    if department:
        scope_patterns.append(f"%{department}%")
    if employment_type:
        scope_patterns.append(f"%{employment_type}%")

    if scope_patterns:
        conditions = [RuleModel.scope.cast(sa.Text).ilike(p) for p in scope_patterns]
        stmt = stmt.where(sa.or_(*conditions))

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    rules = list(result.scalars().all())
    return {
        "items": [{"rule": {"id": str(r.id), "statement": r.statement, "scope": r.scope}, "score": 1.0} for r in rules],
        "total": len(rules),
        "page": page,
        "page_size": page_size,
        "query": f"role={role},location={location},dept={department}",
    }


@router.post("/conflict")
async def conflict_search(
    rule_id: str = Query(..., description="Rule ID to find conflicts for"),
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Search for rules that conflict with a given rule."""
    from rulerepo_server.adapters.postgres.models import RuleRelationshipModel

    stmt = (
        select(RuleRelationshipModel)
        .where(RuleRelationshipModel.relationship_type == "CONFLICTS_WITH")
        .where(
            sa.or_(
                RuleRelationshipModel.source_id == rule_id,
                RuleRelationshipModel.target_id == rule_id,
            )
        )
    )
    result = await session.execute(stmt)
    rels = list(result.scalars().all())

    conflicting_ids = set()
    for rel in rels:
        other = str(rel.target_id) if str(rel.source_id) == rule_id else str(rel.source_id)
        conflicting_ids.add(other)

    if not conflicting_ids:
        return {"items": [], "total": 0, "page": 1, "page_size": 20, "query": rule_id}

    rule_stmt = select(RuleModel).where(RuleModel.id.in_(list(conflicting_ids)))
    if project_id:
        rule_stmt = rule_stmt.where(RuleModel.project_id == project_id)
    rule_result = await session.execute(rule_stmt)
    rules = list(rule_result.scalars().all())
    return {
        "items": [{"rule": {"id": str(r.id), "statement": r.statement, "scope": r.scope}, "score": 1.0} for r in rules],
        "total": len(rules),
        "page": 1,
        "page_size": 20,
        "query": rule_id,
    }


def _build_filters(query: SearchQuery, accept_language: str | None = None) -> dict:
    """Build ES filter dict from search query parameters.

    When ``query.language`` is set it takes precedence.  Otherwise, the
    ``Accept-Language`` header is parsed for a primary language tag and
    mapped to the ``primary_language`` ES field.
    """
    filters: dict = {}
    if query.modality:
        filters["modality"] = query.modality.value
    if query.severity:
        filters["severity"] = query.severity.value
    if query.scope:
        filters["scope"] = query.scope
    if query.tags:
        filters["tags"] = query.tags

    # Language filter: explicit query param > Accept-Language header.
    lang = query.language
    if not lang and accept_language:
        lang = _parse_accept_language(accept_language)
    if lang:
        filters["primary_language"] = lang

    return filters


def _parse_accept_language(header: str) -> str | None:
    """Extract the primary language tag from an Accept-Language header.

    Returns the first two-letter language code, or None if unparseable.
    Examples: ``"ja,en;q=0.9"`` → ``"ja"``, ``"en-US"`` → ``"en"``.
    """
    if not header:
        return None
    # Take the first language (highest priority).
    first = header.split(",")[0].strip()
    # Strip quality factor.
    tag = first.split(";")[0].strip()
    # Extract primary subtag (e.g., "en-US" → "en").
    primary = tag.split("-")[0].strip().lower()
    if len(primary) == 2 and primary.isalpha():
        return primary
    return None

"""REST API routes for search operations."""

from fastapi import APIRouter, Depends

from rulerepo_server.core.deps import get_search_service
from rulerepo_server.schemas.search import CategorySearchQuery, ContextSearchQuery, SearchQuery
from rulerepo_server.services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/fulltext")
async def fulltext_search(
    query: SearchQuery,
    service: SearchService = Depends(get_search_service),
) -> dict:
    """BM25 full-text search over rule statements."""
    filters = _build_filters(query)
    return await service.fulltext_search(
        query.query, filters=filters, page=query.page, page_size=query.page_size
    )


@router.post("/vector")
async def vector_search(
    query: SearchQuery,
    service: SearchService = Depends(get_search_service),
) -> dict:
    """Semantic similarity search using embeddings."""
    filters = _build_filters(query)
    return await service.vector_search(
        query.query, filters=filters, page=query.page, page_size=query.page_size
    )


@router.post("/hybrid")
async def hybrid_search(
    query: SearchQuery,
    service: SearchService = Depends(get_search_service),
) -> dict:
    """Combined BM25 + vector hybrid search."""
    filters = _build_filters(query)
    return await service.hybrid_search(
        query.query, filters=filters, page=query.page, page_size=query.page_size
    )


@router.post("/category")
async def category_search(
    query: CategorySearchQuery,
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
    return await service.category_search(
        filters=filters, page=query.page, page_size=query.page_size
    )


@router.post("/context")
async def context_search(
    query: ContextSearchQuery,
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
    )


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

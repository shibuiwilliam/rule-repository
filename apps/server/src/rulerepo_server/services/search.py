"""Search service — coordinates multi-modal search across Elasticsearch and Postgres."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.elasticsearch.rule_index import ElasticsearchRuleIndex
from rulerepo_server.adapters.gemini.embeddings import generate_embedding
from rulerepo_server.adapters.postgres.rule_repo import PostgresRuleRepository
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class SearchService:
    """Multi-modal search over the rule corpus.

    Searches ES for IDs and scores, then hydrates full Rule objects from Postgres.
    """

    def __init__(
        self,
        session: AsyncSession,
        es_index: ElasticsearchRuleIndex,
        gemini_client: Any | None = None,
    ) -> None:
        self._rule_repo = PostgresRuleRepository(session)
        self._es_index = es_index
        self._gemini_client = gemini_client

    async def fulltext_search(
        self,
        query: str,
        *,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """BM25 full-text search.

        Args:
            query: Search query text.
            filters: Optional field filters.
            page: Page number.
            page_size: Results per page.

        Returns:
            Search results with rule data and scores.
        """
        hits, total = await self._es_index.search_fulltext(
            query, filters=filters, page=page, page_size=page_size
        )
        return await self._hydrate_results(hits, total, page, page_size, query)

    async def vector_search(
        self,
        query: str,
        *,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Semantic similarity search using embeddings.

        Args:
            query: Natural-language query to embed.
            filters: Optional field filters.
            page: Page number.
            page_size: Results per page.

        Returns:
            Search results with rule data and scores.
        """
        embedding: list[float] = []
        if self._gemini_client:
            embedding = await generate_embedding(self._gemini_client, query)

        if not embedding:
            logger.warning("vector_search_no_embedding", query=query[:100])
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "query": query}

        hits, total = await self._es_index.search_vector(
            embedding, filters=filters, page=page, page_size=page_size
        )
        return await self._hydrate_results(hits, total, page, page_size, query)

    async def hybrid_search(
        self,
        query: str,
        *,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Combined BM25 + vector search.

        Args:
            query: Search query text.
            filters: Optional field filters.
            page: Page number.
            page_size: Results per page.

        Returns:
            Search results with rule data and scores.
        """
        embedding: list[float] = []
        if self._gemini_client:
            try:
                embedding = await generate_embedding(self._gemini_client, query)
            except Exception as exc:
                logger.warning("hybrid_embedding_failed", error=str(exc))

        if embedding:
            hits, total = await self._es_index.search_hybrid(
                query, embedding, filters=filters, page=page, page_size=page_size
            )
        else:
            # Fall back to fulltext if embedding unavailable
            hits, total = await self._es_index.search_fulltext(
                query, filters=filters, page=page, page_size=page_size
            )

        return await self._hydrate_results(hits, total, page, page_size, query)

    async def category_search(
        self,
        *,
        filters: dict,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Filter-only search by category fields (no free-text query).

        Args:
            filters: Filter criteria (modality, severity, tags, scope, status).
            page: Page number.
            page_size: Results per page.

        Returns:
            Search results with rule data.
        """
        hits, total = await self._es_index.search_category(
            filters=filters, page=page, page_size=page_size
        )
        return await self._hydrate_results(hits, total, page, page_size, "")

    async def context_search(
        self,
        facts: dict[str, object],
        *,
        scope: list[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, object]:
        """Context search — given a body of facts, return applicable rules.

        Converts the facts into a natural-language description, then runs
        hybrid search to find rules whose scope and statement match the context.
        PROJECT.md §6.1: "given a body of facts, return applicable rules."

        Args:
            facts: Key-value pairs describing the current situation.
            scope: Optional scope filter to narrow results.
            page: Page number.
            page_size: Results per page.

        Returns:
            Search results with applicable rules and scores.
        """
        # Build a natural-language summary of the facts for semantic matching
        fact_lines = [f"{k}: {v}" for k, v in facts.items()]
        query = "Given these facts: " + "; ".join(fact_lines)

        filters: dict[str, object] = {}
        if scope:
            filters["scope"] = scope

        return await self.hybrid_search(query, filters=filters, page=page, page_size=page_size)

    async def _hydrate_results(
        self,
        hits: list[tuple[str, float]],
        total: int,
        page: int,
        page_size: int,
        query: str,
    ) -> dict:
        """Hydrate search hits with full rule data from Postgres.

        Args:
            hits: List of (rule_id, score) from ES.
            total: Total number of matching documents.
            page: Current page number.
            page_size: Items per page.
            query: Original query string.

        Returns:
            Formatted search response dictionary.
        """
        if not hits:
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "query": query}

        rule_ids = [UUID(hit[0]) for hit in hits]
        scores = {hit[0]: hit[1] for hit in hits}

        rules = await self._rule_repo.get_rules_by_ids(rule_ids)
        rule_map = {str(r.id): r for r in rules}

        items = []
        for rule_id_str, score in scores.items():
            model = rule_map.get(rule_id_str)
            if model:
                items.append(
                    {
                        "rule": {
                            "id": str(model.id),
                            "statement": model.statement,
                            "modality": model.modality,
                            "severity": model.severity,
                            "status": model.status,
                            "scope": model.scope,
                            "tags": model.tags,
                            "rationale": model.rationale,
                            "preconditions": model.preconditions,
                            "exceptions": model.exceptions,
                            "source_refs": model.source_refs,
                            "effective_period": model.effective_period,
                            "governance": model.governance,
                            "created_at": model.created_at,
                            "updated_at": model.updated_at,
                        },
                        "score": score,
                    }
                )

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "query": query,
        }

"""Elasticsearch index operations for rules — search and indexing."""

from __future__ import annotations

from uuid import UUID

from elasticsearch import AsyncElasticsearch
from elasticsearch import NotFoundError as ESNotFoundError

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

INDEX_NAME = "rules"


class ElasticsearchRuleIndex:
    """Manages the Elasticsearch 'rules' index for search operations."""

    def __init__(self, client: AsyncElasticsearch) -> None:
        self._client = client

    async def index_rule(
        self,
        rule_id: UUID,
        document: dict,
        *,
        tenant_id: str | None = None,
    ) -> None:
        """Index or re-index a rule document.

        Args:
            rule_id: The rule's UUID (used as the ES document ID).
            document: The document body to index.
            tenant_id: Optional tenant ID for routing tenant isolation.
        """
        kwargs: dict = {
            "index": INDEX_NAME,
            "id": str(rule_id),
            "document": document,
        }
        if tenant_id:
            kwargs["routing"] = f"tenant_{tenant_id}"
        await self._client.index(**kwargs)
        logger.info("rule_indexed", rule_id=str(rule_id), tenant_id=tenant_id)

    async def delete_rule(self, rule_id: UUID) -> None:
        """Remove a rule from the index.

        Args:
            rule_id: The rule's UUID.
        """
        try:
            await self._client.delete(index=INDEX_NAME, id=str(rule_id))
            logger.info("rule_deleted_from_index", rule_id=str(rule_id))
        except ESNotFoundError:
            logger.warning("rule_not_in_index", rule_id=str(rule_id))

    async def search_fulltext(
        self,
        query: str,
        *,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[tuple[str, float]], int]:
        """BM25 full-text search on rule statements.

        Args:
            query: The search query text.
            filters: Optional ES filter clauses.
            page: Page number (1-indexed).
            page_size: Results per page.

        Returns:
            Tuple of (list of (rule_id, score), total_hits).
        """
        body = self._build_query(
            must={"match": {"statement": {"query": query, "fuzziness": "AUTO"}}},
            filters=filters,
            page=page,
            page_size=page_size,
        )
        return await self._execute_search(body)

    async def search_vector(
        self,
        embedding: list[float],
        *,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
        k: int = 50,
    ) -> tuple[list[tuple[str, float]], int]:
        """kNN vector search on rule embeddings.

        Args:
            embedding: Query vector.
            filters: Optional ES filter clauses.
            page: Page number.
            page_size: Results per page.
            k: Number of nearest neighbors to retrieve.

        Returns:
            Tuple of (list of (rule_id, score), total_hits).
        """
        body: dict = {
            "knn": {
                "field": "embedding",
                "query_vector": embedding,
                "k": k,
                "num_candidates": k * 2,
            },
            "size": page_size,
            "from": (page - 1) * page_size,
        }
        if filters:
            body["knn"]["filter"] = {"bool": {"filter": self._build_filters(filters)}}
        return await self._execute_search(body)

    async def search_hybrid(
        self,
        query: str,
        embedding: list[float],
        *,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[tuple[str, float]], int]:
        """Hybrid BM25 + kNN search combining text relevance and semantic similarity.

        Args:
            query: Text query for BM25.
            embedding: Query vector for kNN.
            filters: Optional filter clauses.
            page: Page number.
            page_size: Results per page.

        Returns:
            Tuple of (list of (rule_id, score), total_hits).
        """
        filter_clauses = self._build_filters(filters) if filters else []
        body: dict = {
            "query": {
                "bool": {
                    "must": {"match": {"statement": {"query": query, "fuzziness": "AUTO"}}},
                    "filter": filter_clauses,
                },
            },
            "knn": {
                "field": "embedding",
                "query_vector": embedding,
                "k": 50,
                "num_candidates": 100,
            },
            "size": page_size,
            "from": (page - 1) * page_size,
        }
        return await self._execute_search(body)

    async def search_category(
        self,
        *,
        filters: dict,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[tuple[str, float]], int]:
        """Category/filter-only search (no free-text query).

        Args:
            filters: Filter criteria (modality, severity, tags, scope, status).
            page: Page number.
            page_size: Results per page.

        Returns:
            Tuple of (list of (rule_id, score), total_hits).
        """
        body = self._build_query(
            must={"match_all": {}},
            filters=filters,
            page=page,
            page_size=page_size,
        )
        return await self._execute_search(body)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _build_query(
        self,
        must: dict,
        filters: dict | None,
        page: int,
        page_size: int,
    ) -> dict:
        filter_clauses = self._build_filters(filters) if filters else []
        return {
            "query": {
                "bool": {
                    "must": must,
                    "filter": filter_clauses,
                },
            },
            "size": page_size,
            "from": (page - 1) * page_size,
            "sort": ["_score", {"created_at": "desc"}],
        }

    @staticmethod
    def _build_filters(filters: dict | None) -> list[dict]:
        if not filters:
            return []
        clauses: list[dict] = []
        for key, value in filters.items():
            if value is None:
                continue
            if isinstance(value, list):
                clauses.append({"terms": {key: value}})
            else:
                clauses.append({"term": {key: value}})
        return clauses

    async def _execute_search(self, body: dict) -> tuple[list[tuple[str, float]], int]:
        result = await self._client.search(index=INDEX_NAME, body=body)
        hits = result["hits"]["hits"]
        total = result["hits"]["total"]["value"]
        return [(hit["_id"], hit["_score"] or 0.0) for hit in hits], total

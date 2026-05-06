"""Elasticsearch index operations for documents — full-text, vector, and hybrid search."""

from __future__ import annotations

from uuid import UUID

from elasticsearch import AsyncElasticsearch
from elasticsearch import NotFoundError as ESNotFoundError

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

DOC_INDEX_NAME = "documents"


class ElasticsearchDocumentIndex:
    """Manages the Elasticsearch 'documents' index for document search operations."""

    def __init__(self, client: AsyncElasticsearch) -> None:
        self._client = client

    async def ensure_index(self) -> None:
        """Create the documents index if it doesn't exist."""
        exists = await self._client.indices.exists(index=DOC_INDEX_NAME)
        if not exists:
            await self._client.indices.create(
                index=DOC_INDEX_NAME,
                body={
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                    },
                    "mappings": {
                        "properties": {
                            "document_id": {"type": "keyword"},
                            "project_id": {"type": "keyword"},
                            "filename": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {"keyword": {"type": "keyword"}},
                            },
                            "content_text": {"type": "text", "analyzer": "standard"},
                            "mime_type": {"type": "keyword"},
                            "size_bytes": {"type": "integer"},
                            "uploaded_by": {"type": "keyword"},
                            "uploaded_at": {"type": "date"},
                            "embedding": {
                                "type": "dense_vector",
                                "dims": 768,
                                "index": True,
                                "similarity": "cosine",
                            },
                        },
                    },
                },
            )
            logger.info("documents_index_created")

    async def index_document(self, document_id: UUID, doc: dict) -> None:
        """Index or re-index a document.

        Args:
            document_id: The document's UUID (used as ES document ID).
            doc: The document body containing filename, content_text, embedding, etc.
        """
        await self.ensure_index()
        await self._client.index(
            index=DOC_INDEX_NAME,
            id=str(document_id),
            document=doc,
        )
        logger.info("document_indexed", document_id=str(document_id))

    async def delete_document(self, document_id: UUID) -> None:
        """Remove a document from the index."""
        try:
            await self._client.delete(index=DOC_INDEX_NAME, id=str(document_id))
            logger.info("document_deleted_from_index", document_id=str(document_id))
        except ESNotFoundError:
            logger.warning("document_not_in_index", document_id=str(document_id))

    async def search_fulltext(
        self,
        query: str,
        *,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[tuple[str, float, dict]], int]:
        """BM25 full-text search on document filename and content.

        Returns:
            Tuple of (list of (document_id, score, source), total_hits).
        """
        body = {
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": ["filename^3", "content_text"],
                            "fuzziness": "AUTO",
                        },
                    },
                    "filter": self._build_filters(filters),
                },
            },
            "size": page_size,
            "from": (page - 1) * page_size,
            "sort": ["_score", {"uploaded_at": "desc"}],
            "highlight": {
                "fields": {
                    "content_text": {"fragment_size": 200, "number_of_fragments": 2},
                    "filename": {},
                },
            },
        }
        return await self._execute_search(body)

    async def search_vector(
        self,
        embedding: list[float],
        *,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 20,
        k: int = 50,
    ) -> tuple[list[tuple[str, float, dict]], int]:
        """kNN vector search on document embeddings (semantic search).

        Returns:
            Tuple of (list of (document_id, score, source), total_hits).
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
    ) -> tuple[list[tuple[str, float, dict]], int]:
        """Hybrid BM25 + kNN search combining text relevance and semantic similarity.

        Returns:
            Tuple of (list of (document_id, score, source), total_hits).
        """
        filter_clauses = self._build_filters(filters) if filters else []
        body: dict = {
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": ["filename^3", "content_text"],
                            "fuzziness": "AUTO",
                        },
                    },
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
            "highlight": {
                "fields": {
                    "content_text": {"fragment_size": 200, "number_of_fragments": 2},
                },
            },
        }
        return await self._execute_search(body)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

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

    async def _execute_search(self, body: dict) -> tuple[list[tuple[str, float, dict]], int]:
        """Execute an ES search and return (doc_id, score, source) tuples."""
        try:
            await self.ensure_index()
            result = await self._client.search(index=DOC_INDEX_NAME, body=body)
        except Exception as exc:
            logger.warning("document_search_failed", error=str(exc))
            return [], 0
        hits = result["hits"]["hits"]
        total = result["hits"]["total"]["value"]
        return [
            (
                hit["_id"],
                hit["_score"] or 0.0,
                {
                    **hit.get("_source", {}),
                    "highlight": hit.get("highlight", {}),
                },
            )
            for hit in hits
        ], total

"""Test fixtures for the Rule Repository server.

Provides mocked adapters and a configured FastAPI TestClient
so integration tests can run without Docker infrastructure.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.elasticsearch.rule_index import ElasticsearchRuleIndex
from rulerepo_server.adapters.neo4j.graph_repo import Neo4jGraphRepository
from rulerepo_server.adapters.postgres.audit_repo import AuditLogRepository
from rulerepo_server.adapters.postgres.rule_repo import PostgresRuleRepository


# ---------------------------------------------------------------------------
# In-memory store to back the mocked repositories
# ---------------------------------------------------------------------------


class _FakeStore:
    def __init__(self) -> None:
        self.rules: dict[str, dict[str, Any]] = {}
        self.revisions: dict[str, list[dict[str, Any]]] = {}
        self.relationships: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.rules.clear()
        self.revisions.clear()
        self.relationships.clear()


_store = _FakeStore()


class _Obj:
    """Generic attribute-bag that mimics an ORM model."""

    def __init__(self, **kw: Any) -> None:
        for k, v in kw.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    _store.reset()


@pytest.fixture
def sample_rule_data() -> dict[str, Any]:
    return {
        "statement": "All production deployments must go through staging first",
        "modality": "MUST",
        "severity": "HIGH",
        "scope": ["engineering", "devops"],
        "tags": ["deployment", "ci-cd"],
        "rationale": "Prevents untested code from reaching production",
    }


@pytest.fixture
def sample_rule_data_list() -> list[dict[str, Any]]:
    return [
        {
            "statement": "Overtime must not exceed 45 hours per month",
            "modality": "MUST_NOT",
            "severity": "HIGH",
            "scope": ["hr/attendance"],
            "tags": ["overtime", "labor-law"],
        },
        {
            "statement": "All code must be reviewed by at least one peer before merging",
            "modality": "MUST",
            "severity": "MEDIUM",
            "scope": ["engineering"],
            "tags": ["code-review"],
        },
        {
            "statement": "Contract values above $10,000 should be approved by procurement",
            "modality": "SHOULD",
            "severity": "MEDIUM",
            "scope": ["procurement", "contracts"],
            "tags": ["approval", "procurement"],
        },
    ]


# ---------------------------------------------------------------------------
# App + Client fixtures
# ---------------------------------------------------------------------------


def _build_mock_rule_repo() -> MagicMock:
    """Build an in-memory mock of PostgresRuleRepository."""
    repo = MagicMock(spec=PostgresRuleRepository)

    async def _create(data: dict[str, Any]) -> _Obj:
        _store.rules[str(data["id"])] = data
        return _Obj(**data)

    async def _get_by_id(rule_id: Any) -> _Obj:
        key = str(rule_id)
        if key not in _store.rules:
            from rulerepo_server.core.errors import NotFoundError

            raise NotFoundError("Rule", key)
        return _Obj(**_store.rules[key])

    async def _list_rules(**kw: Any) -> tuple[list[_Obj], int]:
        all_rules = list(_store.rules.values())
        page = kw.get("page", 1)
        page_size = kw.get("page_size", 20)
        start = (page - 1) * page_size
        return [_Obj(**r) for r in all_rules[start : start + page_size]], len(all_rules)

    async def _update(rule_id: Any, updates: dict[str, Any]) -> _Obj:
        key = str(rule_id)
        if key not in _store.rules:
            from rulerepo_server.core.errors import NotFoundError

            raise NotFoundError("Rule", key)
        _store.rules[key].update(updates)
        return _Obj(**_store.rules[key])

    async def _create_revision(data: dict[str, Any]) -> _Obj:
        rid = str(data["rule_id"])
        _store.revisions.setdefault(rid, []).append(data)
        return _Obj(**data)

    async def _get_revisions(rule_id: Any) -> list[_Obj]:
        return [_Obj(**r) for r in _store.revisions.get(str(rule_id), [])]

    async def _get_latest_rev_num(rule_id: Any) -> int:
        revs = _store.revisions.get(str(rule_id), [])
        return max((r["revision_number"] for r in revs), default=0)

    async def _get_relationships(rule_id: Any) -> list[_Obj]:
        key = str(rule_id)
        return [
            _Obj(**r)
            for r in _store.relationships
            if str(r.get("source_id")) == key or str(r.get("target_id")) == key
        ]

    async def _create_relationship(data: dict[str, Any]) -> _Obj:
        data.setdefault("created_at", datetime.now(tz=timezone.utc))
        _store.relationships.append(data)
        return _Obj(**data)

    async def _get_rules_by_ids(ids: list[Any]) -> list[_Obj]:
        return [_Obj(**_store.rules[str(i)]) for i in ids if str(i) in _store.rules]

    repo.create = AsyncMock(side_effect=_create)
    repo.get_by_id = AsyncMock(side_effect=_get_by_id)
    repo.list_rules = AsyncMock(side_effect=_list_rules)
    repo.update = AsyncMock(side_effect=_update)
    repo.create_revision = AsyncMock(side_effect=_create_revision)
    repo.get_revisions = AsyncMock(side_effect=_get_revisions)
    repo.get_latest_revision_number = AsyncMock(side_effect=_get_latest_rev_num)
    repo.get_relationships = AsyncMock(side_effect=_get_relationships)
    repo.create_relationship = AsyncMock(side_effect=_create_relationship)
    repo.delete_relationship = AsyncMock()
    repo.get_rules_by_ids = AsyncMock(side_effect=_get_rules_by_ids)
    return repo


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app with mocked dependencies for testing."""
    from rulerepo_server.core.deps import get_es_index, get_graph_repo, get_rule_service, get_search_service
    from rulerepo_server.main import create_app
    from rulerepo_server.services.rule_service import RuleService
    from rulerepo_server.services.search import SearchService

    test_app = create_app()

    mock_es = MagicMock(spec=ElasticsearchRuleIndex)
    mock_es.index_rule = AsyncMock()
    mock_es.delete_rule = AsyncMock()
    mock_es.search_fulltext = AsyncMock(return_value=([], 0))
    mock_es.search_vector = AsyncMock(return_value=([], 0))
    mock_es.search_hybrid = AsyncMock(return_value=([], 0))
    mock_es.search_category = AsyncMock(return_value=([], 0))

    mock_graph = MagicMock(spec=Neo4jGraphRepository)
    mock_graph.upsert_rule_node = AsyncMock()
    mock_graph.create_relationship = AsyncMock()
    mock_graph.delete_relationship = AsyncMock()
    mock_graph.get_subgraph = AsyncMock(return_value={"nodes": [], "edges": []})

    mock_rule_repo = _build_mock_rule_repo()

    mock_audit = MagicMock(spec=AuditLogRepository)
    mock_audit.append = AsyncMock()

    def _rule_service() -> RuleService:
        svc = RuleService.__new__(RuleService)
        svc._rule_repo = mock_rule_repo
        svc._audit_repo = mock_audit
        svc._es_index = mock_es
        svc._graph_repo = mock_graph
        svc._gemini_client = None
        svc._session = MagicMock(spec=AsyncSession)
        return svc

    def _search_service() -> SearchService:
        svc = SearchService.__new__(SearchService)
        svc._rule_repo = mock_rule_repo
        svc._es_index = mock_es
        svc._gemini_client = None
        return svc

    test_app.dependency_overrides[get_es_index] = lambda: mock_es
    test_app.dependency_overrides[get_graph_repo] = lambda: mock_graph
    test_app.dependency_overrides[get_rule_service] = _rule_service
    test_app.dependency_overrides[get_search_service] = _search_service

    return test_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client wired to the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

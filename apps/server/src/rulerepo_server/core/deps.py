"""FastAPI dependency injection factories.

Provides configured service instances for API route handlers.
Tier-aware: uses Postgres fallbacks when Elasticsearch or Neo4j
are disabled.

Also provides ``require_department_action`` for ABAC enforcement
on rule-touching endpoints (CLAUDE.md §13 rule 19).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.auth import CurrentUser, get_current_user
from rulerepo_server.core.errors import AuthorizationError
from rulerepo_server.core.feature_flags import get_feature_flags
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.department import Action
from rulerepo_server.services.rule_service import RuleService
from rulerepo_server.services.search import SearchService

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# ABAC enforcement dependency
# ---------------------------------------------------------------------------


def require_department_action(action: Action):
    """Create a dependency that enforces department ABAC for a given action.

    Resolves the owning department from path params (``rule_id``) or
    query params (``department``), then checks the user's capacity against
    the active policy set.

    Args:
        action: The department action (READ, EDIT, APPROVE, EVALUATE, DELETE).

    Returns:
        A FastAPI dependency function that raises ``AuthorizationError``
        when the user lacks the required capacity.
    """

    async def _enforce(
        request: Request,
        user: CurrentUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> None:
        # When auth is not required (local dev), anonymous OWNER bypasses
        # department RBAC to allow seeding and testing without capacity setup.
        if not get_feature_flags().department_rbac_enabled:
            return
        from rulerepo_server.core.config import get_settings as _get_settings

        if not _get_settings().auth_required and user.user_id == "anonymous":
            return

        from rulerepo_server.services.departments.authz import check_permission

        department_id = await _resolve_department(request, session)

        authorized = await check_permission(session, user.user_id, department_id, action)

        if not authorized:
            _logger.warning(
                "abac_denied",
                user_id=user.user_id,
                department=department_id,
                action=action.value,
                path=str(request.url.path),
            )
            raise AuthorizationError(
                f"User '{user.user_id}' is not authorized to {action.value} resources in department '{department_id}'."
            )

        _logger.debug(
            "abac_authorized",
            user_id=user.user_id,
            department=department_id,
            action=action.value,
        )

    return _enforce


async def _resolve_department(request: Request, session: AsyncSession) -> str:
    """Resolve the owning department from the request context.

    Resolution order:
    1. ``rule_id`` in path params -> look up the rule's department column.
    2. ``department`` in query params -> use directly.
    3. Fall back to ``"public"``.
    """
    rule_id_str = request.path_params.get("rule_id")
    if rule_id_str:
        try:
            from sqlalchemy import select

            from rulerepo_server.adapters.postgres.models import RuleModel

            rule_uuid = UUID(rule_id_str)
            result = await session.execute(select(RuleModel.department).where(RuleModel.id == rule_uuid))
            row = result.scalar_one_or_none()
            if row:
                return str(row)
        except (ValueError, Exception):
            pass

    dept_param = request.query_params.get("department")
    if dept_param:
        return dept_param

    return "public"


async def get_search_index(
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Provide the appropriate search index adapter for the current tier.

    Tier 2/3: ``ElasticsearchRuleIndex``.
    Tier 1:   ``PostgresFTSIndex`` (Postgres full-text search fallback).
    """
    flags = get_feature_flags()
    if flags.elasticsearch_enabled:
        from rulerepo_server.adapters.elasticsearch.client import get_es_client
        from rulerepo_server.adapters.elasticsearch.rule_index import ElasticsearchRuleIndex

        return ElasticsearchRuleIndex(get_es_client())

    from rulerepo_server.adapters.search.postgres_fts import PostgresFTSIndex

    return PostgresFTSIndex(session)


async def get_graph_repo(
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Provide the appropriate graph repository for the current tier.

    Tier 3:   ``Neo4jGraphRepository``.
    Tier 1/2: ``PostgresGraphRepository`` (adjacency table fallback).
    """
    flags = get_feature_flags()
    if flags.neo4j_enabled:
        from rulerepo_server.adapters.neo4j.client import get_neo4j_driver
        from rulerepo_server.adapters.neo4j.graph_repo import Neo4jGraphRepository

        return Neo4jGraphRepository(get_neo4j_driver())

    from rulerepo_server.adapters.graph.postgres_adjacency import PostgresGraphRepository

    return PostgresGraphRepository(session)


def _get_optional_gemini() -> Any | None:
    """Attempt to get Gemini client, returning None if unavailable.

    Logs a warning on failure rather than silently swallowing the error.
    """
    try:
        from rulerepo_server.adapters.gemini.client import get_gemini_client

        return get_gemini_client()
    except Exception as exc:
        _logger.warning("gemini_client_unavailable", error=str(exc))
        return None


async def get_rule_service(
    session: AsyncSession = Depends(get_db_session),
    search_index: Any = Depends(get_search_index),
    graph_repo: Any = Depends(get_graph_repo),
) -> RuleService:
    """Provide a RuleService wired to all data stores."""
    return RuleService(session, search_index, graph_repo, _get_optional_gemini())


async def get_search_service(
    session: AsyncSession = Depends(get_db_session),
    search_index: Any = Depends(get_search_index),
) -> SearchService:
    """Provide a SearchService wired to the appropriate search adapter."""
    return SearchService(session, search_index, _get_optional_gemini())


# ---------------------------------------------------------------------------
# Governance policy dependency (ABAC — PROJECT.md §6.9, CLAUDE.md §14.10)
# ---------------------------------------------------------------------------


def require_governance_policy(action: str):
    """Create a dependency that enforces ABAC governance policies.

    Only active when ``ABAC_GOVERNANCE_ENABLED`` is ``true``. When the
    flag is off, this dependency is a no-op.

    Resolution order (per GovernanceResolver):
    explicit deny > explicit allow > inherited allow > default deny.

    Args:
        action: The governance action (e.g. "rule.read", "rule.edit",
                "rule.approve", "rule.evaluate").

    Returns:
        A FastAPI dependency that raises ``AuthorizationError`` when
        the principal lacks access.
    """

    async def _enforce(
        request: Request,
        user: CurrentUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> None:
        flags = get_feature_flags()
        if not flags.abac_governance_enabled:
            return  # ABAC not yet enabled — pass through

        from rulerepo_server.services.governance.resolver import GovernanceResolver

        # Build resolver from stored policies (stub: empty policy list for now)
        # In production this would load policies from the governance_policies table.
        resolver = GovernanceResolver()

        # Determine principal and domain from request context
        principal = f"user:{user.user_id}"
        domain = request.query_params.get("domain")
        org_unit = request.query_params.get("org_unit")

        decision = resolver.evaluate(
            principal=principal,
            action=action,
            domain=domain,
            org_unit=org_unit,
        )

        if not decision.allowed:
            _logger.warning(
                "governance_denied",
                principal=principal,
                action=action,
                domain=domain,
                org_unit=org_unit,
                reason=decision.reason,
            )
            raise AuthorizationError(f"Governance policy denied: {decision.reason}")

    return _enforce

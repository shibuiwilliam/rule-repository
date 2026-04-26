"""MCP resource definitions — expose rules as addressable resources."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


def register_resources(mcp: FastMCP) -> None:
    """Register all MCP resources on the server."""

    @mcp.resource("rule://{rule_id}")
    async def get_rule(rule_id: str) -> dict[str, Any]:
        """A single rule with full metadata, accessible by ID."""
        from uuid import UUID

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.rule_repo import PostgresRuleRepository
        from rulerepo_server.adapters.postgres.session import get_engine

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            repo = PostgresRuleRepository(session)
            try:
                rule = await repo.get_by_id(UUID(rule_id))
            except Exception:
                return {"error": f"Rule not found: {rule_id}"}

        return {
            "id": str(rule.id),
            "statement": rule.statement,
            "modality": rule.modality,
            "severity": rule.severity,
            "status": rule.status,
            "scope": rule.scope,
            "tags": rule.tags,
            "rationale": rule.rationale,
            "governance": rule.governance,
        }

    @mcp.resource("ruleset://{scope}")
    async def get_ruleset(scope: str) -> str:
        """A formatted rule set for a scope — like a dynamic CLAUDE.md section.

        Example: ruleset://engineering/python returns all Python coding rules
        formatted as actionable instructions. Always up-to-date.
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.context_delivery.service import ContextDeliveryService

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            svc = ContextDeliveryService(session)
            return await svc.get_formatted_rules(
                scope=scope,
                format_type="instructions",
            )

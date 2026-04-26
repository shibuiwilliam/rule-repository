"""MCP tool definitions — the core agent-facing interface.

Per CLAUDE_ENHANCE.md §2.3: tool names are verb_noun. Descriptions
explain WHEN to use the tool. Outputs are serializable dicts.
Every tool delegates to existing services.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools on the server."""

    @mcp.tool()
    async def search_rules(
        query: str,
        scope: str | None = None,
        modality: str | None = None,
        severity: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Search the rule repository for rules matching a query.

        Use this when you need to find organizational rules, policies,
        regulations, or guidelines relevant to a task or decision.
        Supports natural language queries — describe what you're looking for.

        Args:
            query: Natural language search query.
            scope: Narrow to a specific scope (e.g., "engineering", "hr/attendance").
            modality: Filter by obligation strength (MUST, MUST_NOT, SHOULD, MAY, INFO).
            severity: Filter by impact level (LOW, MEDIUM, HIGH, CRITICAL).
            top_k: Maximum number of results to return.
        """
        # Build service call — reuses the same search path as REST API
        from rulerepo_server.adapters.elasticsearch.client import get_es_client
        from rulerepo_server.adapters.elasticsearch.rule_index import ElasticsearchRuleIndex

        es_index = ElasticsearchRuleIndex(get_es_client())
        filters: dict[str, Any] = {}
        if scope:
            filters["scope"] = [scope]
        if modality:
            filters["modality"] = modality
        if severity:
            filters["severity"] = severity

        hits, total = await es_index.search_fulltext(
            query, filters=filters, page=1, page_size=top_k
        )

        # Hydrate from Postgres
        if not hits:
            return []

        from uuid import UUID

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.rule_repo import PostgresRuleRepository
        from rulerepo_server.adapters.postgres.session import get_engine

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            repo = PostgresRuleRepository(session)
            rule_ids = [UUID(h[0]) for h in hits]
            rules = await repo.get_rules_by_ids(rule_ids)

        return [
            {
                "id": str(r.id),
                "statement": r.statement,
                "modality": r.modality,
                "severity": r.severity,
                "scope": r.scope,
                "tags": r.tags,
                "rationale": r.rationale,
                "status": r.status,
            }
            for r in rules
        ]

    @mcp.tool()
    async def explain_rule(
        rule_id: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Get a detailed explanation of a rule including its rationale,
        source provenance, relationships, and revision history.

        Use this when you need to understand WHY a rule exists, WHERE it
        came from, and HOW it relates to other rules before making a decision.

        Args:
            rule_id: The UUID of the rule to explain.
            depth: How many levels of relationships to traverse (1-5).
        """
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

            revisions = await repo.get_revisions(UUID(rule_id))
            relationships = await repo.get_relationships(UUID(rule_id))

        return {
            "id": str(rule.id),
            "statement": rule.statement,
            "modality": rule.modality,
            "severity": rule.severity,
            "status": rule.status,
            "rationale": rule.rationale or "No rationale documented.",
            "scope": rule.scope,
            "tags": rule.tags,
            "source_refs": rule.source_refs,
            "governance": rule.governance,
            "effective_period": rule.effective_period,
            "revision_count": len(revisions),
            "latest_revision": {
                "number": revisions[-1].revision_number,
                "changed_by": revisions[-1].changed_by,
                "note": revisions[-1].change_note,
            }
            if revisions
            else None,
            "relationships": [
                {
                    "type": r.relationship_type,
                    "source_id": str(r.source_id),
                    "target_id": str(r.target_id),
                }
                for r in relationships
            ],
        }

    @mcp.tool()
    async def find_conflicts(
        rule_id: str | None = None,
        proposed_statement: str | None = None,
        scope: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find rules that may conflict with a given rule or proposed rule statement.

        Use this when proposing a new rule or changing an existing one to check
        for contradictions with the existing rule corpus.

        Args:
            rule_id: UUID of an existing rule to check for conflicts.
            proposed_statement: Text of a proposed new rule to check.
            scope: Limit conflict search to a specific scope.
        """
        query = proposed_statement or ""
        if rule_id and not proposed_statement:
            # Fetch the rule's statement to use as search query
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
                    query = rule.statement
                except Exception:
                    return [{"error": f"Rule not found: {rule_id}"}]

        if not query:
            return [{"error": "Provide either rule_id or proposed_statement"}]

        # Search for semantically similar rules (potential conflicts)
        from rulerepo_server.adapters.elasticsearch.client import get_es_client
        from rulerepo_server.adapters.elasticsearch.rule_index import ElasticsearchRuleIndex

        es_index = ElasticsearchRuleIndex(get_es_client())
        filters: dict[str, Any] = {}
        if scope:
            filters["scope"] = [scope]

        hits, _ = await es_index.search_fulltext(query, filters=filters, page=1, page_size=20)

        # Filter out the source rule itself
        if rule_id:
            hits = [(h, s) for h, s in hits if h != rule_id]

        return [
            {"rule_id": h, "similarity_score": round(s, 3), "potential_conflict": True}
            for h, s in hits[:10]
        ]

    @mcp.tool()
    async def evaluate_compliance(
        diff: str | None = None,
        file_paths: list[str] | None = None,
        intended_action: str | None = None,
        scope: str | None = None,
        facts: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate whether a code change or action complies with applicable rules.

        Use this BEFORE making changes that may be subject to organizational rules.
        Accepts a unified diff, file paths, or a natural language action description.
        Returns ALLOW, DENY, or NEEDS_CONFIRMATION with specific rule citations
        and fix suggestions.

        Args:
            diff: Unified diff text of the code change.
            file_paths: List of file paths being modified.
            intended_action: Natural language description of what you're doing.
            scope: Rule scope filter (e.g., "engineering/python").
            facts: JSON string of key-value context facts.
        """
        import json as json_mod

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.gemini.client import get_gemini_client
        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.evaluation.service import EvaluationService

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            gemini = None
            try:
                gemini = get_gemini_client()
            except Exception:
                pass

            svc = EvaluationService(session, gemini)
            result = await svc.evaluate(
                diff=diff,
                files=[{"path": p} for p in (file_paths or [])],
                facts=json_mod.loads(facts) if facts else None,
                intent=intended_action,
                scope=scope,
                mode="preflight",
            )
            await session.commit()

        return {
            "overall_verdict": result.overall_verdict.value,
            "rules_evaluated": result.rules_evaluated,
            "rules_violated": result.rules_violated,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "rule_statement": v.rule_statement,
                    "issue": v.issue_description,
                    "fix": v.fix_suggestion,
                }
                for v in result.violations
            ],
            "warnings": [
                {
                    "rule_id": w.rule_id,
                    "issue": w.issue_description,
                }
                for w in result.warnings
            ],
            "fix_summary": result.fix_summary,
        }

    @mcp.tool()
    async def get_rules_for_context(
        file_paths: list[str] | None = None,
        repository: str | None = None,
        task_description: str | None = None,
        languages: list[str] | None = None,
        max_rules: int = 15,
        format: str = "instructions",
    ) -> str:
        """Get the rules that apply to your current coding context.

        Call this when you start working on a file or task to understand
        what organizational rules, conventions, and policies apply.
        Returns rules formatted as actionable instructions optimized for
        your context window.

        This is the most important tool for coding agents — use it before
        writing code to know what rules you need to follow.

        Args:
            file_paths: Files you're working on (e.g., ["src/api/payment.py"]).
            repository: Repository name (e.g., "payments-api").
            task_description: What you're doing (e.g., "Adding refund endpoint").
            languages: Programming languages (auto-detected from file paths if omitted).
            max_rules: Maximum rules to return (default 15).
            format: Output format — "instructions" (best for working context),
                    "checklist" (best for PR review), "detailed" (best for learning).
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.context_delivery.service import ContextDeliveryService

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            svc = ContextDeliveryService(session)
            return await svc.get_formatted_rules(
                file_paths=file_paths,
                repository=repository,
                task_description=task_description,
                languages=languages,
                max_rules=max_rules,
                format_type=format,
            )

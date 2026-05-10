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

        hits, total = await es_index.search_fulltext(query, filters=filters, page=1, page_size=top_k)

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
                "preconditions": getattr(r, "preconditions", []) or [],
                "exceptions": getattr(r, "exceptions", []) or [],
                "following_examples": getattr(r, "following_examples", []) or [],
                "violation_examples": getattr(r, "violation_examples", []) or [],
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
            "preconditions": getattr(rule, "preconditions", []) or [],
            "exceptions": getattr(rule, "exceptions", []) or [],
            "following_examples": getattr(rule, "following_examples", []) or [],
            "violation_examples": getattr(rule, "violation_examples", []) or [],
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

        return [{"rule_id": h, "similarity_score": round(s, 3), "potential_conflict": True} for h, s in hits[:10]]

    @mcp.tool()
    async def evaluate_compliance(
        diff: str | None = None,
        file_paths: list[str] | None = None,
        intended_action: str | None = None,
        scope: str | None = None,
        facts: str | None = None,
        environment: str | None = None,
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
            environment: Deployment environment (e.g., "production"). When set,
                evaluation uses the snapshot deployed to this environment.
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
                environment=environment,
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
    async def discover_rules(
        file_contents: str,
        repository: str | None = None,
        sources: list[str] | None = None,
    ) -> str:
        """Discover implicit rules from organizational artifacts. Analyzes code,
        contracts, policies, handbooks, guidelines, and config files to propose
        candidate rules.

        Call this when bootstrapping rules for a new project. Provide the
        contents of relevant files (configs, CLAUDE.md, linter configs,
        representative source files) and the service will extract implicit
        conventions as candidate rules.

        Args:
            file_contents: JSON string mapping file paths to file contents
                (e.g., '{"pyproject.toml": "...", "CLAUDE.md": "..."}').
            repository: Optional repository name or URL.
            sources: Source types to analyze. Defaults to
                ["code_patterns", "linter_config", "claude_md"].
        """
        import json as json_mod

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.gemini.client import get_gemini_client
        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.discovery.service import DiscoveryService

        # Parse file_contents JSON
        try:
            parsed_contents: dict[str, str] = json_mod.loads(file_contents)
        except (json_mod.JSONDecodeError, TypeError) as exc:
            return f"Error: file_contents must be a valid JSON string — {exc}"

        if not isinstance(parsed_contents, dict):
            return "Error: file_contents must be a JSON object mapping paths to content strings."

        effective_sources = sources or ["code_patterns", "linter_config", "claude_md"]

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            gemini = None
            try:
                gemini = get_gemini_client()
            except Exception:
                pass

            svc = DiscoveryService(session, gemini)
            scan_id = await svc.start_scan(
                sources=effective_sources,
                file_contents=parsed_contents,
                repository=repository,
            )
            candidates = await svc.get_candidates(scan_id)
            await session.commit()

        # Format as readable text summary
        if not candidates:
            return "No candidate rules discovered from the provided files."

        lines: list[str] = [f"Discovered {len(candidates)} candidate rule(s) (scan {scan_id}):\n"]
        for i, c in enumerate(candidates, 1):
            lines.append(f"  {i}. [{c['source_type']}] (confidence: {c['confidence']:.2f})")
            lines.append(f"     {c['statement']}")
            if c.get("rationale"):
                lines.append(f"     Rationale: {c['rationale']}")
            lines.append("")

        lines.append(
            "Use the REST API POST /api/v1/discovery/scans/{scan_id}/candidates/{id}/approve "
            "to promote candidates to rules."
        )
        return "\n".join(lines)

    @mcp.tool()
    async def get_rules_for_context(
        file_paths: list[str] | None = None,
        repository: str | None = None,
        task_description: str | None = None,
        languages: list[str] | None = None,
        max_rules: int = 15,
        format: str = "instructions",
        federation: str | None = None,
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
            federation: UUID of a federation node. When provided, only rules
                effective in that federation (including inherited/overridden)
                are returned.
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
                federation_id=federation,
            )

    # ------------------------------------------------------------------
    # Domain-specific rule retrieval tools (Phase 7)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_rules_for_contract_review(
        contract_type: str = "other",
        parties: list[str] | None = None,
        governing_law: str | None = None,
        language: str = "ja",
        max_rules: int = 15,
        format: str = "instructions",
    ) -> str:
        """Get applicable rules for reviewing a contract. This is the primary
        tool for legal review agents.

        Call this when reviewing a contract, NDA, service agreement, or any
        legal document to understand what organizational and regulatory rules
        apply to the contract type and jurisdiction.

        Args:
            contract_type: Type of contract — nda, employment, service,
                procurement, license, or other.
            parties: Party names involved (e.g., ["Acme Corp", "Beta Inc"]).
            governing_law: Governing law jurisdiction (e.g., "Japan", "US-CA").
            language: Primary language of the contract (default "ja").
            max_rules: Maximum rules to return (default 15).
            format: Output format — "instructions", "checklist", or "detailed".
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.context_delivery.service import ContextDeliveryService

        task_desc = f"Reviewing {contract_type} contract"
        if parties:
            task_desc += f" between {', '.join(parties)}"
        if governing_law:
            task_desc += f" (governing law: {governing_law})"

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            svc = ContextDeliveryService(session)
            return await svc.get_formatted_rules(
                task_description=task_desc,
                max_rules=max_rules,
                format_type=format,
                scope=f"legal/contract/{contract_type}" if contract_type != "other" else "legal/contract",
                subject_types=["clause_set"],
                department="legal",
                language=language,
            )

    @mcp.tool()
    async def get_rules_for_transaction(
        transaction_type: str = "other",
        amount: float | None = None,
        department: str | None = None,
        actor_role: str | None = None,
        max_rules: int = 15,
        format: str = "instructions",
    ) -> str:
        """Get applicable rules for validating a business transaction. This is
        the primary tool for finance, HR, and automation agents.

        Call this when processing expense claims, purchase orders, attendance
        records, payroll entries, or journal entries to understand what policies
        and regulations apply.

        Args:
            transaction_type: Type — expense, purchase_order, attendance,
                payroll, journal_entry, or other.
            amount: Transaction amount (for threshold-based rule selection).
            department: Department of the actor (e.g., "sales", "engineering").
            actor_role: Role of the actor (e.g., "manager", "employee").
            max_rules: Maximum rules to return (default 15).
            format: Output format — "instructions", "checklist", or "detailed".
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.context_delivery.service import ContextDeliveryService

        # Map transaction type to scope
        type_to_scope: dict[str, str] = {
            "expense": "finance/expense",
            "purchase_order": "finance/procurement",
            "attendance": "hr/attendance",
            "payroll": "hr/payroll",
            "journal_entry": "finance/accounting",
        }
        scope = type_to_scope.get(transaction_type, "finance")

        # Map transaction type to subject types
        subject_types = ["transaction", "event"]

        # Map to department
        type_to_dept: dict[str, str] = {
            "expense": "finance",
            "purchase_order": "finance",
            "attendance": "hr",
            "payroll": "hr",
            "journal_entry": "finance",
        }
        dept = department or type_to_dept.get(transaction_type)

        task_desc = f"Validating {transaction_type} transaction"
        if amount is not None:
            task_desc += f" (amount: {amount})"
        if actor_role:
            task_desc += f" by {actor_role}"

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            svc = ContextDeliveryService(session)
            return await svc.get_formatted_rules(
                task_description=task_desc,
                max_rules=max_rules,
                format_type=format,
                scope=scope,
                subject_types=subject_types,
                department=dept,
            )

    @mcp.tool()
    async def get_rules_for_communication(
        channel: str = "email",
        audience: str = "external",
        content_type: str = "general",
        max_rules: int = 15,
        format: str = "instructions",
    ) -> str:
        """Get applicable rules for reviewing communications. This is the
        primary tool for content review and compliance agents.

        Call this when drafting or reviewing emails, Slack messages, social
        media posts, press releases, or any external communications to
        understand what policies and regulations apply.

        Args:
            channel: Communication channel — email, slack, social,
                press_release, customer_facing, or other.
            audience: Target audience — internal, external, or regulatory.
            content_type: Content category — marketing, legal, general,
                sales, or hr.
            max_rules: Maximum rules to return (default 15).
            format: Output format — "instructions", "checklist", or "detailed".
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.context_delivery.service import ContextDeliveryService

        # Map content type to department
        content_to_dept: dict[str, str] = {
            "marketing": "marketing",
            "legal": "legal",
            "sales": "sales",
            "hr": "hr",
        }
        dept = content_to_dept.get(content_type)

        task_desc = f"Reviewing {channel} communication for {audience} audience ({content_type} content)"
        scope = f"communications/{channel}" if channel != "other" else "communications"

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            svc = ContextDeliveryService(session)
            return await svc.get_formatted_rules(
                task_description=task_desc,
                max_rules=max_rules,
                format_type=format,
                scope=scope,
                subject_types=["creative", "document"],
                department=dept,
            )

    # ------------------------------------------------------------------
    # Domain-specific evaluation tools (Phase 7)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def evaluate_contract(
        contract_text: str,
        contract_type: str = "other",
        language: str = "ja",
        focus_areas: list[str] | None = None,
    ) -> dict[str, Any]:
        """Evaluate a contract or contract clause against applicable rules.

        Use this to check whether contract language complies with organizational
        policies and legal requirements. Returns verdicts with clause-level
        remediations.

        Args:
            contract_text: The contract text or clause to evaluate.
            contract_type: Type — nda, employment, service, procurement,
                license, or other.
            language: Contract language (default "ja").
            focus_areas: Optional areas to focus on (e.g., ["liability",
                "ip", "termination", "indemnity"]).
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.gemini.client import get_gemini_client
        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.evaluation.service import EvaluationService

        scope = f"legal/contract/{contract_type}" if contract_type != "other" else "legal/contract"
        payload: dict[str, Any] = {
            "clause_text": contract_text,
            "clause_type": contract_type,
        }
        if focus_areas:
            payload["focus_areas"] = focus_areas
        if language:
            payload["language"] = language

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            gemini = None
            try:
                gemini = get_gemini_client()
            except Exception:
                pass

            svc = EvaluationService(session, gemini)
            result = await svc.evaluate_subject(
                surface="contract",
                subject_payload=payload,
                mode="preflight",
                scope=scope,
            )
            await session.commit()

        return {
            "surface": "contract",
            "contract_type": contract_type,
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
    async def evaluate_transaction(
        transaction_payload: str,
        transaction_type: str = "other",
        actor_role: str | None = None,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate a business transaction against applicable rules.

        Use this to check whether an expense claim, purchase order, attendance
        record, or other transaction complies with organizational policies.
        Returns verdicts with field-level remediations.

        Args:
            transaction_payload: JSON string of the transaction record
                (e.g., '{{"amount_jpy": 30000, "category": "entertainment"}}').
            transaction_type: Type — expense, purchase_order, attendance,
                payroll, journal_entry, or other.
            actor_role: Role of the person submitting (e.g., "manager").
            department: Department context (e.g., "sales").
        """
        import json as json_mod

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.gemini.client import get_gemini_client
        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.evaluation.service import EvaluationService

        payload = json_mod.loads(transaction_payload) if isinstance(transaction_payload, str) else transaction_payload
        payload["transaction_type"] = transaction_type
        if actor_role:
            payload["actor_role"] = actor_role
        if department:
            payload["department"] = department

        type_to_scope: dict[str, str] = {
            "expense": "finance/expense",
            "purchase_order": "finance/procurement",
            "attendance": "hr/attendance",
            "payroll": "hr/payroll",
            "journal_entry": "finance/accounting",
        }
        scope = type_to_scope.get(transaction_type, "finance")

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            gemini = None
            try:
                gemini = get_gemini_client()
            except Exception:
                pass

            svc = EvaluationService(session, gemini)
            result = await svc.evaluate_subject(
                surface="transaction",
                subject_payload=payload,
                mode="preflight",
                scope=scope,
            )
            await session.commit()

        return {
            "surface": "transaction",
            "transaction_type": transaction_type,
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
    async def evaluate_communication(
        text: str,
        channel: str = "email",
        audience: str = "external",
        language: str = "ja",
    ) -> dict[str, Any]:
        """Evaluate a communication draft against applicable rules.

        Use this to check whether an email, Slack message, press release,
        or other communication complies with messaging policies, data
        protection rules, and regulatory requirements.

        Args:
            text: The message content to evaluate.
            channel: Communication channel — email, slack, social,
                press_release, customer_facing, or other.
            audience: Target audience — internal, external, or regulatory.
            language: Message language (default "ja").
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.gemini.client import get_gemini_client
        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.evaluation.service import EvaluationService

        payload: dict[str, Any] = {
            "content": text,
            "channel": channel,
            "audience": audience,
            "language": language,
        }

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            gemini = None
            try:
                gemini = get_gemini_client()
            except Exception:
                pass

            svc = EvaluationService(session, gemini)
            result = await svc.evaluate_subject(
                surface="message",
                subject_payload=payload,
                mode="sidecar",
                scope=f"communications/{channel}" if channel != "other" else "communications",
            )
            await session.commit()

        return {
            "surface": "message",
            "channel": channel,
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

    # ------------------------------------------------------------------
    # Governance Proposals (Phase 6a)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def create_proposal(
        proposal_type: str,
        title: str,
        description: str = "",
        target_rule_ids: list[str] | None = None,
        change_spec: dict[str, Any] | None = None,
        required_approvers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a governance proposal for rule changes.

        Use this when you want to propose creating, modifying, or retiring
        a rule through the proper governance workflow. The proposal goes
        through draft → review → approval → enactment.

        Args:
            proposal_type: Type of change — create, amend, retire, merge, split, override.
            title: Short title describing the proposed change.
            description: Detailed description with motivation (Markdown).
            target_rule_ids: Rule IDs being changed (required for amend, retire, merge, split).
            change_spec: Structured description of changes. For create: {"new_rule_data": {...}}.
                For amend: {"fields_changed": {"statement": {"old": "...", "new": "..."}}}.
            required_approvers: User IDs who must approve before enactment.
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.proposals.service import ProposalService

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            svc = ProposalService(session)
            result = await svc.create_proposal(
                proposal_type=proposal_type,
                title=title,
                description=description,
                target_rule_ids=target_rule_ids,
                change_spec=change_spec,
                required_approvers=required_approvers,
            )
            await session.commit()
            return result

    @mcp.tool()
    async def get_proposal_status(proposal_id: str) -> dict[str, Any]:
        """Check the current status of a governance proposal.

        Use this to see where a proposal is in the review process,
        who has voted, and whether there are conflicts or comments.

        Args:
            proposal_id: UUID of the proposal.
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.proposals.service import ProposalService

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            svc = ProposalService(session)
            return await svc.get_proposal(proposal_id)

    # ------------------------------------------------------------------
    # Agent Governance (Phase 6b)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def register_agent(
        agent_id: str,
        display_name: str,
        agent_type: str = "coding_assistant",
        capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        """Register this agent with the governance system.

        Call once at agent initialization. Returns existing profile if
        already registered. This enables personalized rule delivery,
        trust level progression, and governance participation.

        Args:
            agent_id: Unique identifier for this agent.
            display_name: Human-readable name.
            agent_type: Type: coding_assistant, code_reviewer, security_scanner, deployment_agent, custom.
            capabilities: What this agent can do (e.g., ["write_code", "review_pr"]).
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.agent_governance.service import AgentGovernanceService

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            svc = AgentGovernanceService(session)
            result = await svc.register_agent(
                agent_id=agent_id,
                display_name=display_name,
                agent_type=agent_type,
                capabilities=capabilities,
            )
            await session.commit()
            return result

    @mcp.tool()
    async def get_personalized_rules(
        agent_id: str,
        file_paths: list[str] | None = None,
        max_rules: int = 20,
    ) -> dict[str, Any]:
        """Get rules personalized to this agent's history and current task.

        Returns rules weighted by your violation patterns, with mastered
        rules suppressed. Use this instead of generic rule fetching for
        a more efficient and relevant rule set.

        Args:
            agent_id: Your agent ID (must be registered first).
            file_paths: Files you're working on (for scope matching).
            max_rules: Maximum number of rules to return.
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.agent_governance.service import AgentGovernanceService

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            svc = AgentGovernanceService(session)
            return await svc.get_personalized_rules(
                agent_id=agent_id,
                file_paths=file_paths,
                max_rules=max_rules,
            )

    @mcp.tool()
    async def challenge_verdict(
        agent_id: str,
        evaluation_id: str,
        rule_id: str,
        counter_argument: str,
        proposed_action: str = "proceed_with_justification",
    ) -> dict[str, Any]:
        """Challenge a verdict you disagree with.

        Provide a counter-argument explaining why the rule doesn't apply
        in this context. This creates an audit trail and may trigger
        rule improvements if similar challenges accumulate.

        Args:
            agent_id: Your agent ID.
            evaluation_id: ID of the evaluation being challenged.
            rule_id: ID of the rule that produced the verdict.
            counter_argument: Why you disagree with the verdict.
            proposed_action: What you want to do — proceed_with_justification,
                request_exception, or request_amendment.
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.agent_governance.service import AgentGovernanceService

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            svc = AgentGovernanceService(session)
            result = await svc.challenge_verdict(
                agent_id=agent_id,
                evaluation_id=evaluation_id,
                rule_id=rule_id,
                original_verdict="DENY",
                counter_argument=counter_argument,
                proposed_action=proposed_action,
            )
            await session.commit()
            return result

    @mcp.tool()
    async def request_exception(
        agent_id: str,
        rule_id: str,
        context: str,
        proposed_exception: str,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Request a formal exception to a rule for a specific context.

        If similar exceptions are requested frequently, the system may
        auto-draft a rule amendment proposal.

        Args:
            agent_id: Your agent ID.
            rule_id: ID of the rule to request an exception for.
            context: The specific context where the exception applies.
            proposed_exception: What the exception should be.
            evidence: Supporting evidence (e.g., file paths, diffs).
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.agent_governance.service import AgentGovernanceService

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            svc = AgentGovernanceService(session)
            result = await svc.request_exception(
                agent_id=agent_id,
                rule_id=rule_id,
                context=context,
                proposed_exception=proposed_exception,
                evidence=evidence,
            )
            await session.commit()
            return result

    # ------------------------------------------------------------------
    # Surface-aware tools (Phase 8+)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def evaluate_subject(
        surface: str,
        subject_payload: str,
        mode: str = "preflight",
        scope: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate a subject against applicable rules for any surface.

        This is the surface-aware evaluation tool. Use it for contract
        reviews, HR event checks, transaction audits, message compliance,
        or any non-code evaluation.

        Args:
            surface: Surface type — one of: code, contract, human_action,
                transaction, document, message, generic.
            subject_payload: JSON string with surface-specific fields.
                For code: {"diff": "..."}
                For contract: {"clause_text": "...", "clause_type": "indemnity", "parties": ["A", "B"]}
                For human_action: {"action": "register_overtime", "actor_id": "E001", "facts": {"hours": 50}}
                For transaction: {"transaction_type": "expense", "amount": 5000, "description": "..."}
                For document: {"content": "...", "document_type": "policy", "title": "..."}
                For message: {"content": "...", "channel": "slack", "sender": "..."}
                For generic: {"content": "...", "description": "..."}
            mode: Evaluation mode — preflight (default), posthoc, or sidecar.
            scope: Optional rule scope filter.
        """
        import json as json_mod

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.gemini.client import get_gemini_client
        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.evaluation.service import EvaluationService

        payload = json_mod.loads(subject_payload) if isinstance(subject_payload, str) else subject_payload

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            gemini = None
            try:
                gemini = get_gemini_client()
            except Exception:
                pass

            svc = EvaluationService(session, gemini)
            result = await svc.evaluate_subject(
                surface=surface,
                subject_payload=payload,
                mode=mode,
                scope=scope,
            )
            await session.commit()

        return {
            "surface": surface,
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
    async def list_available_surfaces() -> list[dict[str, Any]]:
        """List all registered evaluation surfaces and their capabilities.

        Returns information about each surface including its name,
        default audit retention, and a description.
        """
        from rulerepo_server.services.evaluation.surfaces import (
            get_surface_adapter,
            list_surfaces,
        )

        result = []
        for surface in list_surfaces():
            adapter = get_surface_adapter(surface)
            result.append(
                {
                    "surface": surface.value,
                    "adapter": type(adapter).__name__,
                    "default_retention_days": adapter.default_audit_retention_days,
                    "prompt_hints_available": bool(adapter.get_prompt_hints()),
                }
            )
        return result

    # ------------------------------------------------------------------
    # Norm Lineage tools (Phase 10)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def lookup_norm_lineage(
        rule_id: str,
        direction: str = "upstream",
        max_depth: int = 20,
    ) -> dict[str, Any]:
        """Look up the norm lineage chain for a rule.

        Walks the DERIVES_FROM relationship chain to find upstream
        authorities (laws, regulations) or downstream derivatives.

        Args:
            rule_id: ID of the rule to query.
            direction: "upstream" (toward laws) or "downstream" (toward operational rules).
            max_depth: Maximum chain depth to traverse.
        """
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.norm_lineage.walker import NormLineageWalker

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            walker = NormLineageWalker(session)
            if direction == "downstream":
                chain = await walker.downstream(rule_id, max_depth=max_depth)
            else:
                chain = await walker.upstream(rule_id, max_depth=max_depth)

        return {
            "rule_id": rule_id,
            "direction": direction,
            "chain": [
                {
                    "rule_id": n.rule_id,
                    "statement": n.statement,
                    "norm_tier": n.norm_tier,
                    "norm_authority": n.norm_authority,
                    "depth": n.depth,
                }
                for n in chain.nodes
            ],
        }

    # ------------------------------------------------------------------
    # Contract tools (Phase 9)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def find_clause_conflicts(
        contract_text: str,
        scope: str = "legal/contract",
    ) -> dict[str, Any]:
        """Find policy conflicts in contract clauses.

        Evaluates the contract text against applicable rules on the
        Contract surface and returns any conflicts found.

        Args:
            contract_text: The contract text or clause to check.
            scope: Rule scope filter (default: legal/contract).
        """
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
            result = await svc.evaluate_subject(
                surface="contract",
                subject_payload={
                    "clause_text": contract_text,
                    "clause_type": "general",
                },
                mode="preflight",
                scope=scope,
            )
            await session.commit()

        return {
            "conflicts_found": result.rules_violated,
            "conflicts": [
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
        }

    # ------------------------------------------------------------------
    # Human action tools (Phase 11)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def check_action(
        actor: str,
        action: str,
        payload: str,
    ) -> dict[str, Any]:
        """Check if a human action complies with applicable rules.

        Evaluates actions like overtime registration, leave requests,
        expense claims, etc. against HR and organizational rules.

        Args:
            actor: Actor identifier (e.g., "user:E001").
            action: Action type (e.g., "register_overtime", "submit_leave_request").
            payload: JSON string with action-specific facts.
        """
        import json as json_mod

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rulerepo_server.adapters.gemini.client import get_gemini_client
        from rulerepo_server.adapters.postgres.session import get_engine
        from rulerepo_server.services.evaluation.service import EvaluationService

        facts = json_mod.loads(payload) if isinstance(payload, str) else payload

        engine = get_engine()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            gemini = None
            try:
                gemini = get_gemini_client()
            except Exception:
                pass

            svc = EvaluationService(session, gemini)
            result = await svc.evaluate_subject(
                surface="human_action",
                subject_payload={
                    "action": action,
                    "actor_id": actor,
                    "facts": facts,
                },
                mode="preflight",
            )
            await session.commit()

        return {
            "actor": actor,
            "action": action,
            "overall_verdict": result.overall_verdict.value,
            "rules_evaluated": result.rules_evaluated,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "issue": v.issue_description,
                    "fix": v.fix_suggestion,
                }
                for v in result.violations
            ],
        }

    # ------------------------------------------------------------------
    # Communication review tool (Phase 11)
    # ------------------------------------------------------------------

    @mcp.tool()
    async def review_communication(
        channel: str,
        content: str,
        sender: str = "",
        recipients: str = "",
    ) -> dict[str, Any]:
        """Review a communication for compliance with messaging rules.

        Checks email, Slack, or Teams messages against communication
        policies (harassment, confidentiality, data leakage, etc.).

        Args:
            channel: Communication channel (email, slack, teams).
            content: The message content to review.
            sender: Sender identifier.
            recipients: Comma-separated recipient list.
        """
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
            result = await svc.evaluate_subject(
                surface="message",
                subject_payload={
                    "content": content,
                    "channel": channel,
                    "sender": sender,
                    "recipients": [r.strip() for r in recipients.split(",") if r.strip()],
                },
                mode="sidecar",
            )
            await session.commit()

        return {
            "channel": channel,
            "overall_verdict": result.overall_verdict.value,
            "rules_evaluated": result.rules_evaluated,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "issue": v.issue_description,
                }
                for v in result.violations
            ],
        }

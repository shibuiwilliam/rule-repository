"""Rule service — orchestrates rule CRUD across Postgres, Elasticsearch, and Neo4j."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.elasticsearch.rule_index import ElasticsearchRuleIndex
from rulerepo_server.adapters.gemini.embeddings import generate_embedding
from rulerepo_server.adapters.neo4j.graph_repo import Neo4jGraphRepository
from rulerepo_server.adapters.postgres.audit_repo import AuditLogRepository
from rulerepo_server.adapters.postgres.rule_repo import PostgresRuleRepository
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.rule import RuleStatus, validate_status_transition
from rulerepo_server.schemas.rule import RuleCreate, RuleUpdate

logger = get_logger(__name__)


class RuleService:
    """Coordinates rule operations across all data stores.

    Every write goes to Postgres (source of truth), Elasticsearch (search index),
    and Neo4j (relationship graph). If ES or Neo4j fails, the error is logged but
    does not roll back the Postgres write — the reconciler script is the safety net.
    """

    def __init__(
        self,
        session: AsyncSession,
        es_index: ElasticsearchRuleIndex,
        graph_repo: Neo4jGraphRepository,
        gemini_client: Any | None = None,
    ) -> None:
        self._rule_repo = PostgresRuleRepository(session)
        self._audit_repo = AuditLogRepository(session)
        self._es_index = es_index
        self._graph_repo = graph_repo
        self._gemini_client = gemini_client
        self._session = session

    async def create_rule(self, data: RuleCreate, actor: str = "system", project_id: str | None = None) -> dict:
        """Create a new rule across all stores.

        Args:
            data: The rule creation data.
            actor: Who is creating the rule.
            project_id: Project to associate the rule with.

        Returns:
            Dictionary representation of the created rule.
        """
        from rulerepo_server.adapters.postgres.models import DEFAULT_PROJECT_ID

        rule_id = uuid4()
        now = datetime.now(UTC)

        # Generate embedding if Gemini client available
        embedding: list[float] = []
        if self._gemini_client:
            try:
                embedding = await generate_embedding(self._gemini_client, data.statement)
            except Exception as exc:
                logger.warning("embedding_generation_failed", error=str(exc))

        # 1. Postgres (source of truth)
        rule_data = {
            "id": rule_id,
            "project_id": project_id or DEFAULT_PROJECT_ID,
            "statement": data.statement,
            "modality": data.modality.value,
            "severity": data.severity.value,
            "status": data.status.value,
            "scope": data.scope,
            "tags": data.tags,
            "rationale": data.rationale,
            "context": data.context,
            "following_examples": data.following_examples,
            "violation_examples": data.violation_examples,
            "preconditions": data.preconditions,
            "exceptions": data.exceptions,
            "source_refs": [ref.model_dump() for ref in data.source_refs],
            "effective_period": data.effective_period.model_dump(),
            "governance": data.governance.model_dump(),
            "embedding": embedding if embedding else None,
            "created_at": now,
            "updated_at": now,
        }
        model = await self._rule_repo.create(rule_data)

        # Create initial revision
        await self._rule_repo.create_revision(
            {
                "id": uuid4(),
                "rule_id": rule_id,
                "revision_number": 1,
                "statement": data.statement,
                "modality": data.modality.value,
                "severity": data.severity.value,
                "status": data.status.value,
                "scope": data.scope,
                "tags": data.tags,
                "rationale": data.rationale,
                "changed_by": actor,
                "change_note": "Initial creation",
                "created_at": now,
            }
        )

        # 2. Elasticsearch (search index)
        try:
            es_doc = {
                "rule_id": str(rule_id),
                "project_id": project_id or DEFAULT_PROJECT_ID,
                "statement": data.statement,
                "modality": data.modality.value,
                "severity": data.severity.value,
                "status": data.status.value,
                "scope": data.scope,
                "tags": data.tags,
                "rationale": data.rationale,
                "context": data.context,
                "effective_from": data.effective_period.valid_from.isoformat()
                if data.effective_period.valid_from
                else None,
                "effective_until": data.effective_period.valid_until.isoformat()
                if data.effective_period.valid_until
                else None,
                "embedding": embedding if embedding else None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            await self._es_index.index_rule(rule_id, es_doc)
        except Exception as exc:
            logger.warning("es_index_failed", rule_id=str(rule_id), error=str(exc))

        # 3. Neo4j (graph node)
        try:
            await self._graph_repo.upsert_rule_node(
                rule_id,
                {
                    "modality": data.modality.value,
                    "severity": data.severity.value,
                    "status": data.status.value,
                    "statement_preview": data.statement[:200],
                },
            )
        except Exception as exc:
            logger.warning("neo4j_upsert_failed", rule_id=str(rule_id), error=str(exc))

        # 4. Audit log
        await self._audit_repo.append(
            action="rule_created",
            actor=actor,
            resource_type="rule",
            resource_id=str(rule_id),
            details={"statement_preview": data.statement[:200]},
        )

        return self._model_to_dict(model)

    async def get_rule(self, rule_id: UUID) -> dict:
        """Get a single rule by ID.

        Args:
            rule_id: The rule's UUID.

        Returns:
            Dictionary representation of the rule.
        """
        model = await self._rule_repo.get_by_id(rule_id)
        return self._model_to_dict(model)

    async def list_rules(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        project_id: str | None = None,
        modality: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        scope: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """List rules with filters and pagination.

        Returns:
            Dictionary with items, total, page, page_size.
        """
        rules, total = await self._rule_repo.list_rules(
            page=page,
            page_size=page_size,
            project_id=project_id,
            modality=modality,
            severity=severity,
            status=status,
            scope=scope,
            tags=tags,
        )
        return {
            "items": [self._model_to_dict(r) for r in rules],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_rule(self, rule_id: UUID, data: RuleUpdate, actor: str = "system") -> dict:
        """Update a rule and create a revision snapshot.

        Args:
            rule_id: The rule's UUID.
            data: Fields to update.
            actor: Who is making the change.

        Returns:
            Dictionary representation of the updated rule.
        """
        # Get current state for revision
        current = await self._rule_repo.get_by_id(rule_id)

        # Build updates dict (only non-None fields)
        updates: dict[str, Any] = {}
        if data.statement is not None:
            updates["statement"] = data.statement
        if data.modality is not None:
            updates["modality"] = data.modality.value
        if data.severity is not None:
            updates["severity"] = data.severity.value
        if data.status is not None:
            try:
                current_status = RuleStatus(current.status)
                validate_status_transition(current_status, data.status)
            except ValueError as exc:
                from rulerepo_server.core.errors import ValidationError

                raise ValidationError(str(exc)) from exc
            updates["status"] = data.status.value
        if data.scope is not None:
            updates["scope"] = data.scope
        if data.tags is not None:
            updates["tags"] = data.tags
        if data.rationale is not None:
            updates["rationale"] = data.rationale
        if data.context is not None:
            updates["context"] = data.context
        if data.preconditions is not None:
            updates["preconditions"] = data.preconditions
        if data.exceptions is not None:
            updates["exceptions"] = data.exceptions
        if data.following_examples is not None:
            updates["following_examples"] = data.following_examples
        if data.violation_examples is not None:
            updates["violation_examples"] = data.violation_examples
        if data.source_refs is not None:
            updates["source_refs"] = [ref.model_dump() for ref in data.source_refs]
        if data.effective_period is not None:
            updates["effective_period"] = data.effective_period.model_dump()
        if data.governance is not None:
            updates["governance"] = data.governance.model_dump()

        updates["updated_at"] = datetime.now(UTC)

        # Regenerate embedding if statement changed
        if data.statement is not None and self._gemini_client:
            try:
                embedding = await generate_embedding(self._gemini_client, data.statement)
                if embedding:
                    updates["embedding"] = embedding
            except Exception as exc:
                logger.warning("embedding_regen_failed", error=str(exc))

        # 1. Create revision before applying updates
        rev_num = await self._rule_repo.get_latest_revision_number(rule_id) + 1
        await self._rule_repo.create_revision(
            {
                "id": uuid4(),
                "rule_id": rule_id,
                "revision_number": rev_num,
                "statement": updates.get("statement", current.statement),
                "modality": updates.get("modality", current.modality),
                "severity": updates.get("severity", current.severity),
                "status": updates.get("status", current.status),
                "scope": updates.get("scope", current.scope),
                "tags": updates.get("tags", current.tags),
                "rationale": updates.get("rationale", current.rationale),
                "changed_by": actor,
                "change_note": data.revision_note,
            }
        )

        # 2. Update Postgres
        model = await self._rule_repo.update(rule_id, updates)

        # 3. Re-index in Elasticsearch
        try:
            es_doc = {
                "rule_id": str(rule_id),
                "project_id": str(model.project_id) if hasattr(model, "project_id") else None,
                "statement": model.statement,
                "modality": model.modality,
                "severity": model.severity,
                "status": model.status,
                "scope": model.scope,
                "tags": model.tags,
                "rationale": model.rationale,
                "effective_from": model.effective_period.get("valid_from")
                if isinstance(model.effective_period, dict)
                else None,
                "effective_until": model.effective_period.get("valid_until")
                if isinstance(model.effective_period, dict)
                else None,
                "embedding": model.embedding,
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None,
            }
            await self._es_index.index_rule(rule_id, es_doc)
        except Exception as exc:
            logger.warning("es_reindex_failed", rule_id=str(rule_id), error=str(exc))

        # 4. Update Neo4j
        try:
            await self._graph_repo.upsert_rule_node(
                rule_id,
                {
                    "modality": model.modality,
                    "severity": model.severity,
                    "status": model.status,
                    "statement_preview": model.statement[:200],
                },
            )
        except Exception as exc:
            logger.warning("neo4j_update_failed", rule_id=str(rule_id), error=str(exc))

        # 5. Audit log
        await self._audit_repo.append(
            action="rule_updated",
            actor=actor,
            resource_type="rule",
            resource_id=str(rule_id),
            details={"revision": rev_num, "note": data.revision_note},
        )

        return self._model_to_dict(model)

    async def retire_rule(self, rule_id: UUID, actor: str = "system") -> dict:
        """Retire a rule by setting valid_until to now. Never deletes.

        Args:
            rule_id: The rule's UUID.
            actor: Who is retiring the rule.

        Returns:
            Dictionary representation of the retired rule.
        """
        now = datetime.now(UTC)
        updates = {
            "status": "RETIRED",
            "effective_period": {"valid_from": None, "valid_until": now.isoformat()},
            "updated_at": now,
        }
        model = await self._rule_repo.update(rule_id, updates)

        # Update ES and Neo4j
        try:
            await self._es_index.index_rule(
                rule_id,
                {
                    "rule_id": str(rule_id),
                    "project_id": str(model.project_id) if hasattr(model, "project_id") else None,
                    "statement": model.statement,
                    "modality": model.modality,
                    "severity": model.severity,
                    "status": "RETIRED",
                    "scope": model.scope,
                    "tags": model.tags,
                    "updated_at": now.isoformat(),
                },
            )
        except Exception as exc:
            logger.warning("es_retire_failed", error=str(exc))

        try:
            await self._graph_repo.upsert_rule_node(rule_id, {"status": "RETIRED"})
        except Exception as exc:
            logger.warning("neo4j_retire_failed", error=str(exc))

        await self._audit_repo.append(
            action="rule_retired",
            actor=actor,
            resource_type="rule",
            resource_id=str(rule_id),
        )

        return self._model_to_dict(model)

    async def get_revisions(self, rule_id: UUID) -> list[dict]:
        """Get all revisions for a rule.

        Args:
            rule_id: The rule's UUID.

        Returns:
            List of revision dictionaries.
        """
        revisions = await self._rule_repo.get_revisions(rule_id)
        return [
            {
                "id": str(r.id),
                "rule_id": str(r.rule_id),
                "revision_number": r.revision_number,
                "statement": r.statement,
                "modality": r.modality,
                "severity": r.severity,
                "status": r.status,
                "scope": r.scope,
                "tags": r.tags,
                "rationale": r.rationale,
                "changed_by": r.changed_by,
                "change_note": r.change_note,
                "created_at": r.created_at,
            }
            for r in revisions
        ]

    async def add_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        relationship_type: str,
        actor: str = "system",
    ) -> dict:
        """Create a relationship between two rules in Postgres and Neo4j.

        Args:
            source_id: Source rule UUID.
            target_id: Target rule UUID.
            relationship_type: Type of relationship.
            actor: Who is creating the relationship.

        Returns:
            Dictionary with relationship details.
        """
        rel_data = {
            "id": uuid4(),
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": relationship_type,
            "created_by": actor,
        }
        model = await self._rule_repo.create_relationship(rel_data)

        try:
            await self._graph_repo.create_relationship(source_id, target_id, relationship_type)
        except Exception as exc:
            logger.warning("neo4j_rel_create_failed", error=str(exc))

        await self._audit_repo.append(
            action="relationship_created",
            actor=actor,
            resource_type="rule_relationship",
            resource_id=f"{source_id}->{target_id}",
            details={"type": relationship_type},
        )

        return {
            "source_id": str(model.source_id),
            "target_id": str(model.target_id),
            "relationship_type": model.relationship_type,
            "created_at": model.created_at,
            "created_by": model.created_by,
        }

    async def remove_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        relationship_type: str,
        actor: str = "system",
    ) -> None:
        """Remove a relationship between two rules.

        Args:
            source_id: Source rule UUID.
            target_id: Target rule UUID.
            relationship_type: Type of relationship to remove.
            actor: Who is removing the relationship.
        """
        await self._rule_repo.delete_relationship(source_id, target_id, relationship_type)

        try:
            await self._graph_repo.delete_relationship(source_id, target_id, relationship_type)
        except Exception as exc:
            logger.warning("neo4j_rel_delete_failed", error=str(exc))

        await self._audit_repo.append(
            action="relationship_deleted",
            actor=actor,
            resource_type="rule_relationship",
            resource_id=f"{source_id}->{target_id}",
            details={"type": relationship_type},
        )

    async def get_relationships(self, rule_id: UUID) -> list[dict]:
        """Get all relationships involving a rule.

        Args:
            rule_id: The rule's UUID.

        Returns:
            List of relationship dictionaries.
        """
        rels = await self._rule_repo.get_relationships(rule_id)
        return [
            {
                "source_id": str(r.source_id),
                "target_id": str(r.target_id),
                "relationship_type": r.relationship_type,
                "created_at": r.created_at,
                "created_by": r.created_by,
            }
            for r in rels
        ]

    async def get_graph(self, rule_id: UUID, depth: int = 1) -> dict:
        """Get the relationship subgraph around a rule from Neo4j.

        Args:
            rule_id: The rule's UUID.
            depth: Traversal depth.

        Returns:
            Dictionary with nodes and edges.
        """
        try:
            return await self._graph_repo.get_subgraph([rule_id], depth=depth)
        except Exception as exc:
            logger.warning("neo4j_subgraph_failed", error=str(exc))
            return {"nodes": [], "edges": []}

    @staticmethod
    def _model_to_dict(model: Any) -> dict:
        """Convert a SQLAlchemy RuleModel to a plain dictionary."""
        return {
            "id": str(model.id),
            "project_id": str(model.project_id),
            "maturity_level": getattr(model, "maturity_level", "experimental"),
            "statement": model.statement,
            "modality": model.modality,
            "severity": model.severity,
            "status": model.status,
            "scope": model.scope,
            "tags": model.tags,
            "rationale": model.rationale,
            "context": getattr(model, "context", ""),
            "following_examples": getattr(model, "following_examples", []),
            "violation_examples": getattr(model, "violation_examples", []),
            "preconditions": model.preconditions,
            "exceptions": model.exceptions,
            "source_refs": model.source_refs,
            "effective_period": model.effective_period,
            "governance": model.governance,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

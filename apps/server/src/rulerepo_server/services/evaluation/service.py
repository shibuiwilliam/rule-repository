"""EvaluationService — orchestrates the full evaluation pipeline.

Supports both the legacy code-centric API and the new surface-aware API.
See CLAUDE.md §14.2.3.
"""

from __future__ import annotations

import time
from typing import Any

from google import genai
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.audit_repo import AuditLogRepository
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import EvaluationResult
from rulerepo_server.services.evaluation.batch_evaluator import evaluate_batch
from rulerepo_server.services.evaluation.conflict_aggregator import (
    aggregate_with_conflicts,
)
from rulerepo_server.services.evaluation.context_assembler import assemble_context
from rulerepo_server.services.evaluation.graph_resolver import resolve_evaluation_plan
from rulerepo_server.services.evaluation.rule_selector import select_rules
from rulerepo_server.services.evaluation.verdict_aggregator import aggregate_verdicts

logger = get_logger(__name__)


class EvaluationService:
    """Orchestrates the Subject-Aware Evaluation Engine pipeline.

    Supports two entry points:
    - ``evaluate()``: legacy code-centric API (backwards compatible)
    - ``evaluate_subject()``: new surface-aware API (Phase 8+)

    Pipeline: parse subject → select rules → evaluate each rule → aggregate verdicts.
    """

    def __init__(
        self,
        session: AsyncSession,
        gemini_client: genai.Client | None = None,
    ) -> None:
        self._session = session
        self._gemini_client = gemini_client
        self._audit_repo = AuditLogRepository(session)

    async def evaluate(
        self,
        *,
        diff: str | None = None,
        files: list[dict[str, str]] | None = None,
        facts: dict[str, Any] | None = None,
        intent: str | None = None,
        scope: str | None = None,
        repository: str | None = None,
        mode: str = "preflight",
        max_rules: int = 20,
        severity_min: str = "MEDIUM",
        actor: str | None = None,
        environment: str | None = None,
        agent_id: str | None = None,
        subject_kind: str | None = None,
        surface: str | None = None,
    ) -> EvaluationResult:
        """Run the full evaluation pipeline.

        Args:
            diff: Unified diff text (for code evaluations).
            files: List of {"path": ..., "content": ...} dicts.
            facts: Key-value pairs for non-code evaluations.
            intent: Natural language description of the change.
            scope: Rule scope filter.
            repository: Repository identifier.
            mode: "preflight" or "posthoc".
            max_rules: Maximum rules to evaluate.
            severity_min: Minimum rule severity to include.
            actor: Who triggered the evaluation.
            environment: Deployment environment for snapshot-based evaluation.

        Returns:
            EvaluationResult with overall verdict and per-rule breakdowns.
        """
        start_time = time.time()

        # 1. Assemble context
        # Use explicit surface if provided; otherwise infer from input shape.
        resolved_surface = surface or ("code" if diff else "generic")
        context = assemble_context(
            diff=diff,
            files=files,
            facts=facts,
            intent=intent,
            scope=scope,
            repository=repository,
            actor=actor,
            surface=resolved_surface,
        )

        # 2. Select applicable rules
        modality_filter = ["MUST", "MUST_NOT"]
        if mode == "posthoc":
            modality_filter = ["MUST", "MUST_NOT", "SHOULD"]

        rules = await select_rules(
            self._session,
            context,
            max_rules=max_rules,
            severity_min=severity_min,
            modality_filter=modality_filter,
            scope=scope,
            environment=environment,
            agent_id=agent_id,
            subject_type=subject_kind,
        )

        logger.info(
            "evaluation_rules_selected",
            rules_count=len(rules),
            mode=mode,
            has_diff=bool(diff),
            file_count=len(context.file_paths),
        )

        # 3. If no Gemini client or no rules, return ALLOW
        if not rules:
            return aggregate_verdicts([], [], 0)

        if not self._gemini_client:
            logger.warning("evaluation_no_llm_client")
            return aggregate_verdicts([], [], 0)

        # 4. Resolve relationship graph for conflict-aware evaluation
        rule_id_list = [r["id"] for r in rules]
        try:
            from rulerepo_server.core.feature_flags import get_feature_flags

            flags = get_feature_flags()
            if flags.neo4j_enabled:
                from rulerepo_server.adapters.neo4j.client import get_neo4j_driver
                from rulerepo_server.adapters.neo4j.graph_repo import Neo4jGraphRepository

                graph_repo = Neo4jGraphRepository(get_neo4j_driver())
            else:
                from rulerepo_server.adapters.graph.postgres_adjacency import PostgresGraphRepository

                graph_repo = PostgresGraphRepository(self._session)
            plan = await resolve_evaluation_plan(rule_id_list, graph_repo)
        except Exception as exc:
            logger.warning("graph_resolution_skipped", error=str(exc))
            from rulerepo_server.services.evaluation.graph_resolver import EvaluationPlan

            plan = EvaluationPlan(ordered_rules=rule_id_list)

        # 5. Evaluate each rule (concurrently)
        # Pass LLM cache repo for caching (CLAUDE_ENHANCE.md §0.2)
        cache_repo = None
        try:
            from rulerepo_server.adapters.postgres.cache_repo import LLMCacheRepository

            cache_repo = LLMCacheRepository(self._session)
        except Exception:
            pass

        # Legacy evaluate() always uses code surface (or None for backward compat)
        batch_results = await evaluate_batch(
            rules,
            context,
            self._gemini_client,
            cache_repo=cache_repo,
            evaluation_plan=plan,
        )

        verdicts = []
        model_ids: list[str] = []
        total_rule_latency = 0

        for result_item in batch_results:
            verdict, model_id, latency_ms = result_item
            verdicts.append(verdict)
            model_ids.append(model_id)
            total_rule_latency += latency_ms

        # 6. Conflict-aware aggregation (or simple if no relationships)
        total_latency = int((time.time() - start_time) * 1000)

        if plan.overrides or plan.conflicts or plan.skip_if_denied:
            rule_dict_map = {r["id"]: r for r in rules}
            overall_verdict, conflict_resolutions = aggregate_with_conflicts(verdicts, plan, rule_dict_map)
            eval_result = aggregate_verdicts(verdicts, model_ids, total_latency)
            eval_result.overall_verdict = overall_verdict
            eval_result.conflict_resolutions = [
                {
                    "rule_a_id": cr.rule_a_id,
                    "rule_b_id": cr.rule_b_id,
                    "relationship": cr.relationship,
                    "winner_id": cr.winner_id,
                    "reason": cr.reason,
                    "discarded_verdict": cr.discarded_verdict,
                }
                for cr in conflict_resolutions
            ]
        else:
            eval_result = aggregate_verdicts(verdicts, model_ids, total_latency)

        # 6. Persist evaluation records
        try:
            from rulerepo_server.adapters.postgres.models import (
                DEFAULT_PROJECT_ID,
                EvaluationRecordModel,
            )

            input_type = "code" if diff else "facts"
            eval_scope = scope or ""
            latency_per_rule = [total_rule_latency // max(len(verdicts), 1)] * len(verdicts)
            for i, (v, mid) in enumerate(zip(verdicts, model_ids, strict=False)):
                record = EvaluationRecordModel(
                    project_id=DEFAULT_PROJECT_ID,
                    rule_id=v.rule_id,
                    verdict=v.verdict.value,
                    confidence=v.confidence,
                    latency_ms=latency_per_rule[i] if i < len(latency_per_rule) else 0,
                    scope=eval_scope,
                    input_type=input_type,
                    model_id=mid,
                    cached=False,
                    agent_id=agent_id,
                )
                self._session.add(record)
            await self._session.flush()
        except Exception as exc:
            logger.warning("evaluation_persistence_failed", error=str(exc))

        # 7. Audit log
        await self._audit_repo.append(
            action="evaluate",
            actor=actor or "system",
            resource_type="evaluation",
            resource_id=eval_result.evaluation_id,
            details={
                "overall_verdict": eval_result.overall_verdict.value,
                "rules_evaluated": eval_result.rules_evaluated,
                "rules_violated": eval_result.rules_violated,
                "mode": mode,
                "has_diff": bool(diff),
                "file_paths": context.file_paths[:10],
                "model_ids": list(set(model_ids)),
                "latency_ms": total_latency,
            },
        )

        logger.info(
            "evaluation_complete",
            evaluation_id=eval_result.evaluation_id,
            verdict=eval_result.overall_verdict.value,
            rules_evaluated=eval_result.rules_evaluated,
            violations=eval_result.rules_violated,
            latency_ms=total_latency,
        )

        return eval_result

    async def get_applicable_rules(
        self,
        *,
        file_paths: list[str] | None = None,
        repository: str | None = None,
        scope: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get rules that would apply to given file paths, without running evaluation.

        Args:
            file_paths: List of file paths to check.
            repository: Repository identifier.
            scope: Rule scope filter.

        Returns:
            List of applicable rule dicts.
        """
        context = assemble_context(
            files=[{"path": p} for p in (file_paths or [])],
            repository=repository,
            scope=scope,
        )
        return await select_rules(
            self._session,
            context,
            max_rules=50,
            severity_min="LOW",
            modality_filter=["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"],
            scope=scope,
        )

    # ------------------------------------------------------------------
    # Surface-aware evaluation (Phase 8+)
    # ------------------------------------------------------------------

    async def evaluate_subject(
        self,
        *,
        surface: str,
        subject_payload: dict[str, Any],
        mode: str = "preflight",
        max_rules: int = 20,
        severity_min: str = "MEDIUM",
        scope: str | None = None,
    ) -> EvaluationResult:
        """Evaluate a subject against applicable rules using the surface adapter.

        This is the new surface-aware entry point. It dispatches to the
        appropriate surface adapter for parsing, then runs the universal
        evaluation pipeline.

        Args:
            surface: Surface name (e.g., "code", "contract", "human_action").
            subject_payload: Surface-specific payload dict.
            mode: "preflight", "posthoc", or "sidecar".
            max_rules: Maximum rules to evaluate.
            severity_min: Minimum rule severity to include.
            scope: Optional scope override (if not provided, adapter resolves it).

        Returns:
            EvaluationResult with overall verdict and per-rule breakdowns.
        """
        from rulerepo_server.services.evaluation.surfaces import get_surface_adapter

        start_time = time.time()

        # 1. Resolve surface adapter and parse payload
        adapter = get_surface_adapter(surface)
        subject = await adapter.parse(subject_payload)

        # Resolve scope from adapter if not explicitly provided
        resolved_scope = scope or (adapter.resolve_scopes(subject_payload) or [None])[0]

        # 2. Build an EvaluationContext from the parsed subject
        # This bridges the surface-aware API to the existing pipeline
        context = assemble_context(
            diff=subject.payload.get("diff"),
            files=None,
            facts={**subject.facts, **subject.payload},
            intent=subject.description,
            scope=resolved_scope,
            actor=subject.actor.identifier if subject.actor else None,
            surface=surface,
        )

        # 3. Select applicable rules
        modality_filter = ["MUST", "MUST_NOT"]
        if mode == "posthoc":
            modality_filter = ["MUST", "MUST_NOT", "SHOULD"]
        elif mode == "sidecar":
            modality_filter = ["MUST", "MUST_NOT", "SHOULD", "MAY"]

        # Map surface to subject_type for rule selector filtering
        surface_to_subject_type: dict[str, str] = {
            "code": "code_diff",
            "contract": "clause_set",
            "human_action": "event",
            "transaction": "transaction",
            "document": "document",
            "message": "creative",  # closest existing SubjectKind
            "generic": None,
        }
        subject_type = surface_to_subject_type.get(surface)

        rules = await select_rules(
            self._session,
            context,
            max_rules=max_rules,
            severity_min=severity_min,
            modality_filter=modality_filter,
            scope=resolved_scope,
            subject_type=subject_type,
        )

        logger.info(
            "surface_evaluation_rules_selected",
            surface=surface,
            rules_count=len(rules),
            mode=mode,
            subject_id=subject.identifier,
        )

        # 4. Early return if no rules or no LLM
        if not rules:
            return aggregate_verdicts([], [], 0)
        if not self._gemini_client:
            logger.warning("evaluation_no_llm_client", surface=surface)
            return aggregate_verdicts([], [], 0)

        # 5. Resolve graph relationships
        rule_id_list = [r["id"] for r in rules]
        try:
            from rulerepo_server.core.feature_flags import get_feature_flags

            flags = get_feature_flags()
            if flags.neo4j_enabled:
                from rulerepo_server.adapters.neo4j.client import get_neo4j_driver
                from rulerepo_server.adapters.neo4j.graph_repo import Neo4jGraphRepository

                graph_repo = Neo4jGraphRepository(get_neo4j_driver())
            else:
                from rulerepo_server.adapters.graph.postgres_adjacency import PostgresGraphRepository

                graph_repo = PostgresGraphRepository(self._session)
            plan = await resolve_evaluation_plan(rule_id_list, graph_repo)
        except Exception as exc:
            logger.warning("graph_resolution_skipped", error=str(exc))
            from rulerepo_server.services.evaluation.graph_resolver import EvaluationPlan

            plan = EvaluationPlan(ordered_rules=rule_id_list)

        # 6. Evaluate rules
        cache_repo = None
        try:
            from rulerepo_server.adapters.postgres.cache_repo import LLMCacheRepository

            cache_repo = LLMCacheRepository(self._session)
        except Exception:
            pass

        batch_results = await evaluate_batch(
            rules,
            context,
            self._gemini_client,
            cache_repo=cache_repo,
            evaluation_plan=plan,
            surface=surface,
        )

        verdicts = []
        model_ids: list[str] = []
        total_rule_latency = 0
        for verdict, model_id, latency_ms in batch_results:
            verdicts.append(verdict)
            model_ids.append(model_id)
            total_rule_latency += latency_ms

        # 7. Aggregate
        total_latency = int((time.time() - start_time) * 1000)
        if plan.overrides or plan.conflicts or plan.skip_if_denied:
            rule_dict_map = {r["id"]: r for r in rules}
            overall_verdict, conflict_resolutions = aggregate_with_conflicts(verdicts, plan, rule_dict_map)
            eval_result = aggregate_verdicts(verdicts, model_ids, total_latency)
            eval_result.overall_verdict = overall_verdict
            eval_result.conflict_resolutions = [
                {
                    "rule_a_id": cr.rule_a_id,
                    "rule_b_id": cr.rule_b_id,
                    "relationship": cr.relationship,
                    "winner_id": cr.winner_id,
                    "reason": cr.reason,
                    "discarded_verdict": cr.discarded_verdict,
                }
                for cr in conflict_resolutions
            ]
        else:
            eval_result = aggregate_verdicts(verdicts, model_ids, total_latency)

        # 8. Persist evaluation records with surface metadata
        try:
            from rulerepo_server.adapters.postgres.models import (
                DEFAULT_PROJECT_ID,
                EvaluationRecordModel,
            )

            eval_scope = resolved_scope or ""
            latency_per_rule = [total_rule_latency // max(len(verdicts), 1)] * len(verdicts)
            for i, (v, mid) in enumerate(zip(verdicts, model_ids, strict=False)):
                record = EvaluationRecordModel(
                    project_id=DEFAULT_PROJECT_ID,
                    rule_id=v.rule_id,
                    verdict=v.verdict.value,
                    confidence=v.confidence,
                    latency_ms=latency_per_rule[i] if i < len(latency_per_rule) else 0,
                    scope=eval_scope,
                    input_type=surface,
                    model_id=mid,
                    cached=False,
                )
                self._session.add(record)
            await self._session.flush()
        except Exception as exc:
            logger.warning("evaluation_persistence_failed", error=str(exc))

        # 9. Audit log with surface metadata
        actor_str = subject.actor.identifier if subject.actor else "system"
        await self._audit_repo.append(
            action="evaluate",
            actor=actor_str,
            resource_type="evaluation",
            resource_id=eval_result.evaluation_id,
            details={
                "overall_verdict": eval_result.overall_verdict.value,
                "rules_evaluated": eval_result.rules_evaluated,
                "rules_violated": eval_result.rules_violated,
                "mode": mode,
                "surface": surface,
                "subject_id": subject.identifier,
                "locale": subject.locale,
                "model_ids": list(set(model_ids)),
                "latency_ms": total_latency,
            },
        )

        logger.info(
            "surface_evaluation_complete",
            evaluation_id=eval_result.evaluation_id,
            surface=surface,
            verdict=eval_result.overall_verdict.value,
            rules_evaluated=eval_result.rules_evaluated,
            violations=eval_result.rules_violated,
            latency_ms=total_latency,
        )

        return eval_result

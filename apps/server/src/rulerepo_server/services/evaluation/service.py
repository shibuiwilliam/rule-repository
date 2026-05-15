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
from rulerepo_server.domain.evaluation import EvaluationResult, RuleVerdict, Verdict
from rulerepo_server.domain.rule import ComputationalBody, DefinitionalBody, NormativeBody, RuleKind
from rulerepo_server.services.evaluation.batch_evaluator import evaluate_batch
from rulerepo_server.services.evaluation.conflict_aggregator import (
    aggregate_with_conflicts,
)
from rulerepo_server.services.evaluation.context_assembler import assemble_context
from rulerepo_server.services.evaluation.deterministic.runner import (
    DeterministicRuleVerdict,
    evaluate_deterministic,
)
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
        # Use explicit surface if provided; infer from subject_kind; fall
        # back to "code" only when a diff is actually provided.
        resolved_surface = surface or _subject_kind_to_surface(subject_kind) or ("code" if diff else "generic")
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
            surface=resolved_surface,
        )

        # 3. If no rules, return ALLOW
        if not rules:
            return aggregate_verdicts([], [], 0)

        # 3a. Deterministic pre-pass: resolve computational/lookup rules
        #     without touching the LLM. Rules that are fully resolved are
        #     excluded from the LLM batch. See CLAUDE.md §14.9.
        det_verdicts, det_model_ids, llm_rules = _run_deterministic_prepass(
            rules,
            facts or {},
        )

        if det_verdicts:
            logger.info(
                "deterministic_prepass_complete",
                resolved=len(det_verdicts),
                remaining_for_llm=len(llm_rules),
            )

        # If everything was resolved deterministically, skip LLM entirely
        if not llm_rules:
            total_latency = int((time.time() - start_time) * 1000)
            return aggregate_verdicts(det_verdicts, det_model_ids, total_latency)

        if not self._gemini_client:
            logger.warning("evaluation_no_llm_client")
            # Return whatever the deterministic layer produced
            total_latency = int((time.time() - start_time) * 1000)
            return aggregate_verdicts(det_verdicts, det_model_ids, total_latency)

        # 4. Resolve relationship graph for conflict-aware evaluation
        rule_id_list = [r["id"] for r in llm_rules]
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

        # 5. Evaluate remaining rules via LLM (concurrently)
        # Pass LLM cache repo for caching (CLAUDE_ENHANCE.md §0.2)
        cache_repo = None
        try:
            from rulerepo_server.adapters.postgres.cache_repo import LLMCacheRepository

            cache_repo = LLMCacheRepository(self._session)
        except Exception:
            pass

        batch_results = await evaluate_batch(
            llm_rules,
            context,
            self._gemini_client,
            cache_repo=cache_repo,
            evaluation_plan=plan,
        )

        # Merge deterministic verdicts with LLM verdicts
        verdicts = list(det_verdicts)
        model_ids: list[str] = list(det_model_ids)
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

            input_type = resolved_surface if resolved_surface != "generic" else ("code" if diff else "facts")
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
                "surface": resolved_surface,
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
        # Merge subject facts and payload into a single facts dict. The
        # surface adapter has already parsed the payload into the uniform
        # EvaluationSubjectPayload — the shared assembler does not need
        # to know which fields are surface-specific.
        merged_facts = {**subject.facts, **subject.payload}
        context = assemble_context(
            facts=merged_facts,
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

        # 4. Early return if no rules
        if not rules:
            return aggregate_verdicts([], [], 0)

        # 4a. Deterministic pre-pass (same as legacy evaluate)
        subject_facts = {**merged_facts}
        det_verdicts, det_model_ids, llm_rules = _run_deterministic_prepass(
            rules,
            subject_facts,
        )

        if det_verdicts:
            logger.info(
                "deterministic_prepass_complete",
                surface=surface,
                resolved=len(det_verdicts),
                remaining_for_llm=len(llm_rules),
            )

        if not llm_rules:
            total_latency = int((time.time() - start_time) * 1000)
            return aggregate_verdicts(det_verdicts, det_model_ids, total_latency)

        if not self._gemini_client:
            logger.warning("evaluation_no_llm_client", surface=surface)
            total_latency = int((time.time() - start_time) * 1000)
            return aggregate_verdicts(det_verdicts, det_model_ids, total_latency)

        # 5. Resolve graph relationships
        rule_id_list = [r["id"] for r in llm_rules]
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

        # 6. Evaluate remaining rules via LLM
        cache_repo = None
        try:
            from rulerepo_server.adapters.postgres.cache_repo import LLMCacheRepository

            cache_repo = LLMCacheRepository(self._session)
        except Exception:
            pass

        batch_results = await evaluate_batch(
            llm_rules,
            context,
            self._gemini_client,
            cache_repo=cache_repo,
            evaluation_plan=plan,
            surface=surface,
        )

        # Merge deterministic verdicts with LLM verdicts
        verdicts = list(det_verdicts)
        model_ids: list[str] = list(det_model_ids)
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


def _build_rule_body(rule: dict[str, Any]) -> ComputationalBody | NormativeBody | DefinitionalBody | None:
    """Build a typed RuleBody from a rule dict's ``body`` or ``constraints`` fields.

    Returns ``None`` if the rule has no deterministic-evaluable body.
    """
    body = rule.get("body")
    kind_str = rule.get("kind", "normative")

    if isinstance(body, ComputationalBody | NormativeBody | DefinitionalBody):
        return body

    if isinstance(body, dict):
        if kind_str == "computational" or "expression" in body:
            return ComputationalBody(
                expression=body.get("expression", ""),
                required_inputs=body.get("required_inputs", []),
                unit=body.get("unit"),
                exception_predicate=body.get("exception_predicate"),
            )
        if kind_str == "definitional" and "term" in body:
            return DefinitionalBody(
                term=body.get("term", ""),
                definition=body.get("definition", ""),
                lookup_table=body.get("lookup_table"),
            )
        if kind_str == "normative" and body.get("predicate"):
            return NormativeBody(predicate=body.get("predicate"))

    # Check legacy constraints field for expression-based rules
    constraints = rule.get("constraints")
    if isinstance(constraints, list):
        for c in constraints:
            if isinstance(c, dict) and c.get("expression"):
                return ComputationalBody(
                    expression=c["expression"],
                    required_inputs=c.get("required_inputs", []),
                )

    return None


def _resolve_rule_kind(rule: dict[str, Any]) -> RuleKind:
    """Resolve a ``RuleKind`` from a rule dict, defaulting to NORMATIVE."""
    kind_str = rule.get("kind", "normative")
    try:
        return RuleKind(kind_str)
    except (ValueError, KeyError):
        return RuleKind.NORMATIVE


def _deterministic_verdict_to_rule_verdict(
    det: DeterministicRuleVerdict,
    rule: dict[str, Any],
) -> RuleVerdict:
    """Convert a fully-resolved ``DeterministicRuleVerdict`` into a ``RuleVerdict``."""
    if det.passed:
        verdict = Verdict.ALLOW
        reasoning = "Deterministic evaluation passed."
    else:
        verdict = Verdict.DENY
        reasoning = "Deterministic evaluation failed."

    if det.numeric_result:
        reasoning += f" Computed value: {det.numeric_result.computed_value}."
    if det.lookup_result:
        reasoning += f" Lookup matched: {det.lookup_result.matched}."

    return RuleVerdict(
        rule_id=det.rule_id,
        rule_statement=rule.get("statement", ""),
        verdict=verdict,
        confidence=1.0,
        reasoning=reasoning,
    )


def _run_deterministic_prepass(
    rules: list[dict[str, Any]],
    facts: dict[str, Any],
) -> tuple[list[RuleVerdict], list[str], list[dict[str, Any]]]:
    """Split rules into deterministically-resolved and LLM-bound.

    Returns:
        (deterministic_verdicts, deterministic_model_ids, llm_rules)
    """
    deterministic_verdicts: list[RuleVerdict] = []
    deterministic_model_ids: list[str] = []
    llm_rules: list[dict[str, Any]] = []

    for rule in rules:
        kind = _resolve_rule_kind(rule)
        body = _build_rule_body(rule)

        if body is None:
            llm_rules.append(rule)
            continue

        try:
            det_result = evaluate_deterministic(
                rule_id=str(rule.get("id", "")),
                kind=kind,
                body=body,
                inputs=facts,
            )
        except Exception as exc:
            logger.warning(
                "deterministic_evaluation_error",
                rule_id=str(rule.get("id", "")),
                error=str(exc),
            )
            llm_rules.append(rule)
            continue

        if det_result.resolved:
            rv = _deterministic_verdict_to_rule_verdict(det_result, rule)
            deterministic_verdicts.append(rv)
            deterministic_model_ids.append("deterministic")
        else:
            # Not fully resolved — send to LLM
            llm_rules.append(rule)

    return deterministic_verdicts, deterministic_model_ids, llm_rules


def _subject_kind_to_surface(subject_kind: str | None) -> str | None:
    """Map a SubjectKind string to a surface name, or None if unknown."""
    if not subject_kind:
        return None
    mapping: dict[str, str] = {
        "code_diff": "code",
        "document": "document",
        "transaction": "transaction",
        "event": "human_action",
        "clause_set": "contract",
        "creative": "message",
        "decision": "generic",
        "identity": "generic",
    }
    return mapping.get(subject_kind)

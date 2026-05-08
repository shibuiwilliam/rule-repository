"""Engineering domain module — code-aware evaluation, discovery, and delivery.

Wraps the existing engineering-specific features into the DomainModule
protocol, enabling the orchestrator to dispatch ``code_diff`` and ``code_file``
evaluations to this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rulerepo_server.services.domains._protocol import (
    Connector,
    ContextAssembler,
    DiscoveryAnalyzer,
    DomainEvaluator,
    RuleSelector,
)


class _EngineeringContextAssembler:
    """Delegates to the existing ``services.evaluation.context_assembler``."""

    async def assemble(self, evaluable: dict[str, Any]) -> str:
        from rulerepo_server.services.evaluation.context_assembler import (
            assemble_context,
        )

        payload = evaluable.get("payload", {})
        ctx = assemble_context(
            diff=payload.get("diff"),
            files=payload.get("files"),
            facts=payload.get("facts"),
            intent=evaluable.get("intent"),
            scope=evaluable.get("scope"),
            repository=evaluable.get("repository"),
            actor=evaluable.get("actor"),
        )
        # Return a string summary suitable for LLM context.
        parts: list[str] = []
        if ctx.diff:
            parts.append(f"Diff:\n{ctx.diff}")
        if ctx.file_paths:
            parts.append(f"Files: {', '.join(ctx.file_paths)}")
        if ctx.languages:
            parts.append(f"Languages: {', '.join(ctx.languages)}")
        if ctx.intent:
            parts.append(f"Intent: {ctx.intent}")
        return "\n\n".join(parts) if parts else ""


class _EngineeringRuleSelector:
    """Delegates to the existing ``services.evaluation.rule_selector``."""

    async def select(
        self,
        context: Any,
        *,
        max_rules: int = 20,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        from rulerepo_server.services.evaluation.rule_selector import select_rules

        session = kwargs.get("session")
        if session is None:
            return []

        # Filter kwargs to only what select_rules accepts.
        passthrough = {k: v for k, v in kwargs.items() if k not in ("session",)}
        return await select_rules(
            session,
            context,
            max_rules=max_rules,
            artifact_type="code_diff",
            **passthrough,
        )


class _EngineeringEvaluator:
    """Placeholder for domain-specific evaluation logic.

    The actual evaluation is currently handled by the core evaluation
    service.  This stub will be filled in when engineering-specific
    prompt customisation is extracted.
    """

    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return []


class EngineeringModule:
    """Concrete implementation of the ``DomainModule`` protocol for engineering."""

    @property
    def name(self) -> str:
        return "engineering"

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["code_diff", "code_file"]

    def context_assembler(self) -> ContextAssembler:
        return _EngineeringContextAssembler()

    def rule_selector(self) -> RuleSelector:
        return _EngineeringRuleSelector()

    def evaluator(self) -> DomainEvaluator:
        return _EngineeringEvaluator()

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]:
        return []

    def connectors(self) -> list[Connector]:
        return []

    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"


module = EngineeringModule()

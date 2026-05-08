"""HR domain module stub — attendance, leave, and evaluation-comment rules.

This is a minimal skeleton that satisfies the ``DomainModule`` protocol.
Full implementation is planned for Phase 1 (see IMPROVEMENT.md RR-009).
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


class _HRContextAssembler:
    async def assemble(self, evaluable: dict[str, Any]) -> str:
        payload = evaluable.get("payload", {})
        parts: list[str] = []
        if record := payload.get("record"):
            parts.append(f"Record:\n{record}")
        if request := payload.get("request"):
            parts.append(f"Request:\n{request}")
        if comment := payload.get("comment"):
            parts.append(f"Comment:\n{comment}")
        return "\n\n".join(parts) if parts else str(payload)


class _HRRuleSelector:
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
        passthrough = {k: v for k, v in kwargs.items() if k != "session"}
        return await select_rules(
            session,
            context,
            max_rules=max_rules,
            artifact_type="leave_request",
            **passthrough,
        )


class _HREvaluator:
    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return []


class HRModule:
    """Concrete implementation of the ``DomainModule`` protocol for HR."""

    @property
    def name(self) -> str:
        return "hr"

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["attendance_record", "leave_request", "evaluation_comment"]

    def context_assembler(self) -> ContextAssembler:
        return _HRContextAssembler()

    def rule_selector(self) -> RuleSelector:
        return _HRRuleSelector()

    def evaluator(self) -> DomainEvaluator:
        return _HREvaluator()

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]:
        return []

    def connectors(self) -> list[Connector]:
        return []

    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"


module = HRModule()

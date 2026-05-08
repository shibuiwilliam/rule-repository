"""Finance domain module stub — journal entries, expenses, POs, invoices.

This is a minimal skeleton that satisfies the ``DomainModule`` protocol.
Full implementation is planned for Phase 2 (see IMPROVEMENT.md RR-012).
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


class _FinanceContextAssembler:
    async def assemble(self, evaluable: dict[str, Any]) -> str:
        payload = evaluable.get("payload", {})
        parts: list[str] = []
        if entry := payload.get("entry"):
            parts.append(f"Entry:\n{entry}")
        if request := payload.get("request"):
            parts.append(f"Request:\n{request}")
        if invoice := payload.get("invoice"):
            parts.append(f"Invoice:\n{invoice}")
        return "\n\n".join(parts) if parts else str(payload)


class _FinanceRuleSelector:
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
            artifact_type="journal_entry",
            **passthrough,
        )


class _FinanceEvaluator:
    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return []


class FinanceModule:
    """Concrete implementation of the ``DomainModule`` protocol for finance."""

    @property
    def name(self) -> str:
        return "finance"

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["journal_entry", "expense_request", "po_request", "invoice"]

    def context_assembler(self) -> ContextAssembler:
        return _FinanceContextAssembler()

    def rule_selector(self) -> RuleSelector:
        return _FinanceRuleSelector()

    def evaluator(self) -> DomainEvaluator:
        return _FinanceEvaluator()

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]:
        return []

    def connectors(self) -> list[Connector]:
        return []

    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"


module = FinanceModule()

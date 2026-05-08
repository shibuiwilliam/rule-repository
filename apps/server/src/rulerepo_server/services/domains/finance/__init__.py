"""Finance domain module — journal entries, expenses, POs, invoices.

Handles journal_entry, expense_request, po_request, and invoice artifact types.
See IMPROVEMENT.md RR-016.
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


class FinanceModule:
    """Concrete implementation of the ``DomainModule`` protocol for finance."""

    @property
    def name(self) -> str:
        return "finance"

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["journal_entry", "expense_request", "po_request", "invoice"]

    def context_assembler(self) -> ContextAssembler:
        from rulerepo_server.services.domains.finance.evaluation.context_assembler import (
            FinanceContextAssembler,
        )

        return FinanceContextAssembler()

    def rule_selector(self) -> RuleSelector:
        return _FinanceRuleSelector()

    def evaluator(self) -> DomainEvaluator:
        from rulerepo_server.services.domains.finance.evaluation.evaluator import FinanceEvaluator

        return FinanceEvaluator()

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]:
        from rulerepo_server.services.domains.finance.discovery.policy_analyzer import (
            FinancePolicyAnalyzer,
        )

        return [FinancePolicyAnalyzer()]

    def connectors(self) -> list[Connector]:
        return []

    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"


module = FinanceModule()

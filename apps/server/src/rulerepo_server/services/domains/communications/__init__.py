"""Communications domain module — email and chat message compliance evaluation.

Handles email_message and chat_message artifact types.
See IMPROVEMENT.md RR-018.
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


class _CommunicationsRuleSelector:
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

        # Select rules for both artifact types and merge
        email_rules = await select_rules(
            session,
            context,
            max_rules=max_rules,
            artifact_type="email_message",
            **passthrough,
        )
        chat_rules = await select_rules(
            session,
            context,
            max_rules=max_rules,
            artifact_type="chat_message",
            **passthrough,
        )

        # Deduplicate by rule id
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []
        for rule in [*email_rules, *chat_rules]:
            rid = str(rule.get("id", ""))
            if rid not in seen:
                seen.add(rid)
                merged.append(rule)

        return merged[:max_rules]


class CommunicationsModule:
    """Concrete implementation of the ``DomainModule`` protocol for communications."""

    @property
    def name(self) -> str:
        return "communications"

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["email_message", "chat_message"]

    def context_assembler(self) -> ContextAssembler:
        from rulerepo_server.services.domains.communications.evaluation.context_assembler import (
            CommunicationsContextAssembler,
        )

        return CommunicationsContextAssembler()

    def rule_selector(self) -> RuleSelector:
        return _CommunicationsRuleSelector()

    def evaluator(self) -> DomainEvaluator:
        from rulerepo_server.services.domains.communications.evaluation.evaluator import (
            CommunicationsEvaluator,
        )

        return CommunicationsEvaluator()

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]:
        from rulerepo_server.services.domains.communications.discovery.communication_policy_analyzer import (
            CommunicationPolicyAnalyzer,
        )

        return [CommunicationPolicyAnalyzer()]

    def connectors(self) -> list[Connector]:
        return []

    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"


module = CommunicationsModule()

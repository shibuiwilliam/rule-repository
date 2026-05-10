"""Conversational Rule Assistant orchestrator.

Receives a user turn, classifies intent, retrieves relevant rules,
and returns an answer with rule citations. See PROJECT.md §6.19
and CLAUDE.md §14.9.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RuleCitation:
    """A rule cited in the assistant's answer."""

    rule_id: str
    statement: str
    relevance_score: float = 0.0


@dataclass
class AssistantResponse:
    """Response from the assistant orchestrator."""

    session_id: str
    answer: str
    citations: list[RuleCitation] = field(default_factory=list)
    intent: str = "general_query"
    follow_up_needed: bool = False


class AssistantOrchestrator:
    """Thin orchestrator over Intent API + rule search + evaluation.

    Capabilities:
    - Compliance Q&A: answer questions with rule citations.
    - Pre-flight: evaluate pasted content against applicable rules.
    - Tutorial: walk user through department-specific rules.
    """

    def __init__(self, session: AsyncSession, gemini_client: Any | None = None) -> None:
        self._session = session
        self._gemini = gemini_client

    async def handle_turn(
        self,
        user_message: str,
        session_id: str | None = None,
        language: str = "ja",
        department_filter: list[str] | None = None,
    ) -> AssistantResponse:
        """Process a single user turn.

        Args:
            user_message: The user's natural language message.
            session_id: Optional session ID for conversation continuity.
            language: User's preferred language.
            department_filter: Departments visible to the user.

        Returns:
            AssistantResponse with answer, citations, and intent classification.
        """
        session_id = session_id or str(uuid4())

        logger.info(
            "assistant_turn",
            session_id=session_id,
            language=language,
            message_length=len(user_message),
        )

        # Classify intent
        intent = await self._classify_intent(user_message)

        # Search for relevant rules
        rules = await self._search_rules(user_message, department_filter)

        # Generate answer
        answer, citations = await self._generate_answer(user_message, rules, intent, language)

        return AssistantResponse(
            session_id=session_id,
            answer=answer,
            citations=citations,
            intent=intent,
        )

    async def _classify_intent(self, message: str) -> str:
        """Classify the user's intent."""
        message_lower = message.lower()
        if any(kw in message_lower for kw in ("can i", "is it ok", "allowed", "できますか", "よいですか")):
            return "compliance_question"
        if any(kw in message_lower for kw in ("review", "check", "レビュー", "チェック")):
            return "pre_send_check"
        if any(kw in message_lower for kw in ("explain", "teach", "what is", "説明", "教えて")):
            return "tutorial_request"
        return "general_query"

    async def _search_rules(
        self,
        query: str,
        department_filter: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for rules relevant to the query."""
        from rulerepo_server.services.search import SearchService

        search_svc = SearchService(self._session)
        results = await search_svc.hybrid_search(query=query, limit=10)

        # Apply department filter if provided
        if department_filter:
            results = [r for r in results if not r.get("department") or r["department"] in department_filter]

        return results

    async def _generate_answer(
        self,
        question: str,
        rules: list[dict[str, Any]],
        intent: str,
        language: str,
    ) -> tuple[str, list[RuleCitation]]:
        """Generate an answer with citations from matched rules."""
        citations: list[RuleCitation] = []

        if not rules:
            no_rules_msg = (
                "No applicable rules found for your question. Please rephrase or contact your department administrator."
            )
            if language == "ja":
                no_rules_msg = (
                    "ご質問に該当するルールが見つかりませんでした。"
                    "質問を言い換えるか、部門管理者にお問い合わせください。"
                )
            return no_rules_msg, []

        # Build citations from matched rules
        for rule in rules[:5]:
            citations.append(
                RuleCitation(
                    rule_id=str(rule.get("id", "")),
                    statement=rule.get("statement", ""),
                    relevance_score=float(rule.get("score", 0.0)),
                )
            )

        # Build answer from rules
        rule_texts = []
        for i, rule in enumerate(rules[:5], 1):
            statement = rule.get("statement", "")
            modality = rule.get("modality", "")
            rule_texts.append(f"[{i}] ({modality}) {statement}")

        rules_summary = "\n".join(rule_texts)

        match intent:
            case "compliance_question":
                answer = f"Based on the applicable rules:\n\n{rules_summary}"
            case "pre_send_check":
                answer = f"Pre-send check results based on:\n\n{rules_summary}"
            case "tutorial_request":
                answer = f"Here are the relevant rules:\n\n{rules_summary}"
            case _:
                answer = f"Related rules:\n\n{rules_summary}"

        return answer, citations

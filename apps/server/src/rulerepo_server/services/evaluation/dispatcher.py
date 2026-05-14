"""EvaluationDispatcher — the canonical entry point for all evaluation logic.

Per the v1 mission plan §3.1: "The Evaluation Dispatcher is the only entry
into evaluation logic."  All API endpoints and internal callers should use
this dispatcher rather than calling ``EvaluationService`` directly.

The dispatcher maps a subject kind to the appropriate evaluation surface and
delegates to ``EvaluationService.evaluate_subject()``.  It also supports the
legacy code-evaluation path via ``evaluate_code()`` for backward compatibility.

Architecture:
    API routers / MCP tools / CLI
           │
           ▼
    EvaluationDispatcher.dispatch()
           │
           ├── resolve surface from subject_kind
           ├── delegate to EvaluationService.evaluate_subject()
           │       │
           │       ├── surface adapter (parse subject)
           │       ├── rule selector (structured scope)
           │       ├── kind dispatch (normative→LLM, computational→deterministic)
           │       └── verdict aggregation
           │
           └── return EvaluationResult
"""

from __future__ import annotations

from typing import Any

from google import genai
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import EvaluationResult
from rulerepo_server.domain.subject import SubjectKind
from rulerepo_server.services.evaluation.service import EvaluationService

logger = get_logger(__name__)

# Maps SubjectKind values to evaluation surface names.
# Each surface has a dedicated adapter under services/evaluation/surfaces/.
_SUBJECT_KIND_TO_SURFACE: dict[str, str] = {
    SubjectKind.CODE_DIFF.value: "code",
    SubjectKind.CLAUSE_SET.value: "contract",
    SubjectKind.EVENT.value: "human_action",
    SubjectKind.TRANSACTION.value: "transaction",
    SubjectKind.DOCUMENT.value: "document",
    SubjectKind.CREATIVE.value: "message",
    SubjectKind.DECISION.value: "generic",
    SubjectKind.IDENTITY.value: "generic",
}


class EvaluationDispatcher:
    """Routes evaluation requests to the appropriate surface handler.

    This is the **single entry point** for all evaluation logic.  It wraps
    ``EvaluationService`` and adds subject-kind-to-surface resolution so
    callers need only specify *what* they are evaluating, not *how*.

    Usage::

        dispatcher = EvaluationDispatcher(session, gemini_client)
        result = await dispatcher.dispatch(
            subject_kind="transaction",
            payload={"amount": 42000, "category": "entertainment", ...},
            mode="preflight",
        )
    """

    def __init__(
        self,
        session: AsyncSession,
        gemini_client: genai.Client | None = None,
    ) -> None:
        self._service = EvaluationService(session, gemini_client)
        self._session = session

    async def dispatch(
        self,
        *,
        subject_kind: str,
        payload: dict[str, Any],
        mode: str = "preflight",
        max_rules: int = 20,
        severity_min: str = "MEDIUM",
        scope: str | None = None,
        actor: str | None = None,
    ) -> EvaluationResult:
        """Dispatch an evaluation request by subject kind.

        Resolves the subject kind to an evaluation surface, then delegates
        to the surface-aware evaluation pipeline.

        Args:
            subject_kind: One of the ``SubjectKind`` values (e.g. "code_diff",
                "transaction", "event", "document", "clause_set", "creative").
            payload: Surface-specific data dict.
            mode: "preflight", "posthoc", or "sidecar".
            max_rules: Maximum rules to evaluate.
            severity_min: Minimum rule severity.
            scope: Optional scope override.
            actor: Who triggered the evaluation.

        Returns:
            EvaluationResult with overall verdict and per-rule breakdowns.
        """
        surface = _SUBJECT_KIND_TO_SURFACE.get(subject_kind, "generic")

        logger.info(
            "dispatcher_routing",
            subject_kind=subject_kind,
            surface=surface,
            mode=mode,
        )

        return await self._service.evaluate_subject(
            surface=surface,
            subject_payload=payload,
            mode=mode,
            max_rules=max_rules,
            severity_min=severity_min,
            scope=scope,
        )

    async def evaluate_code(
        self,
        *,
        diff: str | None = None,
        files: list[dict[str, str]] | None = None,
        scope: str | None = None,
        mode: str = "preflight",
        agent_id: str | None = None,
    ) -> EvaluationResult:
        """Legacy entry point for code evaluation.

        Maintained for backward compatibility with the CI CLI, agent hooks,
        and existing integrations that pass diffs directly.

        Args:
            diff: Unified diff text.
            files: List of {"path": ..., "content": ...} dicts.
            scope: Rule scope filter.
            mode: "preflight" or "posthoc".
            agent_id: Agent identifier for tracking.

        Returns:
            EvaluationResult.
        """
        return await self._service.evaluate(
            diff=diff,
            files=files,
            scope=scope,
            mode=mode,
            agent_id=agent_id,
            surface="code",
        )

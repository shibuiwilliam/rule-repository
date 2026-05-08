"""Universal Evaluable abstraction — the input to any evaluation.

An ``Evaluable`` wraps any artifact type (code diff, contract clause,
expense request, HR transaction, etc.) in a uniform envelope that the
evaluation orchestrator can dispatch to the correct domain module.

Legacy ``EvaluateRequest`` fields (``diff``, ``files``, ``facts``) are
auto-translated to ``Evaluable(artifact_type="code_diff", payload={...})``.

See PROJECT.md §6.4 and CLAUDE.md §15.2(c).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass
class Evaluable:
    """A domain-agnostic evaluation input.

    Attributes:
        id: Unique identifier for this evaluation request.
        artifact_type: The type of artifact being evaluated (e.g.,
            ``code_diff``, ``contract_clause``, ``expense_request``).
            Determines which domain module handles the evaluation.
        payload: The artifact data.  Structure varies by artifact type.
            For ``code_diff``: ``{"diff": "...", "files": [...], "facts": {}}``.
            For ``contract_clause``: ``{"clause_text": "...", "parties": [...]}``.
        metadata: Additional context (scope, repository, agent_id, etc.).
        diff_against: Optional previous version for comparison-based
            evaluation (e.g., contract redline).
        created_at: When this evaluable was created.
    """

    id: UUID = field(default_factory=uuid4)
    artifact_type: str = "code_diff"
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    diff_against: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @classmethod
    def from_legacy_diff(
        cls,
        *,
        diff: str | None = None,
        files: list[dict[str, Any]] | None = None,
        facts: dict[str, Any] | None = None,
        intent: str | None = None,
        scope: str | None = None,
        repository: str | None = None,
        agent_id: str | None = None,
    ) -> Evaluable:
        """Create an Evaluable from legacy EvaluateRequest fields.

        This provides backwards compatibility: existing clients that
        send ``diff`` / ``files`` / ``facts`` continue to work.
        """
        payload: dict[str, Any] = {}
        if diff is not None:
            payload["diff"] = diff
        if files is not None:
            payload["files"] = files
        if facts is not None:
            payload["facts"] = facts
        if intent is not None:
            payload["intent"] = intent

        metadata: dict[str, Any] = {}
        if scope is not None:
            metadata["scope"] = scope
        if repository is not None:
            metadata["repository"] = repository
        if agent_id is not None:
            metadata["agent_id"] = agent_id

        return cls(
            artifact_type="code_diff",
            payload=payload,
            metadata=metadata,
        )

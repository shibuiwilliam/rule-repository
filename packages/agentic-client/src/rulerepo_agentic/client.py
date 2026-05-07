"""AgenticRuleClient — wraps RuleClient with evaluation and context delivery.

Supports both the legacy diff-based evaluation path and the Phase 7b
Subject envelope for cross-domain evaluation (HR, contracts, expenses, etc.).
"""

from __future__ import annotations

from typing import Any

from rulerepo import RuleClient


class AgenticRuleClient:
    """Higher-level client that wraps RuleClient with agentic capabilities.

    Calls the server's evaluation engine to check compliance, get verdicts
    with fix suggestions, and deliver rules to coding agents.

    Args:
        server_url: Base URL of the Rule Repository server.
        scope: Default scope for evaluations.
        api_key: Optional API key.
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        scope: str = "",
        api_key: str | None = None,
    ) -> None:
        self._client = RuleClient(server_url=server_url, api_key=api_key)
        self._scope = scope
        self._server_url = server_url

    async def evaluate(
        self,
        context: dict[str, Any],
        intent: str,
        mode: str = "preflight",
        diff: str | None = None,
        file_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        """Evaluate an action or code change against applicable rules.

        Calls POST /api/v1/evaluate on the Rule Repository server.

        Args:
            context: Facts about the action to evaluate.
            intent: What the caller intends to do.
            mode: Integration mode ("preflight", "posthoc", "sidecar").
            diff: Unified diff text for code evaluations.
            file_paths: File paths being modified.

        Returns:
            Evaluation result with verdict, violations, and fix suggestions.
        """
        body: dict[str, Any] = {
            "intent": intent,
            "mode": mode,
            "facts": context,
        }
        if diff:
            body["diff"] = diff
        if file_paths:
            body["files"] = [{"path": p} for p in file_paths]
        if self._scope:
            body["scope"] = self._scope

        resp = await self._client._http.post("/api/v1/evaluate", json=body)
        if resp.status_code >= 400:
            return {
                "verdict": "NEEDS_CONFIRMATION",
                "error": f"Evaluation failed: HTTP {resp.status_code}",
            }
        return resp.json()

    async def evaluate_subject(
        self,
        subject_type: str,
        payload: dict[str, Any],
        *,
        scope: str | None = None,
        mode: str = "preflight",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate a typed subject against applicable rules (Phase 7b).

        The server routes the payload through the appropriate SubjectAdapter.

        Args:
            subject_type: The type of entity (e.g. hr_event, contract_clause,
                expense_claim, code_change).
            payload: Subject-specific data.
            scope: Override the default scope for rule selection.
            mode: Integration mode ("preflight", "posthoc", "sidecar").
            metadata: Optional metadata (actor, timestamp, source system).

        Returns:
            Evaluation result with verdict, violations, and remediations.
        """
        body: dict[str, Any] = {
            "subject_type": subject_type,
            "facts": payload,
            "mode": mode,
        }
        effective_scope = scope or self._scope
        if effective_scope:
            body["scope"] = effective_scope
        if metadata:
            body["metadata"] = metadata

        resp = await self._client._http.post("/api/v1/evaluate", json=body)
        if resp.status_code >= 400:
            return {
                "verdict": "NEEDS_CONFIRMATION",
                "error": f"Evaluation failed: HTTP {resp.status_code}",
                "subject_type": subject_type,
            }
        return resp.json()

    async def get_applicable_rules(
        self,
        file_paths: list[str],
        repository: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get rules that apply to given file paths without running evaluation.

        Args:
            file_paths: File paths to check.
            repository: Repository identifier.

        Returns:
            List of applicable rule dicts.
        """
        body: dict[str, Any] = {"file_paths": file_paths}
        if repository:
            body["repository"] = repository
        if self._scope:
            body["scope"] = self._scope

        resp = await self._client._http.post("/api/v1/evaluate/applicable-rules", json=body)
        if resp.status_code >= 400:
            return []
        return resp.json()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()

    async def __aenter__(self) -> AgenticRuleClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

"""AgenticRuleClient — wraps RuleClient with evaluation and context delivery.

Supports both the legacy diff-based evaluation path and the Phase 7b
Subject envelope for cross-domain evaluation (HR, contracts, expenses, etc.).
"""

from __future__ import annotations

from typing import Any

from rulerepo import RuleClient


class AgenticRuleClient:
    """Higher-level client for AI agents interacting with the Rule Repository.

    Provides evaluation and rule retrieval for all organizational domains:
    code changes, contracts, transactions, communications, and more.

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

    # ------------------------------------------------------------------
    # Generic surface-aware rule retrieval
    # ------------------------------------------------------------------

    async def get_applicable_rules_for_surface(
        self,
        surface: str,
        *,
        scope: str | None = None,
        department: str | None = None,
        language: str = "ja",
        max_rules: int = 15,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Get rules applicable to a specific evaluation surface.

        Args:
            surface: Surface name (e.g., "contract", "transaction", "message").
            scope: Rule scope filter.
            department: Department filter (e.g., "legal", "hr", "finance").
            language: Primary language filter (default "ja").
            max_rules: Maximum rules to return.
            **kwargs: Additional surface-specific filters.

        Returns:
            List of applicable rule dicts.
        """
        body: dict[str, Any] = {
            "surface": surface,
            "max_rules": max_rules,
            "language": language,
        }
        effective_scope = scope or self._scope
        if effective_scope:
            body["scope"] = effective_scope
        if department:
            body["department"] = department
        body.update(kwargs)

        resp = await self._client._http.post("/api/v1/evaluate/applicable-rules", json=body)
        if resp.status_code >= 400:
            return []
        return resp.json()

    # ------------------------------------------------------------------
    # Domain-specific rule retrieval convenience methods
    # ------------------------------------------------------------------

    async def get_rules_for_contract(
        self,
        contract_type: str = "other",
        parties: list[str] | None = None,
        language: str = "ja",
    ) -> list[dict[str, Any]]:
        """Get rules applicable to a contract review.

        Args:
            contract_type: Type of contract (nda, employment, service,
                procurement, license, other).
            parties: Party names involved.
            language: Contract language (default "ja").

        Returns:
            List of applicable rule dicts.
        """
        scope = f"legal/contract/{contract_type}" if contract_type != "other" else "legal/contract"
        kwargs: dict[str, Any] = {}
        if parties:
            kwargs["parties"] = parties
        return await self.get_applicable_rules_for_surface(
            "contract",
            scope=scope,
            department="legal",
            language=language,
            **kwargs,
        )

    async def get_rules_for_transaction(
        self,
        transaction_type: str = "other",
        amount: float | None = None,
        department: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get rules applicable to a business transaction.

        Args:
            transaction_type: Type (expense, purchase_order, attendance,
                payroll, journal_entry, other).
            amount: Transaction amount (for threshold-based selection).
            department: Department context.

        Returns:
            List of applicable rule dicts.
        """
        type_to_scope: dict[str, str] = {
            "expense": "finance/expense",
            "purchase_order": "finance/procurement",
            "attendance": "hr/attendance",
            "payroll": "hr/payroll",
            "journal_entry": "finance/accounting",
        }
        scope = type_to_scope.get(transaction_type, "finance")
        type_to_dept: dict[str, str] = {
            "expense": "finance",
            "purchase_order": "finance",
            "attendance": "hr",
            "payroll": "hr",
            "journal_entry": "finance",
        }
        dept = department or type_to_dept.get(transaction_type)
        kwargs: dict[str, Any] = {}
        if amount is not None:
            kwargs["amount"] = amount
        return await self.get_applicable_rules_for_surface(
            "transaction",
            scope=scope,
            department=dept,
            **kwargs,
        )

    async def get_rules_for_communication(
        self,
        channel: str = "email",
        audience: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get rules applicable to a communication.

        Args:
            channel: Channel (email, slack, social, press_release,
                customer_facing, other).
            audience: Target audience (internal, external, regulatory).

        Returns:
            List of applicable rule dicts.
        """
        scope = f"communications/{channel}" if channel != "other" else "communications"
        kwargs: dict[str, Any] = {}
        if audience:
            kwargs["audience"] = audience
        return await self.get_applicable_rules_for_surface(
            "message",
            scope=scope,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Domain-specific evaluation convenience methods
    # ------------------------------------------------------------------

    async def evaluate_contract(
        self,
        text: str,
        contract_type: str = "other",
        language: str = "ja",
    ) -> dict[str, Any]:
        """Evaluate a contract or clause against applicable rules.

        Args:
            text: The contract text or clause to evaluate.
            contract_type: Type (nda, employment, service, procurement,
                license, other).
            language: Contract language (default "ja").

        Returns:
            Evaluation result with verdict and clause-level remediations.
        """
        return await self.evaluate_subject(
            "contract_clause",
            {
                "clause_text": text,
                "clause_type": contract_type,
                "language": language,
            },
            scope=f"legal/contract/{contract_type}" if contract_type != "other" else "legal/contract",
        )

    async def evaluate_transaction(
        self,
        payload: dict[str, Any],
        transaction_type: str = "other",
    ) -> dict[str, Any]:
        """Evaluate a business transaction against applicable rules.

        Args:
            payload: Transaction record as a dict (e.g., {"amount_jpy": 30000,
                "category": "entertainment"}).
            transaction_type: Type (expense, purchase_order, attendance,
                payroll, journal_entry, other).

        Returns:
            Evaluation result with verdict and field-level remediations.
        """
        type_to_scope: dict[str, str] = {
            "expense": "finance/expense",
            "purchase_order": "finance/procurement",
            "attendance": "hr/attendance",
            "payroll": "hr/payroll",
            "journal_entry": "finance/accounting",
        }
        scope = type_to_scope.get(transaction_type, "finance")
        return await self.evaluate_subject(
            "expense_claim" if transaction_type == "expense" else transaction_type,
            {**payload, "transaction_type": transaction_type},
            scope=scope,
        )

    async def evaluate_communication(
        self,
        text: str,
        channel: str = "email",
        audience: str = "external",
    ) -> dict[str, Any]:
        """Evaluate a communication draft against applicable rules.

        Args:
            text: The message content to evaluate.
            channel: Channel (email, slack, social, press_release,
                customer_facing, other).
            audience: Target audience (internal, external, regulatory).

        Returns:
            Evaluation result with verdict and text-level remediations.
        """
        return await self.evaluate_subject(
            "message",
            {
                "content": text,
                "channel": channel,
                "audience": audience,
            },
            scope=f"communications/{channel}" if channel != "other" else "communications",
            mode="sidecar",
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()

    async def __aenter__(self) -> AgenticRuleClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

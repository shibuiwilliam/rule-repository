"""Tests for the unified submissions endpoint (POST /api/v1/submissions).

Tests the submission logic — scope resolution, surface mapping, payload
forwarding — by invoking the endpoint function directly with mocked
dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from rulerepo_server.api.v1.submissions import (
    _SUBJECT_KIND_TO_SURFACE,
    SubmissionActor,
    SubmissionRequest,
    submit,
)
from rulerepo_server.domain.evaluation import (
    EvaluationResult,
    RuleVerdict,
    Verdict,
)
from rulerepo_server.services.events.scope_resolver import EventScopeResolver

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_eval_result(
    verdict: Verdict = Verdict.ALLOW,
    rules_evaluated: int = 2,
    rule_verdicts: list[RuleVerdict] | None = None,
) -> EvaluationResult:
    """Build a synthetic EvaluationResult."""
    if rule_verdicts is None:
        rule_verdicts = [
            RuleVerdict(
                rule_id="rule-1",
                rule_statement="Expenses over 100k JPY require manager approval",
                verdict=verdict,
                confidence=0.92,
                reasoning="Amount is within policy limits.",
            ),
        ]
    return EvaluationResult(
        evaluation_id="eval-test-001",
        overall_verdict=verdict,
        rule_verdicts=rule_verdicts,
        rules_evaluated=rules_evaluated,
        rules_passed=rules_evaluated if verdict == Verdict.ALLOW else 0,
        rules_violated=0 if verdict == Verdict.ALLOW else rules_evaluated,
        rules_uncertain=0,
        fix_summary=None,
        model_ids_used=["gemini-3-flash-preview"],
        total_latency_ms=150,
        timestamp=datetime.now(tz=UTC),
    )


def _make_deny_result() -> EvaluationResult:
    """Build a DENY result with fix suggestion."""
    return _make_eval_result(
        verdict=Verdict.DENY,
        rule_verdicts=[
            RuleVerdict(
                rule_id="rule-2",
                rule_statement="Entertainment expenses must not exceed 100,000 JPY",
                verdict=Verdict.DENY,
                confidence=0.95,
                reasoning="Amount 150,000 JPY exceeds the 100,000 JPY limit.",
                issue_description="Expense amount exceeds policy limit.",
                fix_suggestion="Reduce to 100,000 JPY or obtain CFO pre-approval.",
            ),
        ],
    )


async def _call_submit(body: dict, mock_result: EvaluationResult) -> tuple:
    """Call the submit endpoint with a mocked EvaluationService.

    Returns (response, mock_evaluate) where mock_evaluate captures
    the call args for assertions.
    """
    mock_evaluate = AsyncMock(return_value=mock_result)
    mock_session = MagicMock()

    # Patch EvaluationService at the module where it's imported (submissions.py)
    mock_svc_instance = MagicMock()
    mock_svc_instance.evaluate = mock_evaluate

    with patch(
        "rulerepo_server.api.v1.submissions.EvaluationService",
        return_value=mock_svc_instance,
    ):
        request = SubmissionRequest(**body)
        response = await submit(request, session=mock_session)

    return response, mock_evaluate


# ---------------------------------------------------------------------------
# Subject kind to surface mapping
# ---------------------------------------------------------------------------


class TestSurfaceMapping:
    def test_code_diff_maps_to_code(self) -> None:
        assert _SUBJECT_KIND_TO_SURFACE["code_diff"] == "code"

    def test_transaction_maps_to_transaction(self) -> None:
        assert _SUBJECT_KIND_TO_SURFACE["transaction"] == "transaction"

    def test_document_maps_to_document(self) -> None:
        assert _SUBJECT_KIND_TO_SURFACE["document"] == "document"

    def test_event_maps_to_human_action(self) -> None:
        assert _SUBJECT_KIND_TO_SURFACE["event"] == "human_action"

    def test_clause_set_maps_to_contract(self) -> None:
        assert _SUBJECT_KIND_TO_SURFACE["clause_set"] == "contract"

    def test_creative_maps_to_message(self) -> None:
        assert _SUBJECT_KIND_TO_SURFACE["creative"] == "message"

    def test_unknown_falls_back_to_generic(self) -> None:
        assert _SUBJECT_KIND_TO_SURFACE.get("unknown_kind", "generic") == "generic"


# ---------------------------------------------------------------------------
# Scope Resolution (unit)
# ---------------------------------------------------------------------------


class TestScopeResolver:
    def test_known_event_type(self) -> None:
        resolver = EventScopeResolver()
        scopes = resolver.resolve("finance.expense.submitted")
        assert "finance/expense" in scopes

    def test_convention_fallback(self) -> None:
        resolver = EventScopeResolver()
        scopes = resolver.resolve("logistics.shipment.dispatched")
        assert "logistics/shipment" in scopes

    def test_hr_overtime(self) -> None:
        resolver = EventScopeResolver()
        scopes = resolver.resolve("hr.overtime.filed")
        assert "hr/overtime" in scopes


# ---------------------------------------------------------------------------
# Expense Transaction Submission
# ---------------------------------------------------------------------------


class TestExpenseSubmission:
    async def test_expense_returns_verdict(self) -> None:
        result = _make_eval_result(verdict=Verdict.ALLOW)
        resp, mock_eval = await _call_submit(
            {
                "subject_kind": "transaction",
                "event_type": "finance.expense.submitted",
                "actor": {"id": "E042", "type": "employee", "department": "sales"},
                "payload": {"amount": 80000, "currency": "JPY", "category": "entertainment"},
                "intent": "Submit entertainment expense",
                "mode": "preflight",
            },
            result,
        )

        assert resp.overall_verdict == "ALLOW"
        assert resp.evaluation_id == "eval-test-001"

        kw = mock_eval.call_args.kwargs
        assert kw["scope"] == "finance/expense"
        assert kw["surface"] == "transaction"
        assert kw["subject_kind"] == "transaction"
        assert kw["mode"] == "preflight"
        assert kw["facts"]["amount"] == 80000

    async def test_expense_deny_has_fix_suggestion(self) -> None:
        result = _make_deny_result()
        resp, _ = await _call_submit(
            {
                "subject_kind": "transaction",
                "event_type": "finance.expense.submitted",
                "actor": {"id": "E042", "type": "employee", "department": "sales"},
                "payload": {"amount": 150000, "currency": "JPY"},
            },
            result,
        )

        assert resp.overall_verdict == "DENY"
        assert resp.rules_violated > 0
        assert len(resp.violations) > 0
        assert resp.violations[0].fix_suggestion is not None


# ---------------------------------------------------------------------------
# Contract Document Submission
# ---------------------------------------------------------------------------


class TestContractSubmission:
    async def test_contract_routes_to_document_surface(self) -> None:
        result = _make_eval_result(verdict=Verdict.DENY)
        resp, mock_eval = await _call_submit(
            {
                "subject_kind": "document",
                "event_type": "legal.contract.draft_created",
                "actor": {"id": "E010", "type": "employee", "department": "legal"},
                "payload": {"clause_text": "Unlimited liability...", "clause_type": "liability"},
                "intent": "Review liability clause",
            },
            result,
        )

        assert resp.evaluation_id is not None
        kw = mock_eval.call_args.kwargs
        assert kw["scope"] == "legal/contract"
        assert kw["surface"] == "document"


# ---------------------------------------------------------------------------
# Code Diff Submission (backward compatibility)
# ---------------------------------------------------------------------------


class TestCodeDiffSubmission:
    async def test_code_diff_routes_to_code_surface(self) -> None:
        result = _make_eval_result(verdict=Verdict.ALLOW)
        resp, mock_eval = await _call_submit(
            {
                "subject_kind": "code_diff",
                "event_type": "engineering.pr.opened",
                "actor": {"id": "agent:claude-code", "type": "agent", "department": "engineering"},
                "payload": {"diff": "--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n-old\n+new\n"},
                "intent": "Add login endpoint",
            },
            result,
        )

        assert resp.overall_verdict == "ALLOW"
        kw = mock_eval.call_args.kwargs
        assert kw["surface"] == "code"
        assert kw["subject_kind"] == "code_diff"
        assert kw["diff"] is not None
        assert "main.py" in kw["diff"]

    async def test_code_diff_agent_id_set(self) -> None:
        """For agent actors, agent_id should be passed to the evaluation."""
        result = _make_eval_result()
        _, mock_eval = await _call_submit(
            {
                "subject_kind": "code_diff",
                "actor": {"id": "agent:cursor", "type": "agent"},
                "payload": {"diff": "--- a/x.py\n+++ b/x.py\n"},
            },
            result,
        )

        kw = mock_eval.call_args.kwargs
        assert kw["agent_id"] == "agent:cursor"


# ---------------------------------------------------------------------------
# Scope Resolution (integration)
# ---------------------------------------------------------------------------


class TestScopeResolutionIntegration:
    async def test_scope_from_event_type(self) -> None:
        result = _make_eval_result()
        _, mock_eval = await _call_submit(
            {
                "subject_kind": "event",
                "event_type": "hr.overtime.filed",
                "actor": {"id": "E001", "type": "employee", "department": "hr"},
                "payload": {"hours": 50},
            },
            result,
        )
        assert mock_eval.call_args.kwargs["scope"] == "hr/overtime"

    async def test_scope_fallback_to_department(self) -> None:
        result = _make_eval_result()
        _, mock_eval = await _call_submit(
            {
                "subject_kind": "event",
                "actor": {"id": "E001", "type": "employee", "department": "procurement"},
                "payload": {"action": "approve PO"},
            },
            result,
        )
        assert mock_eval.call_args.kwargs["scope"] == "procurement"

    async def test_explicit_scope_overrides_all(self) -> None:
        result = _make_eval_result()
        _, mock_eval = await _call_submit(
            {
                "subject_kind": "transaction",
                "event_type": "finance.expense.submitted",
                "scope": "custom/override",
                "actor": {"id": "E001", "type": "employee"},
                "payload": {"amount": 1000},
            },
            result,
        )
        assert mock_eval.call_args.kwargs["scope"] == "custom/override"

    async def test_unknown_event_uses_convention(self) -> None:
        result = _make_eval_result()
        _, mock_eval = await _call_submit(
            {
                "subject_kind": "event",
                "event_type": "logistics.shipment.dispatched",
                "actor": {"id": "S001", "type": "system"},
                "payload": {"tracking_id": "TRK-001"},
            },
            result,
        )
        assert mock_eval.call_args.kwargs["scope"] == "logistics/shipment"


# ---------------------------------------------------------------------------
# Payload and Metadata Forwarding
# ---------------------------------------------------------------------------


class TestPayloadForwarding:
    async def test_correlation_id_in_facts(self) -> None:
        result = _make_eval_result()
        _, mock_eval = await _call_submit(
            {
                "subject_kind": "transaction",
                "actor": {"id": "E001", "type": "employee"},
                "payload": {"amount": 5000},
                "correlation_id": "TXN-2025-12345",
            },
            result,
        )
        assert mock_eval.call_args.kwargs["facts"]["_correlation_id"] == "TXN-2025-12345"

    async def test_metadata_passed_in_facts(self) -> None:
        result = _make_eval_result()
        _, mock_eval = await _call_submit(
            {
                "subject_kind": "event",
                "actor": {"id": "E001", "type": "employee"},
                "payload": {"action": "test"},
                "metadata": {"source_system": "SAP", "version": "2.0"},
            },
            result,
        )
        facts = mock_eval.call_args.kwargs["facts"]
        assert facts["_metadata"]["source_system"] == "SAP"

    async def test_intent_forwarded(self) -> None:
        result = _make_eval_result()
        _, mock_eval = await _call_submit(
            {
                "subject_kind": "transaction",
                "actor": {"id": "E001", "type": "employee"},
                "payload": {"amount": 1000},
                "intent": "Reimburse taxi fare",
            },
            result,
        )
        assert mock_eval.call_args.kwargs["intent"] == "Reimburse taxi fare"


# ---------------------------------------------------------------------------
# Request Model Validation
# ---------------------------------------------------------------------------


class TestSubmissionRequestValidation:
    def test_valid_request(self) -> None:
        req = SubmissionRequest(
            subject_kind="transaction",
            actor=SubmissionActor(id="E001"),
            payload={"amount": 100},
        )
        assert req.subject_kind == "transaction"
        assert req.mode == "preflight"

    def test_default_mode_is_preflight(self) -> None:
        req = SubmissionRequest(
            subject_kind="event",
            actor=SubmissionActor(id="E001"),
            payload={},
        )
        assert req.mode == "preflight"

    def test_actor_defaults(self) -> None:
        actor = SubmissionActor(id="E001")
        assert actor.type == "employee"
        assert actor.department is None
        assert actor.role is None
        assert actor.org_unit is None

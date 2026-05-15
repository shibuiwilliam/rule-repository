"""Tests for the Universal Submissions API schemas."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from rulerepo_server.schemas.submissions import (
    BusinessEventInput,
    CodeChangeInput,
    CommunicationInput,
    DecisionRequestInput,
    DocumentArtifactInput,
    SubmissionResponse,
    TransactionInput,
    UniversalSubmissionRequest,
)


class TestSubjectDiscriminatedUnion:
    """Test that the discriminated union on 'kind' works correctly."""

    def test_code_change(self) -> None:
        req = UniversalSubmissionRequest(
            subject={"kind": "code_change", "diff": "--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new"}
        )
        assert isinstance(req.subject, CodeChangeInput)
        assert req.subject.kind == "code_change"

    def test_business_event(self) -> None:
        req = UniversalSubmissionRequest(
            subject={
                "kind": "business_event",
                "event_type": "register_overtime",
                "payload": {"employee_id": "E001", "hours": 50},
            }
        )
        assert isinstance(req.subject, BusinessEventInput)
        assert req.subject.event_type == "register_overtime"

    def test_document_artifact(self) -> None:
        req = UniversalSubmissionRequest(
            subject={
                "kind": "document_artifact",
                "document_id": "doc_123",
                "intent": "draft_review",
            }
        )
        assert isinstance(req.subject, DocumentArtifactInput)

    def test_transaction(self) -> None:
        req = UniversalSubmissionRequest(
            subject={
                "kind": "transaction",
                "transaction_type": "expense",
                "amount": "12000.50",
                "currency": "JPY",
            }
        )
        assert isinstance(req.subject, TransactionInput)
        assert req.subject.amount == Decimal("12000.50")

    def test_communication(self) -> None:
        req = UniversalSubmissionRequest(
            subject={
                "kind": "communication",
                "channel": "email",
                "content": "Hello world",
            }
        )
        assert isinstance(req.subject, CommunicationInput)

    def test_decision_request(self) -> None:
        req = UniversalSubmissionRequest(
            subject={
                "kind": "decision_request",
                "request_type": "approval",
                "description": "Need approval for purchase",
            }
        )
        assert isinstance(req.subject, DecisionRequestInput)

    def test_invalid_kind(self) -> None:
        with pytest.raises(ValidationError):
            UniversalSubmissionRequest(subject={"kind": "invalid_kind"})

    def test_with_scope(self) -> None:
        req = UniversalSubmissionRequest(
            subject={"kind": "business_event", "event_type": "test"},
            scope={"domain": "hr", "org_unit": "acme/jp"},
        )
        assert req.scope is not None
        assert req.scope.domain == "hr"

    def test_with_submission_id(self) -> None:
        req = UniversalSubmissionRequest(
            subject={"kind": "code_change"},
            submission_id="sub_123",
        )
        assert req.submission_id == "sub_123"

    def test_mode_default(self) -> None:
        req = UniversalSubmissionRequest(subject={"kind": "code_change"})
        assert req.mode == "preflight"


class TestSubmissionResponse:
    """Test the response model."""

    def test_allow_verdict(self) -> None:
        resp = SubmissionResponse(verdict="ALLOW", applied_rules=["rule_1"])
        assert resp.verdict == "ALLOW"
        assert len(resp.violations) == 0

    def test_deny_verdict_with_violations(self) -> None:
        resp = SubmissionResponse(
            verdict="DENY",
            violations=[
                {
                    "rule_id": "rule_1",
                    "statement": "Must not exceed limit",
                    "reason": "Exceeded by 10",
                }
            ],
        )
        assert resp.verdict == "DENY"
        assert len(resp.violations) == 1

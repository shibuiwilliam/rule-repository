"""Tests for the EvaluationSubject abstraction (domain/evaluation_subject.py).

Covers:
- Creation of each of the 6 concrete subject types
- Auto-correction of ``kind`` in ``__post_init__``
- SUBJECT_CLASSES mapping completeness
- Basic context assembler for code_change
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from rulerepo_server.domain.evaluation_subject import (
    SUBJECT_CLASSES,
    BusinessEventSubject,
    CodeChangeSubject,
    CommunicationSubject,
    DecisionRequestSubject,
    DocumentArtifactSubject,
    EvaluationSubject,
    EvaluationSubjectKind,
    TransactionSubject,
)

# ---------------------------------------------------------------------------
# Construction tests
# ---------------------------------------------------------------------------


class TestCodeChangeSubject:
    def test_create_minimal(self) -> None:
        s = CodeChangeSubject(kind=EvaluationSubjectKind.CODE_CHANGE)
        assert s.kind == EvaluationSubjectKind.CODE_CHANGE
        assert s.diff == ""
        assert s.files == []
        assert s.repository is None

    def test_create_with_fields(self) -> None:
        s = CodeChangeSubject(
            kind=EvaluationSubjectKind.CODE_CHANGE,
            diff="--- a/f.py\n+++ b/f.py",
            files=[{"path": "f.py", "status": "modified"}],
            repository="my-repo",
            actor_id="user-1",
        )
        assert s.diff == "--- a/f.py\n+++ b/f.py"
        assert s.repository == "my-repo"
        assert s.actor_id == "user-1"

    def test_kind_auto_corrected(self) -> None:
        s = CodeChangeSubject(kind=EvaluationSubjectKind.BUSINESS_EVENT)
        assert s.kind == EvaluationSubjectKind.CODE_CHANGE


class TestBusinessEventSubject:
    def test_create(self) -> None:
        now = datetime.now(UTC)
        s = BusinessEventSubject(
            kind=EvaluationSubjectKind.BUSINESS_EVENT,
            event_type="overtime_request",
            payload={"hours": 10},
            occurred_at=now,
        )
        assert s.kind == EvaluationSubjectKind.BUSINESS_EVENT
        assert s.event_type == "overtime_request"
        assert s.payload == {"hours": 10}
        assert s.occurred_at == now

    def test_kind_auto_corrected(self) -> None:
        s = BusinessEventSubject(kind=EvaluationSubjectKind.CODE_CHANGE)
        assert s.kind == EvaluationSubjectKind.BUSINESS_EVENT


class TestDocumentArtifactSubject:
    def test_create(self) -> None:
        s = DocumentArtifactSubject(
            kind=EvaluationSubjectKind.DOCUMENT_ARTIFACT,
            document_id="doc-123",
            sections=[{"title": "NDA", "text": "..."}],
            intent="draft_review",
        )
        assert s.kind == EvaluationSubjectKind.DOCUMENT_ARTIFACT
        assert s.document_id == "doc-123"
        assert s.intent == "draft_review"

    def test_kind_auto_corrected(self) -> None:
        s = DocumentArtifactSubject(kind=EvaluationSubjectKind.TRANSACTION)
        assert s.kind == EvaluationSubjectKind.DOCUMENT_ARTIFACT


class TestTransactionSubject:
    def test_create(self) -> None:
        s = TransactionSubject(
            kind=EvaluationSubjectKind.TRANSACTION,
            transaction_type="expense",
            amount=Decimal("1500.00"),
            currency="JPY",
            counterparties=["vendor-a"],
            line_items=[{"description": "dinner", "amount": "1500.00"}],
        )
        assert s.kind == EvaluationSubjectKind.TRANSACTION
        assert s.amount == Decimal("1500.00")
        assert s.currency == "JPY"
        assert s.counterparties == ["vendor-a"]

    def test_kind_auto_corrected(self) -> None:
        s = TransactionSubject(kind=EvaluationSubjectKind.CODE_CHANGE)
        assert s.kind == EvaluationSubjectKind.TRANSACTION


class TestCommunicationSubject:
    def test_create(self) -> None:
        s = CommunicationSubject(
            kind=EvaluationSubjectKind.COMMUNICATION,
            channel="email",
            sender_id="alice",
            recipient_ids=["bob", "carol"],
            content="Hello world",
        )
        assert s.kind == EvaluationSubjectKind.COMMUNICATION
        assert s.channel == "email"
        assert s.content == "Hello world"
        assert s.recipient_ids == ["bob", "carol"]

    def test_kind_auto_corrected(self) -> None:
        s = CommunicationSubject(kind=EvaluationSubjectKind.DECISION_REQUEST)
        assert s.kind == EvaluationSubjectKind.COMMUNICATION


class TestDecisionRequestSubject:
    def test_create(self) -> None:
        s = DecisionRequestSubject(
            kind=EvaluationSubjectKind.DECISION_REQUEST,
            request_type="budget_approval",
            description="Q3 marketing budget",
            options=["approve", "reject", "defer"],
            context_data={"amount": 50000},
        )
        assert s.kind == EvaluationSubjectKind.DECISION_REQUEST
        assert s.request_type == "budget_approval"
        assert len(s.options) == 3

    def test_kind_auto_corrected(self) -> None:
        s = DecisionRequestSubject(kind=EvaluationSubjectKind.CODE_CHANGE)
        assert s.kind == EvaluationSubjectKind.DECISION_REQUEST


# ---------------------------------------------------------------------------
# SUBJECT_CLASSES mapping
# ---------------------------------------------------------------------------


class TestSubjectClasses:
    def test_all_kinds_mapped(self) -> None:
        for kind in EvaluationSubjectKind:
            assert kind in SUBJECT_CLASSES, f"{kind} missing from SUBJECT_CLASSES"

    def test_mapping_produces_correct_kind(self) -> None:
        for kind, cls in SUBJECT_CLASSES.items():
            instance = cls(kind=kind)
            assert instance.kind == kind

    def test_all_subclasses_are_evaluation_subjects(self) -> None:
        for cls in SUBJECT_CLASSES.values():
            assert issubclass(cls, EvaluationSubject)


# ---------------------------------------------------------------------------
# Frozen dataclass behavior
# ---------------------------------------------------------------------------


class TestFrozenBehavior:
    def test_immutable(self) -> None:
        s = CodeChangeSubject(kind=EvaluationSubjectKind.CODE_CHANGE, diff="x")
        with pytest.raises(AttributeError):
            s.diff = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Context assembler (code_change)
# ---------------------------------------------------------------------------


class TestCodeChangeContextAssembler:
    @pytest.mark.asyncio
    async def test_assemble_context(self) -> None:
        from rulerepo_server.services.evaluation.subjects.code_change import (
            assemble_context,
        )

        subject = CodeChangeSubject(
            kind=EvaluationSubjectKind.CODE_CHANGE,
            diff="--- a/f.py\n+++ b/f.py",
            files=[{"path": "f.py"}],
            repository="my-repo",
            actor_id="user-1",
            metadata={"ci": True},
        )
        ctx = await assemble_context(subject)
        assert ctx["kind"] == "code_change"
        assert ctx["diff"] == subject.diff
        assert ctx["files"] == subject.files
        assert ctx["repository"] == "my-repo"
        assert ctx["actor_id"] == "user-1"
        assert ctx["metadata"] == {"ci": True}

    @pytest.mark.asyncio
    async def test_assemble_context_minimal(self) -> None:
        from rulerepo_server.services.evaluation.subjects.code_change import (
            assemble_context,
        )

        subject = CodeChangeSubject(kind=EvaluationSubjectKind.CODE_CHANGE)
        ctx = await assemble_context(subject)
        assert ctx["kind"] == "code_change"
        assert "actor_id" not in ctx
        assert "metadata" not in ctx

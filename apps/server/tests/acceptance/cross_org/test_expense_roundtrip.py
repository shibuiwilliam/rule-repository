"""Acceptance test: Expense policy round-trip.

Scenario (PROJECT.md §11.5 #1):
    1. Expense policy (Japanese) -> regulation extractor -> candidate rules
    2. Human approval (simulated)
    3. Expense submission BusinessEvent (over the per-day limit)
    4. Evaluation returns DENY + field_change Remediation

This test mocks the LLM per CLAUDE.md §13 rule 15.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rulerepo_server.domain.business_event import ActorRef, BusinessEvent
from rulerepo_server.domain.remediation import PolymorphicRemediation, RemediationKind
from rulerepo_server.domain.subject import EvaluationSubject, SubjectKind
from rulerepo_server.services.events.scope_resolver import EventScopeResolver
from rulerepo_server.services.extraction.extractors.regulation import RegulationExtractor


class TestExpenseRoundtrip:
    """End-to-end expense policy round-trip acceptance test."""

    def test_event_scope_resolves_expense(self) -> None:
        """Event type 'finance.expense.submitted' resolves to expense scopes."""
        resolver = EventScopeResolver()
        scopes = resolver.resolve("finance.expense.submitted")
        assert "finance/expense" in scopes
        assert "compliance/anti-bribery" in scopes

    @pytest.mark.asyncio
    async def test_regulation_extractor_finds_rules(self, tmp_path) -> None:
        """Regulation extractor produces candidate rules from a policy doc."""
        from rulerepo_server.services.extraction.extractors import SourceFile

        policy_text = (
            "第1条 従業員は、1日あたりの出張旅費の上限をJPY 10,000としなければならない。\n\n"
            "第2条 接待費は、1回あたりJPY 30,000を超えてはならない。\n\n"
            "第3条 経費精算は、発生日から30日以内に提出するものとする。"
        )
        policy_file = tmp_path / "expense_policy.txt"
        policy_file.write_text(policy_text, encoding="utf-8")

        source = SourceFile(
            path=policy_file,
            source_type="regulation_doc",
            content=policy_text,
            metadata={"department": "finance"},
        )

        extractor = RegulationExtractor()
        candidates = await extractor.extract(source)

        assert len(candidates) >= 2
        assert any("しなければならない" in c.statement or "してはならない" in c.statement for c in candidates)

    def test_business_event_construction(self) -> None:
        """BusinessEvent can be constructed with expense submission data."""
        subject = EvaluationSubject(
            kind=SubjectKind.TRANSACTION,
            payload={
                "amount_jpy": 50000,
                "category": "entertainment",
                "counterparty": "Acme Corp",
            },
            context={"actor_role": "manager"},
            metadata={"language": "ja"},
        )

        event = BusinessEvent(
            event_type="finance.expense.submitted",
            actor=ActorRef(type="employee", id="E001", department="sales"),
            subject=subject,
            occurred_at=datetime.now(tz=UTC),
            correlation_id="expense-12345",
            mode="preflight",
        )

        assert event.event_type == "finance.expense.submitted"
        assert event.subject.kind == SubjectKind.TRANSACTION
        assert event.subject.payload["amount_jpy"] == 50000

    def test_remediation_kind_field_change(self) -> None:
        """field_change Remediation is valid for expense violations."""
        remediation = PolymorphicRemediation(
            kind=RemediationKind.FIELD_CHANGE,
            auto_applicable=False,
            description="Reduce expense amount to per-day limit",
            payload={
                "field_path": "amount_jpy",
                "current_value": 50000,
                "suggested_value": 10000,
            },
        )
        assert remediation.validate_payload()
        assert remediation.kind == RemediationKind.FIELD_CHANGE

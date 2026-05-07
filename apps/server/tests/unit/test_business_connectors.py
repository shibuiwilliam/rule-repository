"""Tests for Phase 7d business system connectors."""

from __future__ import annotations

from rulerepo_server.domain.subject import SubjectType
from rulerepo_server.integrations.business_systems.attendance import AttendanceConnector
from rulerepo_server.integrations.business_systems.contract import ContractConnector
from rulerepo_server.integrations.business_systems.expense import ExpenseConnector


class TestAttendanceConnector:
    def test_system_name(self) -> None:
        assert AttendanceConnector().system_name == "attendance"

    def test_normalize_overtime(self) -> None:
        connector = AttendanceConnector()
        subject = connector.normalize_webhook(
            {
                "event_type": "overtime_register",
                "employee_id": "E001",
                "hours": 50,
                "month": "2026-04",
                "location": "jp",
            }
        )
        assert subject.type == SubjectType.HR_EVENT
        assert subject.payload["hours"] == 50
        assert subject.payload["event_type"] == "overtime_register"
        assert subject.metadata["source_system"] == "attendance"

    def test_normalize_leave(self) -> None:
        connector = AttendanceConnector()
        subject = connector.normalize_webhook(
            {
                "event_type": "leave_request",
                "employee_id": "E002",
                "leave_type": "paid_leave",
                "leave_days": 3,
            }
        )
        assert subject.type == SubjectType.HR_EVENT
        assert subject.payload["leave_type"] == "paid_leave"


class TestExpenseConnector:
    def test_system_name(self) -> None:
        assert ExpenseConnector().system_name == "expense"

    def test_normalize_expense(self) -> None:
        connector = ExpenseConnector()
        subject = connector.normalize_webhook(
            {
                "expense_type": "entertainment",
                "amount": 45000,
                "currency": "JPY",
                "employee_id": "E001",
                "attendees": "4 people",
                "receipt_attached": True,
            }
        )
        assert subject.type == SubjectType.EXPENSE_CLAIM
        assert subject.payload["amount"] == 45000
        assert subject.payload["receipt_attached"] is True


class TestContractConnector:
    def test_system_name(self) -> None:
        assert ContractConnector().system_name == "contract"

    def test_normalize_nda_review(self) -> None:
        connector = ContractConnector()
        subject = connector.normalize_webhook(
            {
                "contract_type": "NDA",
                "clause_text": "All information is confidential.",
                "counterparty": "ACME Corp",
                "governing_law": "JP",
            }
        )
        assert subject.type == SubjectType.CONTRACT_CLAUSE
        assert subject.payload["contract_type"] == "NDA"
        assert subject.payload["counterparty"] == "ACME Corp"

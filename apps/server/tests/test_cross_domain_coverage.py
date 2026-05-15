"""Cross-domain integration tests.

Ensures non-engineering subjects are covered by tests.
Target: at least 50% of integration tests cover non-engineering subjects.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from rulerepo_server.domain.evaluation_subject import (
    BusinessEventSubject,
    CodeChangeSubject,
    CommunicationSubject,
    DecisionRequestSubject,
    DocumentArtifactSubject,
    EvaluationSubjectKind,
    TransactionSubject,
)
from rulerepo_server.domain.rule import ComputationalBody, NormativeBody, RuleKind
from rulerepo_server.domain.scope import Scope
from rulerepo_server.schemas.submissions import (
    BusinessEventInput,
    CommunicationInput,
    DecisionRequestInput,
    DocumentArtifactInput,
    TransactionInput,
    UniversalSubmissionRequest,
)
from rulerepo_server.services.evaluation.deterministic.lookup_evaluator import (
    clear_lookup_tables,
    evaluate_lookup,
    register_lookup_table,
)
from rulerepo_server.services.evaluation.deterministic.runner import (
    evaluate_deterministic,
)
from rulerepo_server.services.evaluation.deterministic.schema_evaluator import (
    evaluate_schema,
)

# ============================================================
# HR Domain Tests (BusinessEventSubject)
# ============================================================


class TestHROvertimeEvaluation:
    """Test HR overtime rules end-to-end."""

    def test_overtime_within_limit(self) -> None:
        """Monthly overtime of 40 hours should pass the 45-hour cap."""
        result = evaluate_deterministic(
            rule_id="hr_jp_001",
            kind=RuleKind.COMPUTATIONAL,
            body=ComputationalBody(
                expression="total_overtime <= 45",
                required_inputs=["total_overtime"],
                unit="hours",
            ),
            inputs={"total_overtime": 40},
        )
        assert result.resolved
        assert result.passed

    def test_overtime_exceeds_limit(self) -> None:
        """Monthly overtime of 50 hours should fail the 45-hour cap."""
        result = evaluate_deterministic(
            rule_id="hr_jp_001",
            kind=RuleKind.COMPUTATIONAL,
            body=ComputationalBody(
                expression="total_overtime <= 45",
                required_inputs=["total_overtime"],
                unit="hours",
            ),
            inputs={"total_overtime": 50},
        )
        assert result.resolved
        assert not result.passed

    def test_overtime_with_exception_predicate(self) -> None:
        """Overtime exceeding limit but with exception predicate needs LLM followup."""
        result = evaluate_deterministic(
            rule_id="hr_jp_001",
            kind=RuleKind.COMPUTATIONAL,
            body=ComputationalBody(
                expression="total_overtime <= 45",
                required_inputs=["total_overtime"],
                unit="hours",
                exception_predicate="has_active_special_36_agreement",
            ),
            inputs={"total_overtime": 50},
        )
        assert not result.resolved
        assert not result.passed
        assert result.needs_llm_followup

    def test_paid_leave_compliance(self) -> None:
        """Employee must take at least 5 days of paid leave."""
        result = evaluate_deterministic(
            rule_id="hr_jp_003",
            kind=RuleKind.COMPUTATIONAL,
            body=ComputationalBody(
                expression="used_paid_leave_days >= 5",
                required_inputs=["used_paid_leave_days"],
                unit="days",
            ),
            inputs={"used_paid_leave_days": 3},
        )
        assert result.resolved
        assert not result.passed

    def test_hr_event_subject_creation(self) -> None:
        """Test creating a BusinessEventSubject for HR overtime."""
        subject = BusinessEventSubject(
            kind=EvaluationSubjectKind.BUSINESS_EVENT,
            actor_id="E001",
            occurred_at=datetime.now(UTC),
            event_type="register_overtime",
            payload={"employee_id": "E001", "month": "2026-04", "overtime_hours": 50},
        )
        assert subject.kind == EvaluationSubjectKind.BUSINESS_EVENT
        assert subject.event_type == "register_overtime"

    def test_hr_submission_schema(self) -> None:
        """Test that HR overtime can be submitted via the universal endpoint."""
        req = UniversalSubmissionRequest(
            subject={
                "kind": "business_event",
                "event_type": "register_overtime",
                "payload": {"employee_id": "E001", "overtime_hours": 50},
            },
            scope={"domain": "hr", "org_unit": "acme/jp"},
            mode="preflight",
        )
        assert isinstance(req.subject, BusinessEventInput)
        assert req.scope is not None
        assert req.scope.domain == "hr"


# ============================================================
# Legal Domain Tests (DocumentArtifactSubject)
# ============================================================


class TestLegalContractReview:
    """Test legal contract review rules."""

    def test_contract_subject_creation(self) -> None:
        """Test creating a DocumentArtifactSubject for contract review."""
        subject = DocumentArtifactSubject(
            kind=EvaluationSubjectKind.DOCUMENT_ARTIFACT,
            document_id="contract_001",
            sections=[
                {"title": "反社会的勢力排除", "content": "当事者は反社会的勢力に該当しないことを保証する"},
                {"title": "損害賠償", "content": "損害賠償は契約金額を上限とする"},
            ],
            intent="draft_review",
        )
        assert subject.kind == EvaluationSubjectKind.DOCUMENT_ARTIFACT
        assert len(subject.sections) == 2

    def test_legal_scope_matching(self) -> None:
        """Legal rules with JP jurisdiction should match JP-scoped requests."""
        rule_scope = Scope(
            domain="legal",
            subject_type="contract_draft",
            attributes={"jurisdiction": "JP"},
        )
        request_scope = Scope(
            domain="legal",
            subject_type="contract_draft",
            attributes={"jurisdiction": "JP"},
        )
        assert rule_scope.matches(request_scope)

    def test_legal_scope_jurisdiction_mismatch(self) -> None:
        """JP jurisdiction rule should not match US-scoped request."""
        rule_scope = Scope(
            domain="legal",
            subject_type="contract_draft",
            attributes={"jurisdiction": "JP"},
        )
        request_scope = Scope(
            domain="legal",
            subject_type="contract_draft",
            attributes={"jurisdiction": "US"},
        )
        assert not rule_scope.matches(request_scope)

    def test_contract_submission_schema(self) -> None:
        """Test contract review submission via universal endpoint."""
        req = UniversalSubmissionRequest(
            subject={
                "kind": "document_artifact",
                "document_id": "contract_001",
                "intent": "draft_review",
                "sections": [{"title": "NDA", "content": "Standard NDA terms"}],
            },
            scope={"domain": "legal"},
        )
        assert isinstance(req.subject, DocumentArtifactInput)

    def test_normative_rule_needs_llm(self) -> None:
        """Normative rules without predicates should require LLM follow-up."""
        result = evaluate_deterministic(
            rule_id="legal_jp_001",
            kind=RuleKind.NORMATIVE,
            body=NormativeBody(),
            inputs={},
        )
        assert not result.resolved
        assert result.needs_llm_followup


# ============================================================
# Finance Domain Tests (TransactionSubject)
# ============================================================


class TestFinanceExpenseEvaluation:
    """Test finance expense rules end-to-end."""

    def test_expense_within_limit(self) -> None:
        """Entertainment expense within per-person limit should pass."""
        result = evaluate_deterministic(
            rule_id="fin_jp_001",
            kind=RuleKind.COMPUTATIONAL,
            body=ComputationalBody(
                expression="per_person_amount <= 5000",
                required_inputs=["per_person_amount"],
                unit="JPY",
            ),
            inputs={"per_person_amount": 4000},
        )
        assert result.resolved
        assert result.passed

    def test_expense_exceeds_limit(self) -> None:
        """Entertainment expense exceeding per-person limit should fail."""
        result = evaluate_deterministic(
            rule_id="fin_jp_001",
            kind=RuleKind.COMPUTATIONAL,
            body=ComputationalBody(
                expression="per_person_amount <= 5000",
                required_inputs=["per_person_amount"],
                unit="JPY",
            ),
            inputs={"per_person_amount": 8000},
        )
        assert result.resolved
        assert not result.passed

    def test_receipt_required_schema(self) -> None:
        """Expense above 3000 JPY requires receipt_url."""
        result = evaluate_schema(
            schema_def={
                "receipt_url": {
                    "type": "str",
                    "required": True,
                    "condition": "amount >= 3000",
                },
                "amount": {"type": "float", "required": True, "min": 0},
            },
            data={"amount": 5000.0},  # No receipt_url
        )
        assert not result.passed
        assert any("receipt_url" in e for e in result.errors)

    def test_receipt_not_required_below_threshold(self) -> None:
        """Expense below 3000 JPY does not require receipt."""
        result = evaluate_schema(
            schema_def={
                "receipt_url": {
                    "type": "str",
                    "required": True,
                    "condition": "amount >= 3000",
                },
                "amount": {"type": "float", "required": True, "min": 0},
            },
            data={"amount": 2000.0},
        )
        assert result.passed

    def test_transaction_subject_creation(self) -> None:
        """Test creating a TransactionSubject for expense."""
        subject = TransactionSubject(
            kind=EvaluationSubjectKind.TRANSACTION,
            transaction_type="expense",
            amount=Decimal("12000"),
            currency="JPY",
            counterparties=["restaurant_abc"],
        )
        assert subject.kind == EvaluationSubjectKind.TRANSACTION
        assert subject.amount == Decimal("12000")

    def test_transaction_submission_schema(self) -> None:
        """Test transaction submission via universal endpoint."""
        req = UniversalSubmissionRequest(
            subject={
                "kind": "transaction",
                "transaction_type": "expense",
                "amount": "5000",
                "currency": "JPY",
            },
            scope={"domain": "finance"},
        )
        assert isinstance(req.subject, TransactionInput)

    def test_vendor_sanctions_lookup(self) -> None:
        """Vendor must not be on the sanctions list."""
        clear_lookup_tables()
        register_lookup_table(
            "sanctioned_vendors",
            [
                {"vendor_id": "V001", "name": "Bad Corp"},
                {"vendor_id": "V002", "name": "Evil Inc"},
            ],
        )
        # Good vendor
        result = evaluate_lookup(
            table_name="sanctioned_vendors",
            lookup_key="vendor_id",
            lookup_value="V999",
            must_exist=False,  # Must NOT be on the list
        )
        assert result.passed

        # Sanctioned vendor
        result = evaluate_lookup(
            table_name="sanctioned_vendors",
            lookup_key="vendor_id",
            lookup_value="V001",
            must_exist=False,
        )
        assert not result.passed
        clear_lookup_tables()


# ============================================================
# Sales Domain Tests (DecisionRequestSubject)
# ============================================================


class TestSalesPricingEvaluation:
    """Test sales pricing rules."""

    def test_discount_within_limit(self) -> None:
        """Discount within 20% limit should pass."""
        result = evaluate_deterministic(
            rule_id="sales_jp_001",
            kind=RuleKind.COMPUTATIONAL,
            body=ComputationalBody(
                expression="discount_pct <= 20",
                required_inputs=["discount_pct"],
                unit="percent",
            ),
            inputs={"discount_pct": 15},
        )
        assert result.resolved
        assert result.passed

    def test_discount_exceeds_limit(self) -> None:
        """Discount above 20% should fail."""
        result = evaluate_deterministic(
            rule_id="sales_jp_001",
            kind=RuleKind.COMPUTATIONAL,
            body=ComputationalBody(
                expression="discount_pct <= 20",
                required_inputs=["discount_pct"],
                unit="percent",
            ),
            inputs={"discount_pct": 25},
        )
        assert result.resolved
        assert not result.passed

    def test_decision_request_subject(self) -> None:
        """Test creating a DecisionRequestSubject for discount approval."""
        subject = DecisionRequestSubject(
            kind=EvaluationSubjectKind.DECISION_REQUEST,
            request_type="discount_approval",
            description="25% discount for enterprise client",
            options=["approve", "deny", "escalate"],
        )
        assert subject.kind == EvaluationSubjectKind.DECISION_REQUEST

    def test_decision_submission_schema(self) -> None:
        """Test decision request submission via universal endpoint."""
        req = UniversalSubmissionRequest(
            subject={
                "kind": "decision_request",
                "request_type": "discount_approval",
                "description": "Special discount request",
            },
            scope={"domain": "sales"},
        )
        assert isinstance(req.subject, DecisionRequestInput)


# ============================================================
# Communication Domain Tests (CommunicationSubject)
# ============================================================


class TestCommunicationCompliance:
    """Test communication/marketing rules."""

    def test_communication_subject_creation(self) -> None:
        """Test creating a CommunicationSubject for marketing email."""
        subject = CommunicationSubject(
            kind=EvaluationSubjectKind.COMMUNICATION,
            channel="email",
            sender_id="marketing@company.com",
            recipient_ids=["customer@example.com"],
            content="Our product is the best in the market!",
        )
        assert subject.kind == EvaluationSubjectKind.COMMUNICATION
        assert subject.channel == "email"

    def test_communication_scope(self) -> None:
        """Test communication scope matching."""
        rule_scope = Scope(domain="communication", subject_type="marketing_copy")
        request_scope = Scope(domain="communication", subject_type="marketing_copy")
        assert rule_scope.matches(request_scope)

    def test_communication_submission_schema(self) -> None:
        """Test communication submission via universal endpoint."""
        req = UniversalSubmissionRequest(
            subject={
                "kind": "communication",
                "channel": "social_media",
                "content": "Amazing new product launch!",
            },
            scope={"domain": "communication"},
        )
        assert isinstance(req.subject, CommunicationInput)

    def test_prize_promotion_limit(self) -> None:
        """Prize promotion value must not exceed 50000 JPY."""
        result = evaluate_deterministic(
            rule_id="comm_jp_006",
            kind=RuleKind.COMPUTATIONAL,
            body=ComputationalBody(
                expression="prize_value <= 50000",
                required_inputs=["prize_value"],
                unit="JPY",
            ),
            inputs={"prize_value": 60000},
        )
        assert result.resolved
        assert not result.passed


# ============================================================
# Engineering Domain Tests (CodeChangeSubject) -- kept for balance
# ============================================================


class TestEngineeringCodeChange:
    """Engineering tests for balance -- should be minority of total."""

    def test_code_change_subject(self) -> None:
        """Test creating a CodeChangeSubject."""
        subject = CodeChangeSubject(
            kind=EvaluationSubjectKind.CODE_CHANGE,
            diff="--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n-old\n+new",
            repository="my-repo",
        )
        assert subject.kind == EvaluationSubjectKind.CODE_CHANGE

    def test_engineering_scope(self) -> None:
        """Test legacy scope normalization for engineering."""
        scope = Scope.from_legacy_string("engineering/python")
        assert scope.domain == "engineering"
        assert scope.subject_type == "python_source"

    def test_code_change_submission_schema(self) -> None:
        """Test code change submission via universal endpoint."""
        req = UniversalSubmissionRequest(
            subject={
                "kind": "code_change",
                "diff": "some diff",
            },
        )
        assert req.subject.kind == "code_change"


# ============================================================
# Cross-Domain Scope Tests
# ============================================================


class TestCrossDomainScope:
    """Test scope matching across domains."""

    def test_global_rule_matches_all_domains(self) -> None:
        """A rule with no domain should match any request domain."""
        rule_scope = Scope(domain=None)
        for domain in ("legal", "hr", "finance", "sales", "communication", "engineering"):
            request_scope = Scope(domain=domain)
            assert rule_scope.matches(request_scope), f"Global rule should match {domain}"

    def test_org_unit_hierarchy(self) -> None:
        """A rule scoped to acme/ should match acme/jp/ and acme/jp/sales/."""
        rule_scope = Scope(domain="finance", org_unit="acme")
        assert rule_scope.matches(Scope(domain="finance", org_unit="acme/jp"))
        assert rule_scope.matches(Scope(domain="finance", org_unit="acme/jp/sales"))
        assert not rule_scope.matches(Scope(domain="finance", org_unit="globex"))

    @pytest.mark.parametrize(
        ("domain", "subject_type"),
        [
            ("legal", "contract_draft"),
            ("hr", "overtime_report"),
            ("finance", "expense"),
            ("sales", "discount_request"),
            ("communication", "marketing_copy"),
        ],
    )
    def test_non_engineering_scopes_constructible(self, domain: str, subject_type: str) -> None:
        """All non-engineering scopes should be constructible and matchable."""
        scope = Scope(domain=domain, subject_type=subject_type)
        assert scope.domain == domain
        assert scope.subject_type == subject_type
        assert scope.matches(Scope(domain=domain, subject_type=subject_type))

"""Unit tests for non-code discovery analyzers.

Tests HrPolicyAnalyzer, ExpenseGuidelineAnalyzer, and
CommunicationStandardAnalyzer with fixture documents.
"""

from __future__ import annotations

from rulerepo_server.services.discovery.analyzers.base import DiscoveryContext
from rulerepo_server.services.discovery.analyzers.communication_standard import (
    CommunicationStandardAnalyzer,
)
from rulerepo_server.services.discovery.analyzers.expense_guideline import (
    ExpenseGuidelineAnalyzer,
)
from rulerepo_server.services.discovery.analyzers.hr_policy import HrPolicyAnalyzer

# ---------------------------------------------------------------------------
# HrPolicyAnalyzer
# ---------------------------------------------------------------------------


class TestHrPolicyMustStatements:
    async def test_detects_must_in_employment_rules(self) -> None:
        content = (
            "# Employment Regulations\n\n"
            "All employees must submit leave requests at least 3 days in advance.\n"
            "Overtime work must be approved by the department head prior to execution.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["hr/employment_rules.md"],
            file_contents={"hr/employment_rules.md": content},
        )
        analyzer = HrPolicyAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 2
        for p in patterns:
            assert p.modality == "MUST"
            assert p.source_type == "hr_policy"
            assert p.confidence >= 0.8


class TestHrPolicyJapaneseLabor:
    async def test_detects_japanese_obligations(self) -> None:
        content = (
            "# 就業規則\n\n"
            "第1条 従業員は始業時刻までに出勤しなければならない。\n"
            "第2条 時間外労働は所属長の承認を得なければならない。\n"
        )
        ctx = DiscoveryContext(
            file_paths=["就業規則.md"],
            file_contents={"就業規則.md": content},
        )
        analyzer = HrPolicyAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 2
        for p in patterns:
            assert p.modality == "MUST"
            assert p.source_type == "hr_policy"

    async def test_detects_japanese_prohibitions(self) -> None:
        content = "# 服務規律\n\n従業員は就業時間中に私的な活動をしてはならない。\n"
        ctx = DiscoveryContext(
            file_paths=["hr/服務規律.md"],
            file_contents={"hr/服務規律.md": content},
        )
        analyzer = HrPolicyAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert patterns[0].modality == "MUST_NOT"


class TestHrPolicyThresholds:
    async def test_detects_hour_threshold(self) -> None:
        content = "# Overtime Policy\n\nEmployees must not exceed 45 hours of overtime per month.\n"
        ctx = DiscoveryContext(
            file_paths=["hr/overtime_policy.md"],
            file_contents={"hr/overtime_policy.md": content},
        )
        analyzer = HrPolicyAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert any("threshold:hours" in p.tags for p in patterns)

    async def test_detects_day_threshold(self) -> None:
        content = "# Leave Policy\n\nSick leave requests must be submitted within 3 days of return.\n"
        ctx = DiscoveryContext(
            file_paths=["hr/leave_policy.md"],
            file_contents={"hr/leave_policy.md": content},
        )
        analyzer = HrPolicyAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert any("threshold:days" in p.tags for p in patterns)


class TestHrPolicyConditional:
    async def test_detects_conditional_requirement(self) -> None:
        content = (
            "# Attendance\n\n"
            "If an employee is absent for more than 3 consecutive days, "
            "a medical certificate must be submitted.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["hr/attendance_rules.md"],
            file_contents={"hr/attendance_rules.md": content},
        )
        analyzer = HrPolicyAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert any("conditional" in p.tags for p in patterns)


class TestHrPolicySeverity:
    async def test_labor_law_keywords_critical(self) -> None:
        content = "# Labor Standards\n\nOvertime must comply with the 36協定 agreement limits.\n"
        ctx = DiscoveryContext(
            file_paths=["hr/labor_standards.md"],
            file_contents={"hr/labor_standards.md": content},
        )
        analyzer = HrPolicyAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert patterns[0].severity == "CRITICAL"


class TestHrPolicySkipsNonHr:
    async def test_ignores_non_hr_files(self) -> None:
        content = "All endpoints must return proper HTTP status codes.\n"
        ctx = DiscoveryContext(
            file_paths=["api_guide.md"],
            file_contents={"api_guide.md": content},
        )
        analyzer = HrPolicyAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) == 0


class TestHrPolicyEmptyInput:
    async def test_empty_content(self) -> None:
        ctx = DiscoveryContext(
            file_paths=["hr/empty.md"],
            file_contents={"hr/empty.md": ""},
        )
        analyzer = HrPolicyAnalyzer()
        patterns = await analyzer.analyze(ctx)
        assert len(patterns) == 0


class TestHrPolicyScope:
    async def test_attendance_scope(self) -> None:
        content = "# Attendance\n\nAll employees must clock in at the start of their shift.\n"
        ctx = DiscoveryContext(
            file_paths=["hr/attendance_policy.md"],
            file_contents={"hr/attendance_policy.md": content},
        )
        analyzer = HrPolicyAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert "hr/attendance" in patterns[0].scope


# ---------------------------------------------------------------------------
# ExpenseGuidelineAnalyzer
# ---------------------------------------------------------------------------


class TestExpenseGuidelineMustStatements:
    async def test_detects_must_in_expense_policy(self) -> None:
        content = (
            "# Expense Policy\n\n"
            "All expenses must be accompanied by an original receipt.\n"
            "Expense reports must be submitted within 30 days of the expense.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["finance/expense_policy.md"],
            file_contents={"finance/expense_policy.md": content},
        )
        analyzer = ExpenseGuidelineAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 2
        for p in patterns:
            assert p.source_type == "expense_guideline"
            assert "finance/expense" in p.scope


class TestExpenseGuidelineProhibitions:
    async def test_detects_prohibited_expenses(self) -> None:
        content = (
            "# Expense Restrictions\n\n"
            "Personal expenses are prohibited from reimbursement.\n"
            "Alcohol purchases are not permitted on company expense accounts.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["finance/expense_restrictions.md"],
            file_contents={"finance/expense_restrictions.md": content},
        )
        analyzer = ExpenseGuidelineAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 2
        for p in patterns:
            assert p.modality == "MUST_NOT"


class TestExpenseGuidelineApprovalLevels:
    async def test_detects_approval_requirements(self) -> None:
        content = (
            "# Approval Matrix\n\n"
            "Expenses over 100,000円 require department head approval.\n"
            "Expenses over 500,000円 require director approval.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["finance/approval_matrix.md"],
            file_contents={"finance/approval_matrix.md": content},
        )
        analyzer = ExpenseGuidelineAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 2
        assert any("approval" in p.tags for p in patterns)

    async def test_detects_pre_approval(self) -> None:
        content = "# Travel Policy\n\nAll international travel requires prior approval from the manager.\n"
        ctx = DiscoveryContext(
            file_paths=["finance/travel_policy.md"],
            file_contents={"finance/travel_policy.md": content},
        )
        analyzer = ExpenseGuidelineAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1


class TestExpenseGuidelineReceipts:
    async def test_detects_receipt_requirements(self) -> None:
        content = "# Documentation Requirements\n\nA receipt must be attached for every expense claim over 1,000円.\n"
        ctx = DiscoveryContext(
            file_paths=["経費精算規程.md"],
            file_contents={"経費精算規程.md": content},
        )
        analyzer = ExpenseGuidelineAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert any("category:receipt_required" in p.tags for p in patterns)


class TestExpenseGuidelineJapanese:
    async def test_detects_japanese_expense_rules(self) -> None:
        content = (
            "# 経費精算規程\n\n"
            "経費精算は月末までに提出しなければならない。\n"
            "領収書のない経費の精算は原則として認めない。\n"
        )
        ctx = DiscoveryContext(
            file_paths=["経費精算規程.md"],
            file_contents={"経費精算規程.md": content},
        )
        analyzer = ExpenseGuidelineAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 2
        modalities = {p.modality for p in patterns}
        assert "MUST" in modalities or "MUST_NOT" in modalities


class TestExpenseGuidelineSeverity:
    async def test_fraud_keywords_critical(self) -> None:
        content = "# Compliance\n\nFraudulent expense claims must be reported to compliance immediately.\n"
        ctx = DiscoveryContext(
            file_paths=["finance/expense_compliance.md"],
            file_contents={"finance/expense_compliance.md": content},
        )
        analyzer = ExpenseGuidelineAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert patterns[0].severity == "CRITICAL"


class TestExpenseGuidelineSkipsNonExpense:
    async def test_ignores_non_expense_files(self) -> None:
        content = "All API responses must include proper error codes.\n"
        ctx = DiscoveryContext(
            file_paths=["api_spec.md"],
            file_contents={"api_spec.md": content},
        )
        analyzer = ExpenseGuidelineAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) == 0


class TestExpenseGuidelineTags:
    async def test_travel_tag(self) -> None:
        content = "# Travel Expense Policy\n\nHotel expenses must not exceed the per diem rate for the destination.\n"
        ctx = DiscoveryContext(
            file_paths=["finance/travel_expense.md"],
            file_contents={"finance/travel_expense.md": content},
        )
        analyzer = ExpenseGuidelineAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        all_tags = []
        for p in patterns:
            all_tags.extend(p.tags)
        assert "travel" in all_tags or "per_diem" in all_tags


# ---------------------------------------------------------------------------
# CommunicationStandardAnalyzer
# ---------------------------------------------------------------------------


class TestCommunicationStandardToneRules:
    async def test_detects_prohibited_language(self) -> None:
        content = (
            "# Brand Voice Guidelines\n\n"
            "Never use slang or informal language in client communications.\n"
            "Avoid using jargon when writing for external audiences.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["marketing/brand_guidelines.md"],
            file_contents={"marketing/brand_guidelines.md": content},
        )
        analyzer = CommunicationStandardAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert any(p.modality == "MUST_NOT" for p in patterns)
        assert all(p.source_type == "communication_standard" for p in patterns)


class TestCommunicationStandardDisclaimers:
    async def test_detects_disclaimer_requirements(self) -> None:
        content = (
            "# Email Standards\n\n"
            "All external emails must include a confidentiality notice in the footer.\n"
            "The legal disclaimer must be appended to all outgoing correspondence.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["communications/email_standards.md"],
            file_contents={"communications/email_standards.md": content},
        )
        analyzer = CommunicationStandardAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 2
        assert any("disclaimer" in p.tags for p in patterns)


class TestCommunicationStandardChannels:
    async def test_detects_channel_specific_rules(self) -> None:
        content = (
            "# Social Media Policy\n\n"
            "All social media posts must be approved by the marketing team.\n"
            "Internal announcements should use the company intranet.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["marketing/social_media_policy.md"],
            file_contents={"marketing/social_media_policy.md": content},
        )
        analyzer = CommunicationStandardAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        all_tags = []
        for p in patterns:
            all_tags.extend(p.tags)
        # Should detect social_media or internal channel tags
        has_channel = any("channel:" in t for t in all_tags)
        assert has_channel


class TestCommunicationStandardMandatoryElements:
    async def test_detects_must_include(self) -> None:
        content = "# Email Template Guide\n\nAll client emails must include the company logo and contact information.\n"
        ctx = DiscoveryContext(
            file_paths=["brand/email_template_guide.md"],
            file_contents={"brand/email_template_guide.md": content},
        )
        analyzer = CommunicationStandardAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert any(p.modality == "MUST" for p in patterns)


class TestCommunicationStandardJapanese:
    async def test_detects_japanese_communication_rules(self) -> None:
        content = (
            "# コミュニケーションガイドライン\n\n"
            "社外メールには必ず免責事項を含めるものとする。\n"
            "不適切な表現の使用は禁止する。\n"
        )
        ctx = DiscoveryContext(
            file_paths=["コミュニケーション規程.md"],
            file_contents={"コミュニケーション規程.md": content},
        )
        analyzer = CommunicationStandardAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 2
        modalities = {p.modality for p in patterns}
        assert "MUST" in modalities or "MUST_NOT" in modalities


class TestCommunicationStandardSeverity:
    async def test_legal_keywords_critical(self) -> None:
        content = "# Legal Communications\n\nMarketing materials must comply with all regulatory requirements.\n"
        ctx = DiscoveryContext(
            file_paths=["marketing/guidelines.md"],
            file_contents={"marketing/guidelines.md": content},
        )
        analyzer = CommunicationStandardAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert patterns[0].severity in ("CRITICAL", "HIGH")


class TestCommunicationStandardDepartment:
    async def test_sales_department_inferred(self) -> None:
        content = "# Sales Communication\n\nAll sales proposals must include current pricing information.\n"
        ctx = DiscoveryContext(
            file_paths=["sales/communication_guide.md"],
            file_contents={"sales/communication_guide.md": content},
        )
        analyzer = CommunicationStandardAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        # Department should be inferred as "sales"
        assert any("sales" in s for p in patterns for s in p.scope)


class TestCommunicationStandardSkipsNonComms:
    async def test_ignores_non_communication_files(self) -> None:
        content = "All database queries must use parameterized statements.\n"
        ctx = DiscoveryContext(
            file_paths=["security_rules.md"],
            file_contents={"security_rules.md": content},
        )
        analyzer = CommunicationStandardAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) == 0


class TestCommunicationStandardEmpty:
    async def test_empty_content(self) -> None:
        ctx = DiscoveryContext(
            file_paths=["brand/empty.md"],
            file_contents={"brand/empty.md": ""},
        )
        analyzer = CommunicationStandardAnalyzer()
        patterns = await analyzer.analyze(ctx)
        assert len(patterns) == 0


class TestCommunicationStandardPreferred:
    async def test_detects_preferred_style(self) -> None:
        content = (
            "# Writing Style\n\n"
            "Preferred: use active voice in all communications.\n"
            "Use 'we' rather than passive constructions when referring to the company.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["brand/style_guide.md"],
            file_contents={"brand/style_guide.md": content},
        )
        analyzer = CommunicationStandardAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert any(p.modality == "SHOULD" for p in patterns)

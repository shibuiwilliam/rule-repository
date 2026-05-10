"""Tests for deepened surface adapters.

Verifies the domain-specific logic added to contract, transaction,
message, and human_action surface adapters — clause hierarchy detection,
threshold analysis, PII scanning, action classification, etc.
"""

from __future__ import annotations

import pytest

# --------------------------------------------------------------------------
# Contract Adapter Tests
# --------------------------------------------------------------------------


class TestContractAdapter:
    """Tests for ContractSurfaceAdapter domain logic."""

    @pytest.fixture
    def adapter(self):
        from rulerepo_server.services.evaluation.surfaces.contract.adapter import (
            ContractSurfaceAdapter,
        )

        return ContractSurfaceAdapter()

    def test_resolve_scopes_nda(self, adapter):
        """NDA contract type resolves to confidentiality scope."""
        scopes = adapter.resolve_scopes({"contract_type": "nda", "clause_type": "confidentiality"})
        assert "legal/confidentiality" in scopes
        assert "legal/contract" in scopes

    def test_resolve_scopes_employment(self, adapter):
        """Employment contract resolves to hr/employment scope."""
        scopes = adapter.resolve_scopes({"contract_type": "employment", "clause_type": "termination"})
        assert "hr/employment" in scopes
        assert "legal/clause/termination" in scopes

    def test_resolve_scopes_procurement(self, adapter):
        """Procurement contract resolves to finance/procurement scope."""
        scopes = adapter.resolve_scopes({"contract_type": "procurement"})
        assert "finance/procurement" in scopes

    def test_resolve_scopes_with_governing_law_japan(self, adapter):
        """Japanese governing law adds jurisdiction/jp scope."""
        scopes = adapter.resolve_scopes(
            {
                "contract_type": "service",
                "governing_law": "日本法",
            }
        )
        assert "jurisdiction/jp" in scopes

    def test_resolve_scopes_with_governing_law_us(self, adapter):
        """New York governing law adds jurisdiction/us scope."""
        scopes = adapter.resolve_scopes(
            {
                "contract_type": "license",
                "governing_law": "Laws of the State of New York",
            }
        )
        assert "jurisdiction/us" in scopes

    @pytest.mark.asyncio
    async def test_parse_detects_japanese_hierarchy(self, adapter):
        """Parse detects Japanese clause structure (条/項/号)."""
        payload = {
            "clause_text": "第3条第2項 甲は、乙に対して秘密情報を開示する。",
            "clause_type": "confidentiality",
            "contract_type": "nda",
        }
        result = await adapter.parse(payload)
        assert result.payload["hierarchy"]["system"] == "japanese"
        assert result.payload["hierarchy"]["article"] == 3
        assert result.payload["hierarchy"]["paragraph"] == 2
        assert "第3条" in result.payload["hierarchy"]["reference"]

    @pytest.mark.asyncio
    async def test_parse_detects_western_hierarchy(self, adapter):
        """Parse detects Western clause structure (Article/Section)."""
        payload = {
            "clause_text": "Article 5, Section 3.1 - The Disclosing Party shall...",
            "clause_type": "confidentiality",
            "contract_type": "nda",
        }
        result = await adapter.parse(payload)
        assert result.payload["hierarchy"]["system"] == "western"
        assert "Article 5" in result.payload["hierarchy"]["reference"]

    @pytest.mark.asyncio
    async def test_parse_classifies_risk_level(self, adapter):
        """Parse classifies clause risk level based on type."""
        high_risk = await adapter.parse({"clause_text": "test", "clause_type": "indemnity"})
        assert high_risk.payload["risk_level"] == "high"

        medium_risk = await adapter.parse({"clause_text": "test", "clause_type": "payment"})
        assert medium_risk.payload["risk_level"] == "medium"

        low_risk = await adapter.parse({"clause_text": "test", "clause_type": "notice"})
        assert low_risk.payload["risk_level"] == "low"

    @pytest.mark.asyncio
    async def test_parse_extracts_governing_law(self, adapter):
        """Parse detects governing law from text."""
        payload = {
            "clause_text": "本契約は日本法に準拠するものとする。",
            "clause_type": "governing_law",
        }
        result = await adapter.parse(payload)
        assert "governing_law" in result.facts
        assert "日本法" in result.facts["governing_law"]

    def test_prompt_hints_are_proactive(self, adapter):
        """Prompt hints provide proactive guidance, not defensive warnings."""
        hints = adapter.get_prompt_hints()
        assert "Identify the clause number" in hints
        assert "Assess risk level" in hints
        assert "text_rewrite" in hints
        # Should NOT contain defensive "do not" language about code
        assert "Do NOT provide file paths" not in hints
        assert "DO NOT provide code" not in hints


# --------------------------------------------------------------------------
# Transaction Adapter Tests
# --------------------------------------------------------------------------


class TestTransactionAdapter:
    """Tests for TransactionSurfaceAdapter domain logic."""

    @pytest.fixture
    def adapter(self):
        from rulerepo_server.services.evaluation.surfaces.transaction.adapter import (
            TransactionSurfaceAdapter,
        )

        return TransactionSurfaceAdapter()

    def test_resolve_scopes_expense(self, adapter):
        """Expense transaction resolves to finance/expense scope."""
        scopes = adapter.resolve_scopes({"transaction_type": "expense"})
        assert "finance/expense" in scopes

    def test_resolve_scopes_attendance(self, adapter):
        """Attendance transaction resolves to hr/attendance scope."""
        scopes = adapter.resolve_scopes({"transaction_type": "attendance"})
        assert "hr/attendance" in scopes

    def test_resolve_scopes_entertainment_adds_anti_bribery(self, adapter):
        """Entertainment expense adds anti-bribery scope."""
        scopes = adapter.resolve_scopes({"transaction_type": "entertainment"})
        assert "compliance/anti-bribery" in scopes
        assert "finance/expense" in scopes

    def test_resolve_scopes_gift_category(self, adapter):
        """Gift category adds anti-bribery scope."""
        scopes = adapter.resolve_scopes({"transaction_type": "expense", "category": "gift"})
        assert "compliance/anti-bribery" in scopes

    @pytest.mark.asyncio
    async def test_parse_detects_transaction_type(self, adapter):
        """Parse detects transaction type from explicit field."""
        payload = {"transaction_type": "expense", "amount": 50000, "currency": "JPY"}
        result = await adapter.parse(payload)
        assert result.facts["transaction_type"] == "expense"

    @pytest.mark.asyncio
    async def test_parse_validates_missing_fields(self, adapter):
        """Parse identifies missing required fields."""
        payload = {"transaction_type": "expense_claim", "amount": 30000}
        # Missing: category, description, receipt_attached
        result = await adapter.parse(payload)
        missing = result.facts.get("missing_required_fields", [])
        assert "category" in missing
        assert "description" in missing

    @pytest.mark.asyncio
    async def test_parse_checks_thresholds(self, adapter):
        """Parse performs threshold analysis for known transaction types."""
        payload = {"transaction_type": "expense", "amount": 200000, "currency": "JPY"}
        result = await adapter.parse(payload)
        threshold_info = result.facts.get("threshold_analysis", {})
        assert threshold_info.get("highest_exceeded") is not None
        # 200,000 JPY exceeds manager_approve_max (100,000)
        assert threshold_info["amount_jpy"] == 200000

    @pytest.mark.asyncio
    async def test_parse_extracts_approval_chain(self, adapter):
        """Parse extracts approval chain from payload."""
        payload = {
            "transaction_type": "purchase_order",
            "amount": 1000000,
            "currency": "JPY",
            "approval_chain": [
                {"role": "manager", "id": "M001", "status": "approved"},
                {"role": "director", "id": "D001", "status": "pending"},
            ],
        }
        result = await adapter.parse(payload)
        assert len(result.facts["approval_chain"]) == 2

    @pytest.mark.asyncio
    async def test_parse_heuristic_type_detection(self, adapter):
        """Parse detects transaction type from payload content heuristically."""
        payload = {"facts": {"overtime_hours": 30, "employee_id": "E001"}}
        result = await adapter.parse(payload)
        assert result.facts["transaction_type"] == "overtime"

    def test_prompt_hints_are_proactive(self, adapter):
        """Prompt hints provide proactive guidance."""
        hints = adapter.get_prompt_hints()
        assert "Check amount against policy thresholds" in hints
        assert "Verify required approvals" in hints
        assert "JSON path" in hints
        assert "DO NOT provide code" not in hints


# --------------------------------------------------------------------------
# Message Adapter Tests
# --------------------------------------------------------------------------


class TestMessageAdapter:
    """Tests for MessageSurfaceAdapter domain logic."""

    @pytest.fixture
    def adapter(self):
        from rulerepo_server.services.evaluation.surfaces.message.adapter import (
            MessageSurfaceAdapter,
        )

        return MessageSurfaceAdapter()

    def test_resolve_scopes_external_email(self, adapter):
        """External email resolves to sales/communication scope."""
        scopes = adapter.resolve_scopes({"channel": "email", "audience": "external"})
        assert "sales/communication" in scopes
        assert "compliance/data-protection" in scopes

    def test_resolve_scopes_internal_chat(self, adapter):
        """Internal Slack message resolves to internal communication scope."""
        scopes = adapter.resolve_scopes({"channel": "slack", "audience": "internal"})
        assert "general/internal-communication" in scopes

    def test_resolve_scopes_press_release(self, adapter):
        """Press release resolves to marketing/external scope."""
        scopes = adapter.resolve_scopes({"channel": "press_release", "audience": "external"})
        assert "marketing/external" in scopes
        assert "compliance/disclosure" in scopes

    def test_resolve_scopes_social_media(self, adapter):
        """Social media resolves to marketing/external and advertising scope."""
        scopes = adapter.resolve_scopes({"channel": "twitter", "audience": "external"})
        assert "marketing/external" in scopes
        assert "compliance/advertising" in scopes

    @pytest.mark.asyncio
    async def test_parse_detects_pii(self, adapter):
        """Parse detects PII patterns in content."""
        payload = {
            "content": "お客様の山田太郎様のメールアドレスはtaro@example.comで、電話は03-1234-5678です。",
            "channel": "email",
            "sender": "sales@mycompany.co.jp",
            "recipients": ["client@external.com"],
        }
        result = await adapter.parse(payload)
        pii = result.facts.get("pii_detected", [])
        pii_types = [p["type"] for p in pii]
        assert "email_address" in pii_types
        assert "phone_jp" in pii_types

    @pytest.mark.asyncio
    async def test_parse_detects_health_claims(self, adapter):
        """Parse detects unverified health claims."""
        payload = {
            "content": "この製品は病気を治る効果があります。ぜひお試しください。",
            "channel": "email",
            "sender": "marketing@company.co.jp",
            "recipients": ["customer@example.com"],
        }
        result = await adapter.parse(payload)
        claims = result.facts.get("unverified_claims", [])
        assert "health_claim" in claims

    @pytest.mark.asyncio
    async def test_parse_detects_financial_claims(self, adapter):
        """Parse detects unverified financial claims."""
        payload = {
            "content": "This investment has a guaranteed return of 20% per year.",
            "channel": "email",
        }
        result = await adapter.parse(payload)
        claims = result.facts.get("unverified_claims", [])
        assert "financial_claim" in claims

    @pytest.mark.asyncio
    async def test_parse_detects_confidential_markers(self, adapter):
        """Parse detects confidentiality markers."""
        payload = {
            "content": "【社外秘】来期の売上計画について",
            "channel": "email",
            "recipients": ["partner@external.com"],
        }
        result = await adapter.parse(payload)
        assert result.facts.get("contains_confidential_markers") is True

    @pytest.mark.asyncio
    async def test_parse_classifies_audience_internal(self, adapter):
        """Parse classifies internal audience from shared domain."""
        payload = {
            "content": "会議の件",
            "channel": "email",
            "sender": "alice@mycompany.co.jp",
            "recipients": ["bob@mycompany.co.jp", "charlie@mycompany.co.jp"],
        }
        result = await adapter.parse(payload)
        assert result.facts["audience"] == "internal"

    @pytest.mark.asyncio
    async def test_parse_classifies_audience_external(self, adapter):
        """Parse classifies external audience when domains differ."""
        payload = {
            "content": "Hello",
            "channel": "email",
            "sender": "alice@mycompany.co.jp",
            "recipients": ["client@other.com"],
        }
        result = await adapter.parse(payload)
        assert result.facts["audience"] == "external"

    def test_prompt_hints_are_proactive(self, adapter):
        """Prompt hints provide proactive guidance."""
        hints = adapter.get_prompt_hints()
        assert "Flag PII exposure" in hints or "PII" in hints
        assert "unverified claims" in hints or "claims" in hints
        assert "DO NOT provide code" not in hints


# --------------------------------------------------------------------------
# Human Action Adapter Tests
# --------------------------------------------------------------------------


class TestHumanActionAdapter:
    """Tests for HumanActionSurfaceAdapter domain logic."""

    @pytest.fixture
    def adapter(self):
        from rulerepo_server.services.evaluation.surfaces.human_action.adapter import (
            HumanActionSurfaceAdapter,
        )

        return HumanActionSurfaceAdapter()

    def test_resolve_scopes_overtime(self, adapter):
        """Overtime action resolves to hr/attendance scope."""
        scopes = adapter.resolve_scopes({"action": "register_overtime", "actor_department": "sales"})
        assert "hr/attendance" in scopes
        assert "department/sales" in scopes

    def test_resolve_scopes_approval(self, adapter):
        """Approval action resolves to governance/approval scope."""
        scopes = adapter.resolve_scopes({"action": "approve_expense", "actor_department": "finance"})
        assert "governance/approval" in scopes
        assert "finance/approval-authority" in scopes

    def test_resolve_scopes_override(self, adapter):
        """Override action resolves to governance/override and compliance scope."""
        scopes = adapter.resolve_scopes({"action": "force_approve"})
        assert "governance/override" in scopes
        assert "compliance/exception" in scopes

    def test_resolve_scopes_leave(self, adapter):
        """Leave action resolves to hr/leave scope."""
        scopes = adapter.resolve_scopes({"action": "submit_leave"})
        assert "hr/leave" in scopes

    @pytest.mark.asyncio
    async def test_parse_classifies_action_type(self, adapter):
        """Parse classifies action into type categories."""
        payload = {"action": "approve_expense", "actor_id": "M001"}
        result = await adapter.parse(payload)
        assert result.payload["action_type"] == "approval"

    @pytest.mark.asyncio
    async def test_parse_classifies_overtime(self, adapter):
        """Parse classifies overtime as attendance type."""
        payload = {"action": "register_overtime", "actor_id": "E001"}
        result = await adapter.parse(payload)
        assert result.payload["action_type"] == "attendance"

    @pytest.mark.asyncio
    async def test_parse_enriches_actor_context(self, adapter):
        """Parse enriches actor context from payload fields."""
        payload = {
            "action": "submit_expense",
            "actor_id": "E001",
            "actor_role": "engineer",
            "actor_department": "engineering",
            "actor_seniority": 2,
        }
        result = await adapter.parse(payload)
        actor_ctx = result.facts["actor_context"]
        assert actor_ctx["role"] == "engineer"
        assert actor_ctx["department"] == "engineering"
        assert actor_ctx["seniority"] == 2

    @pytest.mark.asyncio
    async def test_parse_checks_authority_insufficient(self, adapter):
        """Parse flags insufficient authority for approval actions."""
        payload = {
            "action": "approve_expense",
            "actor_id": "E001",
            "actor_seniority": 1,  # Below min for approval (3)
        }
        result = await adapter.parse(payload)
        auth = result.facts["authority_check"]
        assert auth["authorized"] is False
        assert auth["actor_seniority"] == 1
        assert auth["required_seniority"] == 3

    @pytest.mark.asyncio
    async def test_parse_checks_authority_sufficient(self, adapter):
        """Parse confirms sufficient authority."""
        payload = {
            "action": "approve_expense",
            "actor_id": "M001",
            "actor_seniority": 4,  # Above min for approval (3)
        }
        result = await adapter.parse(payload)
        auth = result.facts["authority_check"]
        assert auth["authorized"] is True

    @pytest.mark.asyncio
    async def test_parse_analyzes_temporal_context(self, adapter):
        """Parse analyzes temporal context from timestamp."""
        payload = {
            "action": "register_overtime",
            "actor_id": "E001",
            "timestamp": "2026-03-28T22:30:00+09:00",
        }
        result = await adapter.parse(payload)
        temporal = result.facts["temporal_context"]
        assert temporal["hour"] == 22
        assert temporal["is_business_hours"] is False
        assert temporal["is_fiscal_year_end"] is True  # March

    @pytest.mark.asyncio
    async def test_parse_creates_actor_object(self, adapter):
        """Parse creates Actor with enriched attributes."""
        payload = {
            "action": "register_overtime",
            "actor_id": "E001",
            "actor_role": "engineer",
            "actor_department": "engineering",
        }
        result = await adapter.parse(payload)
        assert result.actor is not None
        assert result.actor.identifier == "user:E001"
        assert result.actor.attributes["role"] == "engineer"

    def test_prompt_hints_are_proactive(self, adapter):
        """Prompt hints provide proactive guidance."""
        hints = adapter.get_prompt_hints()
        assert "Verify actor has authority" in hints or "authority" in hints
        assert "temporal" in hints or "business hours" in hints
        assert "DO NOT provide code" not in hints
        assert "file-path" not in hints

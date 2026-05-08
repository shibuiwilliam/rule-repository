"""Unit tests for Compliance and Privacy Layer (workstream 7d).

Tests PII redaction, shadow store, erasure, approval policies.
"""

from __future__ import annotations

import pytest

from rulerepo_server.domain.classification import (
    Classification,
    classification_rank,
    clearance_sufficient,
)

# ---------------------------------------------------------------------------
# Classification domain tests
# ---------------------------------------------------------------------------


class TestClassification:
    def test_classification_ordering(self) -> None:
        assert classification_rank(Classification.PUBLIC) < classification_rank(Classification.INTERNAL)
        assert classification_rank(Classification.INTERNAL) < classification_rank(Classification.CONFIDENTIAL)
        assert classification_rank(Classification.CONFIDENTIAL) < classification_rank(Classification.RESTRICTED)

    def test_clearance_sufficient_public(self) -> None:
        assert clearance_sufficient(Classification.PUBLIC, Classification.PUBLIC) is True

    def test_clearance_insufficient(self) -> None:
        assert clearance_sufficient(Classification.PUBLIC, Classification.RESTRICTED) is False

    def test_clearance_higher_than_needed(self) -> None:
        assert clearance_sufficient(Classification.RESTRICTED, Classification.PUBLIC) is True


# ---------------------------------------------------------------------------
# PII redaction tests
# ---------------------------------------------------------------------------


class TestPIIRedaction:
    def test_redact_marked_fields(self) -> None:
        try:
            from rulerepo_server.core.pii.redactor import redact
        except ImportError:
            pytest.skip("PII redactor not yet available")

        data = {
            "employee_id": "E001",
            "name": "Taro Yamada",
            "overtime_hours": 50,
        }
        result = redact(data, pii_paths=["employee_id", "name"], classification="confidential")
        assert "REDACTED" in str(result.redacted_data.get("employee_id", ""))
        assert "REDACTED" in str(result.redacted_data.get("name", ""))
        assert result.redacted_data["overtime_hours"] == 50

    def test_redaction_preserves_non_pii(self) -> None:
        try:
            from rulerepo_server.core.pii.redactor import redact
        except ImportError:
            pytest.skip("PII redactor not yet available")

        data = {"role": "engineer", "ssn": "123-45-6789"}
        result = redact(data, pii_paths=["ssn"], classification="pii")
        assert result.redacted_data["role"] == "engineer"
        assert "123-45-6789" not in str(result.redacted_data["ssn"])

    def test_restore_from_map(self) -> None:
        try:
            from rulerepo_server.core.pii.redactor import redact, restore
        except ImportError:
            pytest.skip("PII redactor not yet available")

        data = {"name": "Hanako Suzuki", "age": 30}
        result = redact(data, pii_paths=["name"], classification="pii")
        restored = restore(result.redacted_data, result.redaction_map)
        assert restored["name"] == "Hanako Suzuki"
        assert restored["age"] == 30

    def test_detect_pii_fields(self) -> None:
        try:
            from rulerepo_server.core.pii.redactor import detect_pii
        except ImportError:
            pytest.skip("PII redactor not yet available")

        data = {
            "email": "test@example.com",
            "phone_number": "090-1234-5678",
            "department": "engineering",
            "ssn": "123-45-6789",
        }
        pii_fields = detect_pii(data)
        assert "email" in pii_fields
        assert "ssn" in pii_fields
        assert "department" not in pii_fields


# ---------------------------------------------------------------------------
# Shadow store tests
# ---------------------------------------------------------------------------


class TestShadowStore:
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self) -> None:
        try:
            from rulerepo_server.core.pii.shadow_store import ShadowStore
        except ImportError:
            pytest.skip("Shadow store not yet available")

        store = ShadowStore()
        redaction_map = {"[REDACTED:name:abc]": "Taro Yamada"}
        ref = await store.store("red_001", redaction_map, "tenant_1")
        assert ref is not None

        retrieved = await store.retrieve("red_001", "tenant_1")
        assert retrieved is not None
        assert retrieved["[REDACTED:name:abc]"] == "Taro Yamada"

    @pytest.mark.asyncio
    async def test_tenant_isolation(self) -> None:
        try:
            from rulerepo_server.core.pii.shadow_store import ShadowStore
        except ImportError:
            pytest.skip("Shadow store not yet available")

        store = ShadowStore()
        await store.store("red_001", {"placeholder": "value"}, "tenant_1")
        result = await store.retrieve("red_001", "tenant_2")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        try:
            from rulerepo_server.core.pii.shadow_store import ShadowStore
        except ImportError:
            pytest.skip("Shadow store not yet available")

        store = ShadowStore()
        await store.store("red_001", {"placeholder": "value"}, "tenant_1")
        deleted = await store.delete("red_001", "tenant_1")
        assert deleted is True
        result = await store.retrieve("red_001", "tenant_1")
        assert result is None


# ---------------------------------------------------------------------------
# Approval policy tests
# ---------------------------------------------------------------------------


class TestApprovalPolicy:
    def test_approval_requirement(self) -> None:
        try:
            from rulerepo_server.services.compliance.approval_policy import (
                ApprovalRequirement,
            )
        except ImportError:
            pytest.skip("Approval policy not yet available")

        req = ApprovalRequirement(role="legal_director", count=1, sla_hours=72)
        assert req.role == "legal_director"
        assert req.sla_hours == 72

    def test_policy_engine_matches(self) -> None:
        try:
            from rulerepo_server.services.compliance.approval_policy import (
                ApprovalPolicyEngine,
                ApprovalPolicyRule,
                ApprovalRequirement,
            )
        except ImportError:
            pytest.skip("Approval policy not yet available")

        engine = ApprovalPolicyEngine()
        engine.load_policies(
            [
                ApprovalPolicyRule(
                    match_conditions={"legal_force": "statutory"},
                    requirements=[
                        ApprovalRequirement(role="legal_director", count=1, sla_hours=72),
                    ],
                    mandatory_consultation=["dpo"],
                ),
            ]
        )
        requirements = engine.evaluate(
            rule_attrs={"legal_force": "statutory", "severity": "HIGH"},
            change_type="update",
        )
        assert len(requirements) >= 1
        assert any(r.role == "legal_director" for r in requirements)


# ---------------------------------------------------------------------------
# Read access logging tests
# ---------------------------------------------------------------------------


class TestReadAccessLog:
    @pytest.mark.asyncio
    async def test_log_and_retrieve(self) -> None:
        try:
            from rulerepo_server.services.compliance.read_access_log import ReadAccessLogger
        except ImportError:
            pytest.skip("Read access logger not yet available")

        logger = ReadAccessLogger()
        await logger.log_access(
            principal_id="u_001",
            resource_type="rule",
            resource_id="r_001",
            classification="confidential",
            tenant_id="t_001",
        )
        entries = await logger.get_access_log("r_001", "t_001")
        assert len(entries) >= 1
        assert entries[0].principal_id == "u_001"

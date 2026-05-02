"""Tests for the agent governance domain and service layer."""

from __future__ import annotations

from rulerepo_server.domain.agent import AgentType, TrustLevel


class TestTrustLevel:
    def test_all_values_exist(self) -> None:
        expected = {"untrusted", "limited", "standard", "elevated", "autonomous"}
        assert {t.value for t in TrustLevel} == expected

    def test_ordering(self) -> None:
        levels = list(TrustLevel)
        assert levels[0] == TrustLevel.UNTRUSTED
        assert levels[-1] == TrustLevel.AUTONOMOUS


class TestAgentType:
    def test_all_values_exist(self) -> None:
        expected = {"coding_assistant", "code_reviewer", "security_scanner", "deployment_agent", "custom"}
        assert {t.value for t in AgentType} == expected


class TestAgentSchemas:
    def test_register_request(self) -> None:
        from rulerepo_server.schemas.agent_governance import AgentRegisterRequest

        r = AgentRegisterRequest(agent_id="test-agent", display_name="Test Agent")
        assert r.agent_id == "test-agent"
        assert r.agent_type == "custom"

    def test_exception_request(self) -> None:
        from rulerepo_server.schemas.agent_governance import ExceptionRequest

        r = ExceptionRequest(
            agent_id="agent-1",
            rule_id="rule-1",
            context="Testing endpoint returns single resource",
            proposed_exception="Exempt single-resource GET from pagination",
        )
        assert r.proposed_exception.startswith("Exempt")

    def test_negotiation_request(self) -> None:
        from rulerepo_server.schemas.agent_governance import NegotiationRequest

        r = NegotiationRequest(
            agent_id="agent-1",
            evaluation_id="eval-1",
            rule_id="rule-1",
            original_verdict="DENY",
            counter_argument="This is a one-line lambda",
        )
        assert r.proposed_action == "proceed_with_justification"

    def test_session_create_request(self) -> None:
        from rulerepo_server.schemas.agent_governance import SessionCreateRequest

        r = SessionCreateRequest(agent_id="agent-1", context_ref="PR #123")
        assert r.context_ref == "PR #123"


class TestSerialization:
    def test_profile_to_dict(self) -> None:
        from unittest.mock import MagicMock

        from rulerepo_server.services.agent_governance.service import _profile_to_dict

        profile = MagicMock()
        profile.agent_id = "test"
        profile.display_name = "Test"
        profile.agent_type = "custom"
        profile.capabilities = ["write_code"]
        profile.trust_level = "untrusted"
        profile.compliance_rate_30d = 0.85
        profile.violation_patterns = {}
        profile.strength_areas = []
        profile.weakness_areas = []
        profile.can_propose_rules = False
        profile.can_vote_on_proposals = False
        profile.max_auto_fix_severity = "none"
        profile.suppressed_rule_ids = ["rule-1", "rule-2"]
        profile.created_at = None
        profile.updated_at = None

        d = _profile_to_dict(profile)
        assert d["agent_id"] == "test"
        assert d["trust_level"] == "untrusted"
        assert d["mastered_rules_count"] == 2
        assert d["compliance_rate_30d"] == 0.85

"""Tests for the governance proposal domain and service layer."""

from __future__ import annotations

import pytest

from rulerepo_server.domain.proposal import (
    ProposalStatus,
    ProposalType,
    validate_proposal_transition,
)

# ---------------------------------------------------------------------------
# Domain — Enum validation
# ---------------------------------------------------------------------------


class TestProposalType:
    def test_all_values_exist(self) -> None:
        expected = {"create", "amend", "retire", "merge", "split", "override"}
        assert {t.value for t in ProposalType} == expected

    def test_string_coercion(self) -> None:
        assert ProposalType("create") == ProposalType.CREATE


class TestProposalStatus:
    def test_all_values_exist(self) -> None:
        expected = {"draft", "review", "approved", "rejected", "enacted", "reverted", "closed"}
        assert {s.value for s in ProposalStatus} == expected


# ---------------------------------------------------------------------------
# Domain — Status transitions
# ---------------------------------------------------------------------------


class TestProposalTransitions:
    """Test the proposal status state machine."""

    def test_draft_to_review(self) -> None:
        validate_proposal_transition(ProposalStatus.DRAFT, ProposalStatus.REVIEW)

    def test_draft_to_closed(self) -> None:
        validate_proposal_transition(ProposalStatus.DRAFT, ProposalStatus.CLOSED)

    def test_review_to_approved(self) -> None:
        validate_proposal_transition(ProposalStatus.REVIEW, ProposalStatus.APPROVED)

    def test_review_to_rejected(self) -> None:
        validate_proposal_transition(ProposalStatus.REVIEW, ProposalStatus.REJECTED)

    def test_review_to_draft(self) -> None:
        validate_proposal_transition(ProposalStatus.REVIEW, ProposalStatus.DRAFT)

    def test_approved_to_enacted(self) -> None:
        validate_proposal_transition(ProposalStatus.APPROVED, ProposalStatus.ENACTED)

    def test_enacted_to_reverted(self) -> None:
        validate_proposal_transition(ProposalStatus.ENACTED, ProposalStatus.REVERTED)

    def test_reverted_to_closed(self) -> None:
        validate_proposal_transition(ProposalStatus.REVERTED, ProposalStatus.CLOSED)

    def test_same_status_no_op(self) -> None:
        validate_proposal_transition(ProposalStatus.DRAFT, ProposalStatus.DRAFT)

    def test_invalid_draft_to_enacted(self) -> None:
        with pytest.raises(ValueError, match="Invalid proposal transition"):
            validate_proposal_transition(ProposalStatus.DRAFT, ProposalStatus.ENACTED)

    def test_invalid_closed_to_anything(self) -> None:
        with pytest.raises(ValueError, match="Invalid proposal transition"):
            validate_proposal_transition(ProposalStatus.CLOSED, ProposalStatus.DRAFT)

    def test_invalid_enacted_to_approved(self) -> None:
        with pytest.raises(ValueError, match="Invalid proposal transition"):
            validate_proposal_transition(ProposalStatus.ENACTED, ProposalStatus.APPROVED)

    def test_invalid_review_to_enacted(self) -> None:
        with pytest.raises(ValueError, match="Invalid proposal transition"):
            validate_proposal_transition(ProposalStatus.REVIEW, ProposalStatus.ENACTED)

    def test_rejected_to_draft(self) -> None:
        """Rejected proposals can be returned to draft for revision."""
        validate_proposal_transition(ProposalStatus.REJECTED, ProposalStatus.DRAFT)

    def test_rejected_to_closed(self) -> None:
        validate_proposal_transition(ProposalStatus.REJECTED, ProposalStatus.CLOSED)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class TestProposalSchemas:
    def test_proposal_create_minimal(self) -> None:
        from rulerepo_server.schemas.proposal import ProposalCreate

        p = ProposalCreate(proposal_type="create", title="Test")
        assert p.proposal_type == "create"
        assert p.title == "Test"
        assert p.target_rule_ids == []
        assert p.change_spec == {}

    def test_proposal_create_full(self) -> None:
        from rulerepo_server.schemas.proposal import ProposalCreate

        p = ProposalCreate(
            proposal_type="amend",
            title="Update severity",
            description="Increasing severity of input validation rule.",
            target_rule_ids=["abc-123"],
            change_spec={"fields_changed": {"severity": {"old": "MEDIUM", "new": "HIGH"}}},
            required_approvers=["alice", "bob"],
        )
        assert len(p.target_rule_ids) == 1
        assert len(p.required_approvers) == 2

    def test_vote_request(self) -> None:
        from rulerepo_server.schemas.proposal import VoteRequest

        v = VoteRequest(vote="approve")
        assert v.vote == "approve"
        assert v.condition is None

        v2 = VoteRequest(vote="conditional", condition="Only if scope is narrowed")
        assert v2.condition == "Only if scope is narrowed"

    def test_comment_create(self) -> None:
        from rulerepo_server.schemas.proposal import CommentCreate

        c = CommentCreate(body="Looks good to me")
        assert c.body == "Looks good to me"
        assert c.comment_type == "comment"
        assert c.parent_comment_id is None


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_proposal_to_dict_structure(self) -> None:
        """Verify the proposal dict has all expected keys."""
        from unittest.mock import MagicMock

        from rulerepo_server.services.proposals.service import _proposal_to_dict

        proposal = MagicMock()
        proposal.id = "test-id"
        proposal.project_id = "proj-id"
        proposal.proposal_type = "create"
        proposal.status = "draft"
        proposal.author_id = "alice"
        proposal.title = "Test"
        proposal.description = "Desc"
        proposal.change_spec = {"new_rule_data": {}}
        proposal.target_rule_ids = []
        proposal.conflict_analysis = None
        proposal.impact_preview = None
        proposal.required_approvers = ["bob"]
        proposal.approval_votes = []
        proposal.enacted_at = None
        proposal.created_at = None
        proposal.updated_at = None

        d = _proposal_to_dict(proposal)
        assert d["id"] == "test-id"
        assert d["status"] == "draft"
        assert d["required_approvers"] == ["bob"]
        assert "comments" in d
        assert d["enacted_at"] is None

    def test_comment_to_dict_structure(self) -> None:
        from unittest.mock import MagicMock

        from rulerepo_server.services.proposals.service import _comment_to_dict

        comment = MagicMock()
        comment.id = "c-1"
        comment.proposal_id = "p-1"
        comment.parent_comment_id = None
        comment.author_id = "alice"
        comment.body = "LGTM"
        comment.comment_type = "comment"
        comment.suggestion_spec = None
        comment.resolved = False
        comment.created_at = None

        d = _comment_to_dict(comment)
        assert d["id"] == "c-1"
        assert d["body"] == "LGTM"
        assert d["resolved"] is False

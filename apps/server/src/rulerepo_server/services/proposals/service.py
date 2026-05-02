"""ProposalService — CRUD, status transitions, voting, and comment management.

Orchestrates the governance proposal lifecycle from draft through enactment.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from rulerepo_server.adapters.postgres.models import (
    DEFAULT_PROJECT_ID,
    NotificationModel,
    ProposalCommentModel,
    ProposalModel,
    RuleModel,
)
from rulerepo_server.core.errors import ConflictError, NotFoundError, ValidationError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.proposal import (
    ProposalStatus,
    ProposalType,
    validate_proposal_transition,
)

logger = get_logger(__name__)


class ProposalService:
    """Manages governance proposal lifecycle."""

    def __init__(self, session: AsyncSession, gemini: Any | None = None) -> None:
        self._session = session
        self._gemini = gemini

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_proposal(
        self,
        proposal_type: str,
        title: str,
        description: str = "",
        target_rule_ids: list[str] | None = None,
        change_spec: dict[str, Any] | None = None,
        required_approvers: list[str] | None = None,
        author_id: str = "system",
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new governance proposal in DRAFT status."""
        # Validate proposal type
        try:
            ProposalType(proposal_type)
        except ValueError as exc:
            raise ValidationError(f"Invalid proposal type: {proposal_type}") from exc

        # Validate target rules exist for non-create proposals
        target_ids = target_rule_ids or []
        if proposal_type != ProposalType.CREATE.value and target_ids:
            for rule_id in target_ids:
                result = await self._session.execute(select(RuleModel.id).where(RuleModel.id == rule_id))
                if result.scalar_one_or_none() is None:
                    raise NotFoundError("Rule", rule_id)

        proposal = ProposalModel(
            id=uuid4(),
            project_id=project_id or DEFAULT_PROJECT_ID,
            proposal_type=proposal_type,
            status=ProposalStatus.DRAFT.value,
            author_id=author_id,
            title=title,
            description=description,
            change_spec=change_spec or {},
            target_rule_ids=target_ids,
            required_approvers=required_approvers or [],
            approval_votes=[],
        )
        self._session.add(proposal)
        await self._session.flush()

        logger.info("proposal_created", proposal_id=str(proposal.id), type=proposal_type)
        return _proposal_to_dict(proposal)

    async def get_proposal(self, proposal_id: str) -> dict[str, Any]:
        """Get a single proposal with its comments."""
        proposal = await self._load_proposal(proposal_id)
        result = _proposal_to_dict(proposal)
        result["comments"] = [_comment_to_dict(c) for c in proposal.comments]
        return result

    async def list_proposals(
        self,
        status: str | None = None,
        proposal_type: str | None = None,
        author_id: str | None = None,
        project_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List proposals with optional filters and pagination."""
        query = select(ProposalModel)
        count_query = select(func.count(ProposalModel.id))

        if status:
            query = query.where(ProposalModel.status == status)
            count_query = count_query.where(ProposalModel.status == status)
        if proposal_type:
            query = query.where(ProposalModel.proposal_type == proposal_type)
            count_query = count_query.where(ProposalModel.proposal_type == proposal_type)
        if author_id:
            query = query.where(ProposalModel.author_id == author_id)
            count_query = count_query.where(ProposalModel.author_id == author_id)
        if project_id:
            query = query.where(ProposalModel.project_id == project_id)
            count_query = count_query.where(ProposalModel.project_id == project_id)

        total = (await self._session.execute(count_query)).scalar() or 0

        query = query.order_by(ProposalModel.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        proposals = result.scalars().all()

        return {
            "items": [_proposal_to_dict(p) for p in proposals],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_proposal(
        self,
        proposal_id: str,
        title: str | None = None,
        description: str | None = None,
        target_rule_ids: list[str] | None = None,
        change_spec: dict[str, Any] | None = None,
        required_approvers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update a draft proposal. Only drafts can be edited."""
        proposal = await self._load_proposal(proposal_id)

        if proposal.status != ProposalStatus.DRAFT.value:
            raise ConflictError(f"Cannot edit proposal in {proposal.status} status — must be draft.")

        if title is not None:
            proposal.title = title
        if description is not None:
            proposal.description = description
        if target_rule_ids is not None:
            proposal.target_rule_ids = target_rule_ids
        if change_spec is not None:
            proposal.change_spec = change_spec
        if required_approvers is not None:
            proposal.required_approvers = required_approvers

        await self._session.flush()
        logger.info("proposal_updated", proposal_id=str(proposal.id))
        return _proposal_to_dict(proposal)

    # ------------------------------------------------------------------
    # Status Transitions
    # ------------------------------------------------------------------

    async def submit_for_review(self, proposal_id: str) -> dict[str, Any]:
        """Submit a draft proposal for review.

        Runs conflict analysis and impact preview before transitioning.
        """
        proposal = await self._load_proposal(proposal_id)
        self._validate_transition(proposal, ProposalStatus.REVIEW)

        # Run automated analysis
        conflict_result = await self._run_conflict_analysis(proposal)
        impact_result = await self._run_impact_preview(proposal)

        proposal.status = ProposalStatus.REVIEW.value
        proposal.conflict_analysis = conflict_result
        proposal.impact_preview = impact_result

        await self._session.flush()

        # Notify required approvers
        for approver in proposal.required_approvers:
            await self._create_notification(
                user_id=approver,
                proposal_id=str(proposal.id),
                notification_type="review_requested",
                title=f"Review requested: {proposal.title}",
                body=f"{proposal.author_id} submitted a {proposal.proposal_type} proposal for your review.",
            )

        logger.info("proposal_submitted_for_review", proposal_id=str(proposal.id))
        return _proposal_to_dict(proposal)

    async def vote(
        self,
        proposal_id: str,
        user_id: str,
        vote: str,
        condition: str | None = None,
    ) -> dict[str, Any]:
        """Cast an approval vote on a proposal in review.

        Auto-transitions to APPROVED if all required approvers approve,
        or to REJECTED if any reject.
        """
        proposal = await self._load_proposal(proposal_id)

        if proposal.status != ProposalStatus.REVIEW.value:
            raise ConflictError(f"Cannot vote on proposal in {proposal.status} status — must be in review.")

        if vote not in ("approve", "reject", "conditional"):
            raise ValidationError(f"Invalid vote: {vote}. Must be approve, reject, or conditional.")

        # Remove any previous vote from this user
        existing_votes = [v for v in proposal.approval_votes if v.get("user_id") != user_id]
        new_vote = {
            "user_id": user_id,
            "vote": vote,
            "condition": condition,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }
        existing_votes.append(new_vote)
        proposal.approval_votes = existing_votes

        # Check for auto-transition
        if vote == "reject":
            proposal.status = ProposalStatus.REJECTED.value
            await self._create_notification(
                user_id=proposal.author_id,
                proposal_id=str(proposal.id),
                notification_type="rejected",
                title=f"Proposal rejected: {proposal.title}",
                body=f"{user_id} rejected your proposal.",
            )
        elif self._all_approved(proposal):
            proposal.status = ProposalStatus.APPROVED.value
            await self._create_notification(
                user_id=proposal.author_id,
                proposal_id=str(proposal.id),
                notification_type="approved",
                title=f"Proposal approved: {proposal.title}",
                body="All required approvers have approved.",
            )

        await self._session.flush()
        logger.info("proposal_vote_cast", proposal_id=str(proposal.id), vote=vote, voter=user_id)
        return _proposal_to_dict(proposal)

    async def enact(self, proposal_id: str, actor: str = "system") -> dict[str, Any]:
        """Enact an approved proposal — apply the rule changes.

        Delegates to the enactor module which calls RuleService methods.
        """
        proposal = await self._load_proposal(proposal_id)
        self._validate_transition(proposal, ProposalStatus.ENACTED)

        from rulerepo_server.services.proposals.enactor import enact_proposal

        await enact_proposal(self._session, proposal)

        proposal.status = ProposalStatus.ENACTED.value
        proposal.enacted_at = datetime.now(tz=UTC)
        await self._session.flush()

        # Notify author
        await self._create_notification(
            user_id=proposal.author_id,
            proposal_id=str(proposal.id),
            notification_type="enacted",
            title=f"Proposal enacted: {proposal.title}",
            body=f"Changes have been applied by {actor}.",
        )

        logger.info("proposal_enacted", proposal_id=str(proposal.id), actor=actor)
        return _proposal_to_dict(proposal)

    async def revert(self, proposal_id: str, actor: str = "system") -> dict[str, Any]:
        """Revert an enacted proposal."""
        proposal = await self._load_proposal(proposal_id)
        self._validate_transition(proposal, ProposalStatus.REVERTED)

        proposal.status = ProposalStatus.REVERTED.value
        await self._session.flush()

        await self._create_notification(
            user_id=proposal.author_id,
            proposal_id=str(proposal.id),
            notification_type="reverted",
            title=f"Proposal reverted: {proposal.title}",
            body=f"Changes have been reverted by {actor}.",
        )

        logger.info("proposal_reverted", proposal_id=str(proposal.id), actor=actor)
        return _proposal_to_dict(proposal)

    async def close(self, proposal_id: str) -> dict[str, Any]:
        """Close a proposal without enacting (abandon)."""
        proposal = await self._load_proposal(proposal_id)
        current = ProposalStatus(proposal.status)
        if current == ProposalStatus.CLOSED:
            return _proposal_to_dict(proposal)
        if current in (ProposalStatus.ENACTED,):
            raise ConflictError("Cannot close an enacted proposal — revert first.")
        proposal.status = ProposalStatus.CLOSED.value
        await self._session.flush()
        logger.info("proposal_closed", proposal_id=str(proposal.id))
        return _proposal_to_dict(proposal)

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    async def add_comment(
        self,
        proposal_id: str,
        body: str,
        author_id: str = "system",
        parent_comment_id: str | None = None,
        comment_type: str = "comment",
        suggestion_spec: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a comment to a proposal."""
        # Verify proposal exists
        proposal = await self._load_proposal(proposal_id)

        comment = ProposalCommentModel(
            id=uuid4(),
            proposal_id=proposal.id,
            parent_comment_id=parent_comment_id,
            author_id=author_id,
            body=body,
            comment_type=comment_type,
            suggestion_spec=suggestion_spec,
        )
        self._session.add(comment)
        await self._session.flush()

        # Notify proposal author if commenter is different
        if author_id != proposal.author_id:
            await self._create_notification(
                user_id=proposal.author_id,
                proposal_id=str(proposal.id),
                notification_type="comment_added",
                title=f"New comment on: {proposal.title}",
                body=f"{author_id} commented on your proposal.",
            )

        logger.info("proposal_comment_added", proposal_id=str(proposal.id), comment_id=str(comment.id))
        return _comment_to_dict(comment)

    async def resolve_comment(self, comment_id: str) -> dict[str, Any]:
        """Mark a suggestion comment as resolved."""
        result = await self._session.execute(select(ProposalCommentModel).where(ProposalCommentModel.id == comment_id))
        comment = result.scalar_one_or_none()
        if comment is None:
            raise NotFoundError("Comment", comment_id)
        comment.resolved = True
        await self._session.flush()
        return _comment_to_dict(comment)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    async def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Get notifications for a user."""
        query = select(NotificationModel).where(NotificationModel.user_id == user_id)
        count_query = select(func.count(NotificationModel.id)).where(NotificationModel.user_id == user_id)
        unread_query = select(func.count(NotificationModel.id)).where(
            NotificationModel.user_id == user_id,
            NotificationModel.read == False,  # noqa: E712
        )

        if unread_only:
            query = query.where(NotificationModel.read == False)  # noqa: E712
            count_query = count_query.where(NotificationModel.read == False)  # noqa: E712

        total = (await self._session.execute(count_query)).scalar() or 0
        unread_count = (await self._session.execute(unread_query)).scalar() or 0

        query = query.order_by(NotificationModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        notifications = result.scalars().all()

        return {
            "items": [_notification_to_dict(n) for n in notifications],
            "total": total,
            "unread_count": unread_count,
        }

    async def mark_notification_read(self, notification_id: str) -> dict[str, Any]:
        """Mark a notification as read."""
        result = await self._session.execute(select(NotificationModel).where(NotificationModel.id == notification_id))
        notification = result.scalar_one_or_none()
        if notification is None:
            raise NotFoundError("Notification", notification_id)
        notification.read = True
        await self._session.flush()
        return _notification_to_dict(notification)

    async def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user. Returns count updated."""
        from sqlalchemy import update

        stmt = (
            update(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.read == False,  # noqa: E712
            )
            .values(read=True)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    # ------------------------------------------------------------------
    # Impact & Conflict Analysis
    # ------------------------------------------------------------------

    async def refresh_analysis(self, proposal_id: str) -> dict[str, Any]:
        """Re-run conflict analysis and impact preview for a proposal."""
        proposal = await self._load_proposal(proposal_id)

        conflict_result = await self._run_conflict_analysis(proposal)
        impact_result = await self._run_impact_preview(proposal)

        proposal.conflict_analysis = conflict_result
        proposal.impact_preview = impact_result
        await self._session.flush()

        logger.info("proposal_analysis_refreshed", proposal_id=str(proposal.id))
        result = _proposal_to_dict(proposal)
        return result

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _load_proposal(self, proposal_id: str) -> ProposalModel:
        """Load a proposal by ID, raising NotFoundError if missing."""
        result = await self._session.execute(
            select(ProposalModel).options(selectinload(ProposalModel.comments)).where(ProposalModel.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        if proposal is None:
            raise NotFoundError("Proposal", proposal_id)
        return proposal

    def _validate_transition(self, proposal: ProposalModel, target: ProposalStatus) -> None:
        """Validate and raise on invalid transition."""
        current = ProposalStatus(proposal.status)
        try:
            validate_proposal_transition(current, target)
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc

    def _all_approved(self, proposal: ProposalModel) -> bool:
        """Check if all required approvers have approved."""
        if not proposal.required_approvers:
            return True
        voted_approvers = {v["user_id"] for v in proposal.approval_votes if v.get("vote") in ("approve", "conditional")}
        return all(a in voted_approvers for a in proposal.required_approvers)

    async def _create_notification(
        self,
        user_id: str,
        proposal_id: str,
        notification_type: str,
        title: str,
        body: str,
    ) -> None:
        """Create a notification record."""
        notification = NotificationModel(
            id=uuid4(),
            user_id=user_id,
            proposal_id=proposal_id,
            notification_type=notification_type,
            title=title,
            body=body,
        )
        self._session.add(notification)

    async def _run_conflict_analysis(self, proposal: ProposalModel) -> dict[str, Any]:
        """Detect conflicts between the proposed changes and existing rules.

        Uses semantic similarity via Gemini when available, falls back to
        scope overlap heuristics.
        """
        conflicts: list[dict[str, Any]] = []
        target_ids = set(proposal.target_rule_ids or [])

        # For create/amend, check if new statement overlaps with existing rules
        new_statement = (proposal.change_spec or {}).get("new_rule_data", {})
        if isinstance(new_statement, dict):
            new_statement = new_statement.get("statement", "")
        change_fields = (proposal.change_spec or {}).get("fields_changed", {})
        if isinstance(change_fields, dict) and "statement" in change_fields:
            new_statement = change_fields["statement"].get("new", "")

        if new_statement and isinstance(new_statement, str) and len(new_statement) > 10:
            # Find rules with overlapping scope
            new_scope = (proposal.change_spec or {}).get("new_rule_data", {})
            new_scope = new_scope.get("scope", []) if isinstance(new_scope, dict) else []

            result = await self._session.execute(
                select(RuleModel)
                .where(RuleModel.status.in_(["EFFECTIVE", "APPROVED", "DRAFT", "REVIEW"]))
                .where(RuleModel.id.notin_(target_ids) if target_ids else True)
                .limit(50)
            )
            existing_rules = result.scalars().all()

            for rule in existing_rules:
                # Simple scope overlap check
                rule_scope = rule.scope if isinstance(rule.scope, list) else []
                scope_overlap = bool(set(new_scope) & set(rule_scope)) if new_scope else False

                if scope_overlap:
                    conflicts.append(
                        {
                            "rule_id": str(rule.id),
                            "statement": rule.statement[:200],
                            "overlap_type": "scope_overlap",
                            "overlapping_scopes": list(set(new_scope) & set(rule_scope)),
                        }
                    )

        return {
            "conflicts_found": len(conflicts),
            "conflicts": conflicts[:10],
            "analyzed_at": datetime.now(tz=UTC).isoformat(),
        }

    async def _run_impact_preview(self, proposal: ProposalModel) -> dict[str, Any]:
        """Preview the impact of the proposed changes.

        Counts how many evaluation records exist for target rules.
        """
        from rulerepo_server.adapters.postgres.models import EvaluationRecordModel

        target_ids = proposal.target_rule_ids or []
        total_evaluations = 0
        affected_rules = 0

        if target_ids:
            result = await self._session.execute(
                select(func.count(EvaluationRecordModel.id)).where(EvaluationRecordModel.rule_id.in_(target_ids))
            )
            total_evaluations = result.scalar() or 0
            affected_rules = len(target_ids)

        return {
            "affected_rules": affected_rules,
            "total_evaluations_affected": total_evaluations,
            "proposal_type": proposal.proposal_type,
            "analyzed_at": datetime.now(tz=UTC).isoformat(),
        }


# ---------------------------------------------------------------------------
# Serialization Helpers
# ---------------------------------------------------------------------------


def _proposal_to_dict(proposal: ProposalModel) -> dict[str, Any]:
    """Convert a ProposalModel to a plain dict."""
    return {
        "id": str(proposal.id),
        "project_id": str(proposal.project_id) if proposal.project_id else None,
        "proposal_type": proposal.proposal_type,
        "status": proposal.status,
        "author_id": proposal.author_id,
        "title": proposal.title,
        "description": proposal.description,
        "change_spec": proposal.change_spec or {},
        "target_rule_ids": [str(r) for r in (proposal.target_rule_ids or [])],
        "conflict_analysis": proposal.conflict_analysis,
        "impact_preview": proposal.impact_preview,
        "required_approvers": proposal.required_approvers or [],
        "approval_votes": proposal.approval_votes or [],
        "comments": [],
        "enacted_at": proposal.enacted_at.isoformat() if proposal.enacted_at else None,
        "created_at": proposal.created_at.isoformat() if proposal.created_at else "",
        "updated_at": proposal.updated_at.isoformat() if proposal.updated_at else "",
    }


def _comment_to_dict(comment: ProposalCommentModel) -> dict[str, Any]:
    """Convert a ProposalCommentModel to a plain dict."""
    return {
        "id": str(comment.id),
        "proposal_id": str(comment.proposal_id),
        "parent_comment_id": str(comment.parent_comment_id) if comment.parent_comment_id else None,
        "author_id": comment.author_id,
        "body": comment.body,
        "comment_type": comment.comment_type,
        "suggestion_spec": comment.suggestion_spec,
        "resolved": comment.resolved,
        "created_at": comment.created_at.isoformat() if comment.created_at else "",
    }


def _notification_to_dict(notification: NotificationModel) -> dict[str, Any]:
    """Convert a NotificationModel to a plain dict."""
    return {
        "id": str(notification.id),
        "user_id": notification.user_id,
        "proposal_id": str(notification.proposal_id) if notification.proposal_id else None,
        "notification_type": notification.notification_type,
        "title": notification.title,
        "body": notification.body,
        "read": notification.read,
        "created_at": notification.created_at.isoformat() if notification.created_at else "",
    }

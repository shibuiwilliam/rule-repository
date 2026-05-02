"""AgentGovernanceService — profile management, adaptive delivery, negotiations.

Orchestrates all agent governance operations: registration, personalized rule
delivery, trust management, exception requests, verdict negotiations, and
multi-agent governance sessions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import (
    AgentExceptionRequestModel,
    AgentNegotiationModel,
    AgentProfileModel,
    EvaluationRecordModel,
    GovernanceSessionModel,
    RuleModel,
)
from rulerepo_server.core.errors import ConflictError, NotFoundError, ValidationError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.agent import AgentType, TrustLevel

logger = get_logger(__name__)


class AgentGovernanceService:
    """Manages agent governance profiles, delivery, and negotiations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    async def register_agent(
        self,
        agent_id: str,
        display_name: str,
        agent_type: str = "custom",
        capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        """Register a new agent or return existing profile."""
        # Validate agent type
        try:
            AgentType(agent_type)
        except ValueError as exc:
            raise ValidationError(f"Invalid agent type: {agent_type}") from exc

        existing = await self._session.execute(select(AgentProfileModel).where(AgentProfileModel.agent_id == agent_id))
        profile = existing.scalar_one_or_none()
        if profile is not None:
            logger.info("agent_already_registered", agent_id=agent_id)
            return _profile_to_dict(profile)

        profile = AgentProfileModel(
            agent_id=agent_id,
            display_name=display_name,
            agent_type=agent_type,
            capabilities=capabilities or [],
            trust_level=TrustLevel.UNTRUSTED.value,
        )
        self._session.add(profile)
        await self._session.flush()
        logger.info("agent_registered", agent_id=agent_id, type=agent_type)
        return _profile_to_dict(profile)

    async def get_profile(self, agent_id: str) -> dict[str, Any]:
        """Get an agent's governance profile."""
        profile = await self._load_profile(agent_id)
        return _profile_to_dict(profile)

    async def update_profile(
        self,
        agent_id: str,
        display_name: str | None = None,
        capabilities: list[str] | None = None,
        can_propose_rules: bool | None = None,
        can_vote_on_proposals: bool | None = None,
    ) -> dict[str, Any]:
        """Update an agent's profile settings."""
        profile = await self._load_profile(agent_id)
        if display_name is not None:
            profile.display_name = display_name
        if capabilities is not None:
            profile.capabilities = capabilities
        if can_propose_rules is not None:
            profile.can_propose_rules = can_propose_rules
        if can_vote_on_proposals is not None:
            profile.can_vote_on_proposals = can_vote_on_proposals
        await self._session.flush()
        return _profile_to_dict(profile)

    async def list_agents(
        self,
        sort_by: str = "compliance_rate_30d",
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List agents as a compliance leaderboard."""
        count = (await self._session.execute(select(func.count(AgentProfileModel.agent_id)))).scalar() or 0

        order_col = getattr(AgentProfileModel, sort_by, AgentProfileModel.compliance_rate_30d)
        query = select(AgentProfileModel).order_by(order_col.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        profiles = result.scalars().all()

        return {
            "items": [_profile_to_dict(p) for p in profiles],
            "total": count,
            "page": page,
            "page_size": page_size,
        }

    # ------------------------------------------------------------------
    # Adaptive Rule Delivery
    # ------------------------------------------------------------------

    async def get_personalized_rules(
        self,
        agent_id: str,
        file_paths: list[str] | None = None,
        max_rules: int = 20,
    ) -> dict[str, Any]:
        """Get rules personalized to an agent's history and mastery.

        Suppresses mastered rules and boosts rules the agent struggles with.
        """
        profile = await self._load_profile(agent_id)
        suppressed = set(profile.suppressed_rule_ids or [])
        weights = profile.personalized_rule_weights or {}

        # Get active rules
        query = select(RuleModel).where(
            RuleModel.status.in_(["EFFECTIVE", "APPROVED"]),
        )
        result = await self._session.execute(query)
        all_rules = result.scalars().all()

        # Filter and score
        scored_rules: list[tuple[float, dict[str, Any]]] = []
        for rule in all_rules:
            rule_id_str = str(rule.id)
            if rule_id_str in suppressed:
                continue

            score = 1.0
            # Apply personalized weights (higher = more important for this agent)
            weight = weights.get(rule_id_str, 0)
            score += weight * 0.01  # weight is in points (e.g., +20)

            scored_rules.append(
                (
                    score,
                    {
                        "id": rule_id_str,
                        "statement": rule.statement,
                        "modality": rule.modality,
                        "severity": rule.severity,
                        "scope": rule.scope,
                        "maturity_level": rule.maturity_level,
                        "personalized_weight": weight,
                    },
                )
            )

        # Sort by score descending, take top N
        scored_rules.sort(key=lambda x: x[0], reverse=True)
        rules = [r[1] for r in scored_rules[:max_rules]]

        return {
            "agent_id": agent_id,
            "trust_level": profile.trust_level,
            "rules_delivered": len(rules),
            "rules_suppressed": len(suppressed),
            "rules": rules,
        }

    async def get_mastery_report(self, agent_id: str) -> dict[str, Any]:
        """Get an agent's rule mastery report."""
        profile = await self._load_profile(agent_id)
        mastery = profile.mastery_data or {}
        return {
            "agent_id": agent_id,
            "mastered_rules": list(profile.suppressed_rule_ids or []),
            "mastery_data": mastery,
            "trust_level": profile.trust_level,
        }

    # ------------------------------------------------------------------
    # Exception Requests
    # ------------------------------------------------------------------

    async def request_exception(
        self,
        agent_id: str,
        rule_id: str,
        context: str,
        proposed_exception: str,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit a rule exception request."""
        await self._load_profile(agent_id)

        # Verify rule exists
        rule_result = await self._session.execute(select(RuleModel.id).where(RuleModel.id == rule_id))
        if rule_result.scalar_one_or_none() is None:
            raise NotFoundError("Rule", rule_id)

        req = AgentExceptionRequestModel(
            id=uuid4(),
            agent_id=agent_id,
            rule_id=rule_id,
            context=context,
            proposed_exception=proposed_exception,
            evidence=evidence or {},
        )
        self._session.add(req)
        await self._session.flush()

        logger.info("agent_exception_requested", agent_id=agent_id, rule_id=rule_id)
        return _exception_to_dict(req)

    async def list_exceptions(
        self,
        agent_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List exception requests with optional filters."""
        query = select(AgentExceptionRequestModel)
        count_q = select(func.count(AgentExceptionRequestModel.id))

        if agent_id:
            query = query.where(AgentExceptionRequestModel.agent_id == agent_id)
            count_q = count_q.where(AgentExceptionRequestModel.agent_id == agent_id)
        if status:
            query = query.where(AgentExceptionRequestModel.status == status)
            count_q = count_q.where(AgentExceptionRequestModel.status == status)

        total = (await self._session.execute(count_q)).scalar() or 0
        query = query.order_by(AgentExceptionRequestModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)

        return {
            "items": [_exception_to_dict(r) for r in result.scalars().all()],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def resolve_exception(
        self,
        exception_id: str,
        status: str,
        resolved_by: str = "system",
    ) -> dict[str, Any]:
        """Approve or reject an exception request."""
        result = await self._session.execute(
            select(AgentExceptionRequestModel).where(AgentExceptionRequestModel.id == exception_id)
        )
        req = result.scalar_one_or_none()
        if req is None:
            raise NotFoundError("ExceptionRequest", exception_id)
        req.status = status
        await self._session.flush()
        return _exception_to_dict(req)

    # ------------------------------------------------------------------
    # Verdict Negotiations
    # ------------------------------------------------------------------

    async def challenge_verdict(
        self,
        agent_id: str,
        evaluation_id: str,
        rule_id: str,
        original_verdict: str,
        counter_argument: str,
        proposed_action: str = "proceed_with_justification",
    ) -> dict[str, Any]:
        """Challenge a verdict with a counter-argument."""
        await self._load_profile(agent_id)

        negotiation = AgentNegotiationModel(
            id=uuid4(),
            agent_id=agent_id,
            evaluation_id=evaluation_id,
            rule_id=rule_id,
            original_verdict=original_verdict,
            counter_argument=counter_argument,
            proposed_action=proposed_action,
        )
        self._session.add(negotiation)
        await self._session.flush()

        logger.info(
            "agent_verdict_challenged",
            agent_id=agent_id,
            rule_id=rule_id,
            verdict=original_verdict,
        )
        return _negotiation_to_dict(negotiation)

    async def list_negotiations(
        self,
        agent_id: str | None = None,
        resolution: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List verdict negotiations."""
        query = select(AgentNegotiationModel)
        count_q = select(func.count(AgentNegotiationModel.id))

        if agent_id:
            query = query.where(AgentNegotiationModel.agent_id == agent_id)
            count_q = count_q.where(AgentNegotiationModel.agent_id == agent_id)
        if resolution:
            query = query.where(AgentNegotiationModel.resolution == resolution)
            count_q = count_q.where(AgentNegotiationModel.resolution == resolution)

        total = (await self._session.execute(count_q)).scalar() or 0
        query = query.order_by(AgentNegotiationModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)

        return {
            "items": [_negotiation_to_dict(n) for n in result.scalars().all()],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def resolve_negotiation(
        self,
        negotiation_id: str,
        resolution: str,
        resolved_by: str = "system",
    ) -> dict[str, Any]:
        """Resolve a verdict negotiation."""
        result = await self._session.execute(
            select(AgentNegotiationModel).where(AgentNegotiationModel.id == negotiation_id)
        )
        neg = result.scalar_one_or_none()
        if neg is None:
            raise NotFoundError("Negotiation", negotiation_id)
        neg.resolution = resolution
        neg.resolved_by = resolved_by
        await self._session.flush()
        return _negotiation_to_dict(neg)

    # ------------------------------------------------------------------
    # Governance Sessions
    # ------------------------------------------------------------------

    async def create_session(
        self,
        agent_id: str,
        context_ref: str = "",
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a multi-agent governance session."""
        await self._load_profile(agent_id)

        session_model = GovernanceSessionModel(
            id=uuid4(),
            project_id=project_id,
            context_ref=context_ref,
            agent_ids=[agent_id],
        )
        self._session.add(session_model)
        await self._session.flush()

        logger.info("governance_session_created", session_id=str(session_model.id))
        return _session_to_dict(session_model)

    async def join_session(
        self,
        session_id: str,
        agent_id: str,
    ) -> dict[str, Any]:
        """Join an existing governance session."""
        await self._load_profile(agent_id)

        result = await self._session.execute(
            select(GovernanceSessionModel).where(GovernanceSessionModel.id == session_id)
        )
        gov_session = result.scalar_one_or_none()
        if gov_session is None:
            raise NotFoundError("GovernanceSession", session_id)
        if not gov_session.active:
            raise ConflictError("Session is closed.")

        agents = list(gov_session.agent_ids or [])
        if agent_id not in agents:
            agents.append(agent_id)
            gov_session.agent_ids = agents
            await self._session.flush()

        return _session_to_dict(gov_session)

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Get session details including shared verdicts."""
        result = await self._session.execute(
            select(GovernanceSessionModel).where(GovernanceSessionModel.id == session_id)
        )
        gov_session = result.scalar_one_or_none()
        if gov_session is None:
            raise NotFoundError("GovernanceSession", session_id)
        return _session_to_dict(gov_session)

    async def publish_verdict(
        self,
        session_id: str,
        rule_id: str,
        verdict: str,
        agent_id: str,
    ) -> dict[str, Any]:
        """Publish a verdict to the shared session context."""
        result = await self._session.execute(
            select(GovernanceSessionModel).where(GovernanceSessionModel.id == session_id)
        )
        gov_session = result.scalar_one_or_none()
        if gov_session is None:
            raise NotFoundError("GovernanceSession", session_id)

        verdicts = dict(gov_session.shared_verdicts or {})
        verdicts[rule_id] = {"verdict": verdict, "agent_id": agent_id}
        gov_session.shared_verdicts = verdicts
        await self._session.flush()

        return _session_to_dict(gov_session)

    async def close_session(self, session_id: str) -> dict[str, Any]:
        """Close a governance session."""
        result = await self._session.execute(
            select(GovernanceSessionModel).where(GovernanceSessionModel.id == session_id)
        )
        gov_session = result.scalar_one_or_none()
        if gov_session is None:
            raise NotFoundError("GovernanceSession", session_id)
        gov_session.active = False
        gov_session.closed_at = datetime.now(tz=UTC)
        await self._session.flush()
        return _session_to_dict(gov_session)

    # ------------------------------------------------------------------
    # Trust Level Computation (called by cron worker)
    # ------------------------------------------------------------------

    async def compute_compliance_and_trust(self) -> int:
        """Recompute compliance rates and trust levels for all agents.

        Returns the number of agents updated.
        """
        from rulerepo_server.domain.agent import (
            TRUST_DEMOTION_THRESHOLD,
            TRUST_PROMOTION_THRESHOLDS,
        )

        result = await self._session.execute(select(AgentProfileModel))
        profiles = result.scalars().all()
        updated = 0

        for profile in profiles:
            # Compute 30-day compliance rate
            eval_result = await self._session.execute(
                select(
                    func.count(EvaluationRecordModel.id),
                    func.sum(func.cast(EvaluationRecordModel.verdict == "ALLOW", sa.Integer)),
                ).where(
                    EvaluationRecordModel.agent_id == profile.agent_id,
                    EvaluationRecordModel.created_at >= func.now() - func.cast("30 days", sa.Interval),
                )
            )
            row = eval_result.one()
            total_evals = row[0] or 0
            allow_count = row[1] or 0
            rate = allow_count / total_evals if total_evals > 0 else 0.0

            profile.compliance_rate_30d = rate

            # Trust level promotion/demotion
            current = TrustLevel(profile.trust_level)
            if rate < TRUST_DEMOTION_THRESHOLD and current != TrustLevel.UNTRUSTED:
                # Demote one level
                levels = list(TrustLevel)
                idx = levels.index(current)
                if idx > 0:
                    profile.trust_level = levels[idx - 1].value
                    logger.info("agent_trust_demoted", agent_id=profile.agent_id, new_level=profile.trust_level)
            else:
                # Check promotion thresholds
                levels = list(TrustLevel)
                idx = levels.index(current)
                if idx < len(levels) - 1:
                    next_level = levels[idx + 1]
                    threshold = TRUST_PROMOTION_THRESHOLDS.get(next_level, {})
                    min_compliance = float(threshold.get("min_compliance", 1.0))
                    if rate >= min_compliance and total_evals >= 10:
                        profile.trust_level = next_level.value
                        # Update permissions based on trust level
                        if next_level in (TrustLevel.ELEVATED, TrustLevel.AUTONOMOUS):
                            profile.can_propose_rules = True
                            profile.can_vote_on_proposals = True
                        elif next_level == TrustLevel.STANDARD:
                            profile.can_propose_rules = True
                        logger.info("agent_trust_promoted", agent_id=profile.agent_id, new_level=profile.trust_level)

            updated += 1

        await self._session.flush()
        logger.info("agent_trust_computation_completed", agents_updated=updated)
        return updated

    # ------------------------------------------------------------------
    # Mastery Tracking (called by cron worker)
    # ------------------------------------------------------------------

    async def compute_mastery(self) -> int:
        """Recompute rule mastery for all agents. Returns count updated."""
        from rulerepo_server.domain.agent import MASTERY_CONSECUTIVE_PASSES

        result = await self._session.execute(select(AgentProfileModel))
        profiles = result.scalars().all()
        updated = 0

        for profile in profiles:
            # Get last N evaluations per rule
            eval_result = await self._session.execute(
                select(
                    EvaluationRecordModel.rule_id,
                    func.count(EvaluationRecordModel.id).label("total"),
                    func.sum(func.cast(EvaluationRecordModel.verdict == "ALLOW", sa.Integer)).label("allow_count"),
                )
                .where(EvaluationRecordModel.agent_id == profile.agent_id)
                .group_by(EvaluationRecordModel.rule_id)
            )

            suppressed: list[str] = []
            mastery: dict[str, Any] = {}

            for row in eval_result.all():
                rule_id = str(row[0])
                total = row[1] or 0
                allows = row[2] or 0

                if total >= MASTERY_CONSECUTIVE_PASSES and allows == total:
                    suppressed.append(rule_id)
                    mastery[rule_id] = {"status": "mastered", "total_evals": total}
                elif total > 0:
                    mastery[rule_id] = {
                        "status": "learning",
                        "compliance_rate": allows / total,
                        "total_evals": total,
                    }

            profile.suppressed_rule_ids = suppressed
            profile.mastery_data = mastery
            updated += 1

        await self._session.flush()
        logger.info("agent_mastery_computation_completed", agents_updated=updated)
        return updated

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _load_profile(self, agent_id: str) -> AgentProfileModel:
        result = await self._session.execute(select(AgentProfileModel).where(AgentProfileModel.agent_id == agent_id))
        profile = result.scalar_one_or_none()
        if profile is None:
            raise NotFoundError("AgentProfile", agent_id)
        return profile


# ---------------------------------------------------------------------------
# Serialization Helpers
# ---------------------------------------------------------------------------


def _profile_to_dict(profile: AgentProfileModel) -> dict[str, Any]:
    return {
        "agent_id": profile.agent_id,
        "display_name": profile.display_name,
        "agent_type": profile.agent_type,
        "capabilities": profile.capabilities or [],
        "trust_level": profile.trust_level,
        "compliance_rate_30d": profile.compliance_rate_30d,
        "violation_patterns": profile.violation_patterns or {},
        "strength_areas": profile.strength_areas or [],
        "weakness_areas": profile.weakness_areas or [],
        "can_propose_rules": profile.can_propose_rules,
        "can_vote_on_proposals": profile.can_vote_on_proposals,
        "max_auto_fix_severity": profile.max_auto_fix_severity,
        "mastered_rules_count": len(profile.suppressed_rule_ids or []),
        "created_at": profile.created_at.isoformat() if profile.created_at else "",
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else "",
    }


def _exception_to_dict(req: AgentExceptionRequestModel) -> dict[str, Any]:
    return {
        "id": str(req.id),
        "agent_id": req.agent_id,
        "rule_id": str(req.rule_id),
        "context": req.context,
        "proposed_exception": req.proposed_exception,
        "evidence": req.evidence or {},
        "status": req.status,
        "proposal_id": str(req.proposal_id) if req.proposal_id else None,
        "created_at": req.created_at.isoformat() if req.created_at else "",
    }


def _negotiation_to_dict(neg: AgentNegotiationModel) -> dict[str, Any]:
    return {
        "id": str(neg.id),
        "agent_id": neg.agent_id,
        "evaluation_id": str(neg.evaluation_id),
        "rule_id": str(neg.rule_id),
        "original_verdict": neg.original_verdict,
        "counter_argument": neg.counter_argument,
        "proposed_action": neg.proposed_action,
        "resolution": neg.resolution,
        "resolved_by": neg.resolved_by,
        "created_at": neg.created_at.isoformat() if neg.created_at else "",
    }


def _session_to_dict(session: GovernanceSessionModel) -> dict[str, Any]:
    return {
        "id": str(session.id),
        "project_id": str(session.project_id) if session.project_id else None,
        "context_ref": session.context_ref,
        "agent_ids": session.agent_ids or [],
        "shared_verdicts": session.shared_verdicts or {},
        "active": session.active,
        "created_at": session.created_at.isoformat() if session.created_at else "",
        "closed_at": session.closed_at.isoformat() if session.closed_at else None,
    }

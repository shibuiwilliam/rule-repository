"""Proposal enactor — applies approved proposals to the rule corpus.

Handles all proposal types by translating change_spec into rule CRUD operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import RuleModel
from rulerepo_server.core.errors import ValidationError
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


async def enact_proposal(session: AsyncSession, proposal: Any) -> None:
    """Apply the changes described by an approved proposal.

    Args:
        session: Active database session.
        proposal: ProposalModel instance with change_spec populated.

    Raises:
        ValidationError: If the change_spec is malformed or targets are missing.
    """
    ptype = proposal.proposal_type
    spec = proposal.change_spec or {}

    if ptype == "create":
        await _enact_create(session, spec, proposal)
    elif ptype == "amend":
        await _enact_amend(session, spec, proposal)
    elif ptype == "retire":
        await _enact_retire(session, proposal)
    elif ptype == "merge":
        await _enact_merge(session, spec, proposal)
    elif ptype == "split":
        await _enact_split(session, spec, proposal)
    elif ptype == "override":
        await _enact_create(session, spec, proposal)  # override creates a new rule
    else:
        raise ValidationError(f"Unknown proposal type: {ptype}")

    logger.info("proposal_changes_applied", proposal_id=str(proposal.id), type=ptype)


async def _enact_create(session: AsyncSession, spec: dict, proposal: Any) -> None:
    """Create a new rule from the proposal's new_rule_data."""
    new_data = spec.get("new_rule_data", {})
    if not new_data or not new_data.get("statement"):
        raise ValidationError("Create proposal requires new_rule_data with a statement.")

    rule = RuleModel(
        id=uuid4(),
        project_id=proposal.project_id,
        statement=new_data["statement"],
        modality=new_data.get("modality", "MUST"),
        severity=new_data.get("severity", "MEDIUM"),
        status="EFFECTIVE",
        maturity_level=new_data.get("maturity_level", "experimental"),
        scope=new_data.get("scope", []),
        tags=new_data.get("tags", []),
        rationale=new_data.get("rationale", ""),
        governance=new_data.get("governance", {"owner": proposal.author_id, "approvers": []}),
    )
    session.add(rule)
    await session.flush()
    logger.info("proposal_rule_created", rule_id=str(rule.id))


async def _enact_amend(session: AsyncSession, spec: dict, proposal: Any) -> None:
    """Apply field-level changes to target rules."""
    fields_changed = spec.get("fields_changed", {})
    if not fields_changed:
        raise ValidationError("Amend proposal requires fields_changed in change_spec.")

    for rule_id in proposal.target_rule_ids or []:
        result = await session.execute(select(RuleModel).where(RuleModel.id == rule_id))
        rule = result.scalar_one_or_none()
        if rule is None:
            logger.warning("proposal_enact_rule_not_found", rule_id=str(rule_id))
            continue

        for field_name, change in fields_changed.items():
            new_value = change.get("new")
            if new_value is not None and hasattr(rule, field_name):
                setattr(rule, field_name, new_value)

        await session.flush()
        logger.info("proposal_rule_amended", rule_id=str(rule_id))


async def _enact_retire(session: AsyncSession, proposal: Any) -> None:
    """Retire target rules by setting effective_period.valid_until."""
    now_iso = datetime.now(tz=UTC).isoformat()
    for rule_id in proposal.target_rule_ids or []:
        result = await session.execute(select(RuleModel).where(RuleModel.id == rule_id))
        rule = result.scalar_one_or_none()
        if rule is None:
            continue

        ep = rule.effective_period or {}
        ep["valid_until"] = now_iso
        rule.effective_period = ep
        rule.status = "RETIRED"
        await session.flush()
        logger.info("proposal_rule_retired", rule_id=str(rule_id))


async def _enact_merge(session: AsyncSession, spec: dict, proposal: Any) -> None:
    """Merge source rules into a single new rule, retiring the sources."""
    new_data = spec.get("new_rule_data", {})
    if not new_data or not new_data.get("statement"):
        raise ValidationError("Merge proposal requires new_rule_data with a statement.")

    # Create the merged rule
    await _enact_create(session, spec, proposal)

    # Retire the source rules
    await _enact_retire(session, proposal)


async def _enact_split(session: AsyncSession, spec: dict, proposal: Any) -> None:
    """Split a rule into multiple sub-rules, retiring the original."""
    split_targets = spec.get("split_targets", [])
    if not split_targets:
        raise ValidationError("Split proposal requires split_targets in change_spec.")

    for target_data in split_targets:
        if not target_data.get("statement"):
            continue
        rule = RuleModel(
            id=uuid4(),
            project_id=proposal.project_id,
            statement=target_data["statement"],
            modality=target_data.get("modality", "MUST"),
            severity=target_data.get("severity", "MEDIUM"),
            status="EFFECTIVE",
            maturity_level="experimental",
            scope=target_data.get("scope", []),
            tags=target_data.get("tags", []),
            rationale=target_data.get("rationale", ""),
            governance={"owner": proposal.author_id, "approvers": []},
        )
        session.add(rule)

    await session.flush()

    # Retire the original
    await _enact_retire(session, proposal)

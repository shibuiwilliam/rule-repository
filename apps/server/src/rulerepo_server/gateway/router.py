"""Gateway API router — webhook ingestion, policy management, event stream."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger
from rulerepo_server.gateway.normalizers.email import EmailNormalizer
from rulerepo_server.gateway.normalizers.generic import GenericNormalizer
from rulerepo_server.gateway.normalizers.github import GitHubNormalizer
from rulerepo_server.gateway.normalizers.slack import SlackNormalizer
from rulerepo_server.gateway.normalizers.teams import TeamsNormalizer
from rulerepo_server.gateway.policy_engine import match_policies
from rulerepo_server.gateway.schemas import PolicyCreate, WebhookIngestRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/gateway", tags=["gateway"])

NORMALIZERS = {
    "github": GitHubNormalizer(),
    "slack": SlackNormalizer(),
    "teams": TeamsNormalizer(),
    "email": EmailNormalizer(),
    "generic": GenericNormalizer(),
}


# ---------------------------------------------------------------------------
# Webhook ingestion
# ---------------------------------------------------------------------------


@router.post("/ingest/{source}")
async def ingest_webhook(
    source: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Receive a webhook from an external source and evaluate against matched policies.

    Args:
        source: The event source (github, slack, generic).
    """
    from rulerepo_server.adapters.postgres.models import (
        EnforcementPolicyModel,
        GatewayEvaluationModel,
    )

    payload = await request.json()
    normalizer = NORMALIZERS.get(source, NORMALIZERS["generic"])
    event = normalizer.normalize(payload)

    # Load enabled policies
    result = await session.execute(select(EnforcementPolicyModel).where(EnforcementPolicyModel.enabled.is_(True)))
    policies_raw = [
        {
            "id": str(p.id),
            "name": p.name,
            "event_source": p.event_source,
            "event_type_pattern": p.event_type_pattern,
            "rule_scope": p.rule_scope,
            "evaluation_mode": p.evaluation_mode,
            "on_deny": p.on_deny,
            "response_actions": p.response_actions,
            "enabled": p.enabled,
        }
        for p in result.scalars().all()
    ]

    matched = match_policies(event, policies_raw)
    evaluations = []

    import time

    for policy in matched:
        eval_id = uuid4()
        eval_start = time.monotonic()

        # Run real evaluation via the evaluation engine
        try:
            from rulerepo_server.adapters.gemini.client import get_gemini_client
            from rulerepo_server.services.evaluation.service import EvaluationService

            gemini = None
            try:
                gemini = get_gemini_client()
            except Exception:
                pass
            eval_svc = EvaluationService(session, gemini)
            eval_result = await eval_svc.evaluate(
                facts={"subject": event.subject, **event.metadata},
                intent=event.subject,
                scope=policy.get("rule_scope"),
                mode=policy.get("evaluation_mode", "preflight"),
            )
            verdict = eval_result.overall_verdict.value
        except Exception as exc:
            logger.warning("gateway_evaluation_failed", error=str(exc))
            verdict = "ALLOW"

        elapsed_ms = int((time.monotonic() - eval_start) * 1000)

        # Dispatch actions on DENY verdicts (CLAUDE_ENHANCE.md §0.1)
        actions_executed: list[dict[str, Any]] = []
        if verdict == "DENY" and policy.get("response_actions"):
            from rulerepo_server.gateway.actions.webhook_out import send_webhook

            eval_payload = {
                "verdict": verdict,
                "event_source": event.source,
                "event_type": event.event_type,
                "subject": event.subject,
                "policy_name": policy["name"],
            }
            for action_cfg in policy["response_actions"]:
                action_type = action_cfg.get("type", "")
                match action_type:
                    case "webhook":
                        url = action_cfg.get("url", "")
                        if url:
                            success = await send_webhook(url, verdict, eval_payload)
                            actions_executed.append({"type": "webhook", "url": url, "success": success})
                    case _:
                        logger.info("gateway_action_skipped", type=action_type)

        eval_model = GatewayEvaluationModel(
            id=eval_id,
            policy_id=UUID(policy["id"]),
            event_source=event.source,
            event_type=event.event_type,
            event_payload=event.raw_payload,
            normalized_context={"subject": event.subject, **event.metadata},
            verdict=verdict,
            actions_taken=actions_executed,
            latency_ms=elapsed_ms,
        )
        session.add(eval_model)
        evaluations.append(
            {
                "evaluation_id": str(eval_id),
                "policy": policy["name"],
                "verdict": verdict,
                "actions": actions_executed,
            }
        )

    await session.flush()
    logger.info(
        "webhook_ingested",
        source=source,
        event_type=event.event_type,
        policies_matched=len(matched),
        evaluations=len(evaluations),
    )

    return {
        "source": source,
        "event_type": event.event_type,
        "policies_matched": len(matched),
        "evaluations": evaluations,
    }


@router.post("/ingest")
async def ingest_generic(
    data: WebhookIngestRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Receive a generic webhook event."""
    normalizer = GenericNormalizer()
    event = normalizer.normalize({"event_type": data.event_type, **data.payload})

    # Same flow as source-specific ingestion
    from rulerepo_server.adapters.postgres.models import EnforcementPolicyModel

    result = await session.execute(select(EnforcementPolicyModel).where(EnforcementPolicyModel.enabled.is_(True)))
    policies_raw = [
        {
            "id": str(p.id),
            "name": p.name,
            "event_source": p.event_source,
            "event_type_pattern": p.event_type_pattern,
            "enabled": p.enabled,
        }
        for p in result.scalars().all()
    ]
    matched = match_policies(event, policies_raw)

    return {
        "source": "generic",
        "event_type": event.event_type,
        "policies_matched": len(matched),
    }


# ---------------------------------------------------------------------------
# Policy CRUD
# ---------------------------------------------------------------------------


@router.post("/policies", status_code=201)
async def create_policy(
    data: PolicyCreate,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Create a new enforcement policy."""
    from rulerepo_server.adapters.postgres.models import EnforcementPolicyModel

    policy = EnforcementPolicyModel(
        id=uuid4(),
        name=data.name,
        description=data.description,
        event_source=data.event_source,
        event_type_pattern=data.event_type_pattern,
        rule_scope=data.rule_scope,
        rule_modality_filter=data.rule_modality_filter,
        rule_severity_min=data.rule_severity_min,
        evaluation_mode=data.evaluation_mode,
        context_extraction_prompt=data.context_extraction_prompt,
        response_actions=data.response_actions,
        on_deny=data.on_deny,
        enabled=data.enabled,
    )
    session.add(policy)
    await session.flush()
    await session.refresh(policy)

    return {
        "id": str(policy.id),
        "name": policy.name,
        "event_source": policy.event_source,
        "event_type_pattern": policy.event_type_pattern,
        "enabled": policy.enabled,
        "created_at": policy.created_at,
    }


@router.get("/policies")
async def list_policies(
    enabled_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List all enforcement policies."""
    from rulerepo_server.adapters.postgres.models import EnforcementPolicyModel

    query = select(EnforcementPolicyModel)
    if enabled_only:
        query = query.where(EnforcementPolicyModel.enabled.is_(True))

    result = await session.execute(query)
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "event_source": p.event_source,
            "event_type_pattern": p.event_type_pattern,
            "rule_scope": p.rule_scope,
            "evaluation_mode": p.evaluation_mode,
            "on_deny": p.on_deny,
            "enabled": p.enabled,
            "created_at": p.created_at,
        }
        for p in result.scalars().all()
    ]


@router.get("/evaluations")
async def list_evaluations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """List recent gateway evaluations."""
    from sqlalchemy import func

    from rulerepo_server.adapters.postgres.models import GatewayEvaluationModel

    query = (
        select(GatewayEvaluationModel)
        .order_by(GatewayEvaluationModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(query)
    evaluations = list(result.scalars().all())

    count_result = await session.execute(select(func.count()).select_from(GatewayEvaluationModel))
    total = count_result.scalar_one()

    return {
        "items": [
            {
                "id": str(e.id),
                "policy_id": str(e.policy_id),
                "event_source": e.event_source,
                "event_type": e.event_type,
                "verdict": e.verdict,
                "latency_ms": e.latency_ms,
                "created_at": e.created_at,
            }
            for e in evaluations
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

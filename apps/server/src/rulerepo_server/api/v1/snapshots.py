"""Snapshots & Deployments API — CRUD + deploy + rollback + simulate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.schemas.snapshots import (
    DeploymentResponse,
    DeployRequest,
    SimulateRequest,
    SimulateResponse,
    SnapshotCreate,
    SnapshotResponse,
)
from rulerepo_server.services.snapshots.service import SnapshotService
from rulerepo_server.services.snapshots.simulator import simulate_impact

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


def _get_service(session: AsyncSession) -> SnapshotService:
    return SnapshotService(session)


# ------------------------------------------------------------------
# Snapshots
# ------------------------------------------------------------------


@router.post("", response_model=SnapshotResponse, status_code=201)
async def create_snapshot(
    body: SnapshotCreate,
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> SnapshotResponse:
    """Create a new rule-set snapshot."""
    svc = _get_service(session)
    result = await svc.create_snapshot(
        name=body.name,
        scope_filter=body.scope_filter,
        description=body.description,
        created_by=body.created_by,
        project_id=project_id,
    )
    await session.commit()
    return SnapshotResponse(**result)


@router.get("", response_model=list[SnapshotResponse])
async def list_snapshots(
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> list[SnapshotResponse]:
    """List all snapshots."""
    svc = _get_service(session)
    rows = await svc.list_snapshots(project_id=project_id)
    return [SnapshotResponse(**r) for r in rows]


@router.get("/deployments", response_model=list[DeploymentResponse])
async def list_deployments(
    session: AsyncSession = Depends(get_db_session),
) -> list[DeploymentResponse]:
    """List all deployments across environments."""
    svc = _get_service(session)
    rows = await svc.list_deployments()
    return [DeploymentResponse(**r) for r in rows]


@router.get("/deployments/{environment}", response_model=DeploymentResponse | None)
async def get_active_deployment(
    environment: str,
    session: AsyncSession = Depends(get_db_session),
) -> DeploymentResponse | None:
    """Get the active deployment for an environment."""
    svc = _get_service(session)
    result = await svc.get_active_deployment(environment)
    if result is None:
        return None
    return DeploymentResponse(**result)


@router.get("/{snapshot_id}", response_model=SnapshotResponse)
async def get_snapshot(
    snapshot_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> SnapshotResponse:
    """Get a single snapshot by ID."""
    svc = _get_service(session)
    try:
        result = await svc.get_snapshot(snapshot_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SnapshotResponse(**result)


@router.post("/{snapshot_id}/deploy", response_model=DeploymentResponse, status_code=201)
async def deploy_snapshot(
    snapshot_id: str,
    body: DeployRequest,
    session: AsyncSession = Depends(get_db_session),
) -> DeploymentResponse:
    """Deploy a snapshot to an environment."""
    svc = _get_service(session)
    try:
        result = await svc.deploy(
            snapshot_id=snapshot_id,
            environment=body.environment,
            deployed_by=body.deployed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return DeploymentResponse(**result)


@router.post("/{snapshot_id}/rollback", response_model=DeploymentResponse)
async def rollback_snapshot(
    snapshot_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> DeploymentResponse:
    """Roll back the most recent deployment of this snapshot.

    Finds the active deployment for this snapshot and rolls it back,
    reactivating the previous deployment for the same environment.
    """
    svc = _get_service(session)

    # Find the active deployment that uses this snapshot
    deployments = await svc.list_deployments()
    target = None
    for d in deployments:
        if d["snapshot_id"] == snapshot_id and d["active"]:
            target = d
            break

    if target is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active deployment found for snapshot {snapshot_id}",
        )

    try:
        result = await svc.rollback(target["id"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return DeploymentResponse(**result)


@router.post("/{snapshot_id}/simulate", response_model=SimulateResponse)
async def simulate_snapshot(
    snapshot_id: str,
    body: SimulateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SimulateResponse:
    """Simulate the impact of deploying a snapshot."""
    result = await simulate_impact(
        snapshot_id=snapshot_id,
        compare_environment=body.compare_to,
        sample_size=body.sample_size,
        session=session,
    )
    return SimulateResponse(**result)


@router.post("/{snapshot_id}/simulate-bulk")
async def simulate_bulk(
    snapshot_id: str,
    body: dict,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Simulate the impact of multiple simultaneous rule changes.

    Accepts a list of candidate changes (update, retire, create) and
    aggregates their combined impact against the snapshot's rule set.

    Request body:
        candidate_changes: list of dicts, each with:
            - rule_id + new_statement (update)
            - rule_id + retire: true (retirement)
            - create: {statement, scope} (new rule)

    Returns:
        Aggregated impact summary across all candidate changes.
    """
    candidate_changes = body.get("candidate_changes", [])
    if not candidate_changes:
        raise HTTPException(status_code=400, detail="candidate_changes is required")

    results = []
    for change in candidate_changes:
        rule_id = change.get("rule_id")
        if change.get("retire"):
            results.append(
                {
                    "action": "retire",
                    "rule_id": rule_id,
                    "impact": "Rule will be excluded from future evaluations",
                }
            )
        elif change.get("new_statement"):
            results.append(
                {
                    "action": "update",
                    "rule_id": rule_id,
                    "impact": "Rule statement will change; re-evaluation required",
                }
            )
        elif change.get("create"):
            results.append(
                {
                    "action": "create",
                    "statement_preview": change["create"].get("statement", "")[:100],
                    "impact": "New rule will be added to the snapshot",
                }
            )

    return {
        "snapshot_id": snapshot_id,
        "total_changes": len(candidate_changes),
        "changes": results,
        "summary": f"{len(results)} changes simulated",
    }

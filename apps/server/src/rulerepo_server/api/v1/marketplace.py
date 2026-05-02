"""API router for the Rule Marketplace — package publishing, subscriptions, and conflict resolution."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.errors import ConflictError, NotFoundError, ValidationError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.schemas.marketplace import (
    ConflictResolveRequest,
    ConflictResponse,
    PackageCreate,
    PackageListResponse,
    PackageResponse,
    PackageRuleAdd,
    PackageRuleResponse,
    SubscribeRequest,
    SubscriptionResponse,
)
from rulerepo_server.services.marketplace.service import MarketplaceService

logger = get_logger(__name__)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


def _get_service(session: AsyncSession = Depends(get_db_session)) -> MarketplaceService:
    """Build a MarketplaceService with database session."""
    return MarketplaceService(session)


# ---------------------------------------------------------------------------
# Packages
# ---------------------------------------------------------------------------


@router.post("", response_model=PackageResponse, status_code=201)
async def create_package(
    body: PackageCreate,
    publisher_id: str = Query(default="system", description="Publisher user ID."),
    svc: MarketplaceService = Depends(_get_service),
) -> PackageResponse:
    """Create a new rule package."""
    try:
        result = await svc.create_package(
            name=body.name,
            version=body.version,
            description=body.description,
            license=body.license,
            homepage=body.homepage,
            metadata=body.metadata,
            publisher_id=publisher_id,
        )
        return PackageResponse(**result)
    except (ValidationError, ConflictError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("", response_model=PackageListResponse)
async def list_packages(
    published_only: bool = Query(default=True, description="Only show published packages."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    svc: MarketplaceService = Depends(_get_service),
) -> PackageListResponse:
    """List available packages with pagination."""
    result = await svc.list_packages(
        published_only=published_only,
        page=page,
        page_size=page_size,
    )
    return PackageListResponse(
        items=[PackageResponse(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{package_id}", response_model=PackageResponse)
async def get_package(
    package_id: str,
    svc: MarketplaceService = Depends(_get_service),
) -> PackageResponse:
    """Get a single package by ID."""
    try:
        result = await svc.get_package(package_id)
        return PackageResponse(**result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Package Rules
# ---------------------------------------------------------------------------


@router.post("/{package_id}/rules", response_model=PackageRuleResponse, status_code=201)
async def add_rule_to_package(
    package_id: str,
    body: PackageRuleAdd,
    svc: MarketplaceService = Depends(_get_service),
) -> PackageRuleResponse:
    """Add a rule to a package."""
    try:
        result = await svc.add_rule(
            package_id=package_id,
            rule_id=body.rule_id,
            package_rule_id=body.package_rule_id,
        )
        return PackageRuleResponse(**result)
    except (NotFoundError, ValidationError, ConflictError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete("/{package_id}/rules/{rule_id}", status_code=204)
async def remove_rule_from_package(
    package_id: str,
    rule_id: str,
    svc: MarketplaceService = Depends(_get_service),
) -> None:
    """Remove a rule from a package."""
    try:
        await svc.remove_rule(package_id=package_id, rule_id=rule_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------


@router.post("/{package_id}/publish", response_model=PackageResponse)
async def publish_package(
    package_id: str,
    svc: MarketplaceService = Depends(_get_service),
) -> PackageResponse:
    """Publish a package, making it available for subscription."""
    try:
        result = await svc.publish(package_id)
        return PackageResponse(**result)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------


@router.post("/subscribe", response_model=SubscriptionResponse, status_code=201)
async def subscribe(
    body: SubscribeRequest,
    svc: MarketplaceService = Depends(_get_service),
) -> SubscriptionResponse:
    """Subscribe a project to a package."""
    try:
        result = await svc.subscribe(
            project_id=body.project_id,
            package_id=body.package_id,
            version_constraint=body.version_constraint,
            auto_update=body.auto_update,
        )
        return SubscriptionResponse(**result)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    project_id: str = Query(..., description="Project ID to list subscriptions for."),
    svc: MarketplaceService = Depends(_get_service),
) -> list[SubscriptionResponse]:
    """List all subscriptions for a project."""
    results = await svc.list_subscriptions(project_id=project_id)
    return [SubscriptionResponse(**item) for item in results]


@router.delete("/subscriptions/{subscription_id}", status_code=204)
async def unsubscribe(
    subscription_id: str,
    svc: MarketplaceService = Depends(_get_service),
) -> None:
    """Unsubscribe from a package."""
    try:
        await svc.unsubscribe(subscription_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------


@router.get("/conflicts", response_model=list[ConflictResponse])
async def list_conflicts(
    project_id: str = Query(..., description="Project ID to list conflicts for."),
    resolution: str | None = Query(default=None, description="Filter by resolution status."),
    svc: MarketplaceService = Depends(_get_service),
) -> list[ConflictResponse]:
    """List cross-package rule conflicts for a project."""
    results = await svc.list_conflicts(project_id=project_id, resolution=resolution)
    return [ConflictResponse(**item) for item in results]


@router.post("/conflicts/{conflict_id}/resolve", response_model=ConflictResponse)
async def resolve_conflict(
    conflict_id: str,
    body: ConflictResolveRequest,
    svc: MarketplaceService = Depends(_get_service),
) -> ConflictResponse:
    """Resolve a cross-package rule conflict."""
    try:
        result = await svc.resolve_conflict(
            conflict_id=conflict_id,
            resolution=body.resolution,
            resolved_by=body.resolved_by,
        )
        return ConflictResponse(**result)
    except (NotFoundError, ConflictError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

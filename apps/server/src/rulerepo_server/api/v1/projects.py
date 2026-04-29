"""REST API routes for Project management."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from rulerepo_server.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


async def _get_project_service(
    session: AsyncSession = Depends(get_db_session),
) -> ProjectService:
    return ProjectService(session)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    service: ProjectService = Depends(_get_project_service),
) -> dict:
    """Create a new project."""
    return await service.create_project(name=body.name, description=body.description)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    service: ProjectService = Depends(_get_project_service),
) -> dict:
    """List all projects with pagination."""
    return await service.list_projects(page=page, page_size=page_size)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    service: ProjectService = Depends(_get_project_service),
) -> dict:
    """Get a single project by ID."""
    return await service.get_project(project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    service: ProjectService = Depends(_get_project_service),
) -> dict:
    """Update a project's name or description."""
    updates = body.model_dump(exclude_none=True)
    return await service.update_project(project_id, **updates)

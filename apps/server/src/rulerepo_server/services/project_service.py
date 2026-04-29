"""ProjectService — CRUD operations for projects."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.models import ProjectModel
from rulerepo_server.core.errors import NotFoundError
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class ProjectService:
    """Manages project lifecycle.

    Attributes:
        _session: Async database session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_project(self, name: str, description: str | None = None) -> dict[str, Any]:
        """Create a new project.

        Args:
            name: Project name.
            description: Optional description.

        Returns:
            Dict representation of the created project.
        """
        project = ProjectModel(
            id=uuid4(),
            name=name,
            description=description,
        )
        self._session.add(project)
        await self._session.flush()
        logger.info("project_created", project_id=str(project.id), name=name)
        return self._to_dict(project)

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """Get a project by ID.

        Args:
            project_id: UUID string of the project.

        Returns:
            Dict representation of the project.

        Raises:
            NotFoundError: If project does not exist.
        """
        result = await self._session.execute(
            select(ProjectModel).where(ProjectModel.id == UUID(project_id))
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project", project_id)
        return self._to_dict(project)

    async def list_projects(
        self, *, page: int = 1, page_size: int = 50
    ) -> dict[str, Any]:
        """List all projects with pagination.

        Args:
            page: Page number (1-based).
            page_size: Items per page.

        Returns:
            Paginated response dict.
        """
        offset = (page - 1) * page_size
        result = await self._session.execute(
            select(ProjectModel).order_by(ProjectModel.name).offset(offset).limit(page_size)
        )
        projects = list(result.scalars().all())

        count_result = await self._session.execute(
            select(func.count()).select_from(ProjectModel)
        )
        total = count_result.scalar_one()

        return {
            "items": [self._to_dict(p) for p in projects],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_project(
        self, project_id: str, **updates: Any
    ) -> dict[str, Any]:
        """Update a project's fields.

        Args:
            project_id: UUID string of the project.
            **updates: Fields to update (name, description).

        Returns:
            Updated project dict.

        Raises:
            NotFoundError: If project does not exist.
        """
        result = await self._session.execute(
            select(ProjectModel).where(ProjectModel.id == UUID(project_id))
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project", project_id)

        for key, value in updates.items():
            if value is not None and hasattr(project, key):
                setattr(project, key, value)

        await self._session.flush()
        logger.info("project_updated", project_id=project_id)
        return self._to_dict(project)

    @staticmethod
    def _to_dict(model: ProjectModel) -> dict[str, Any]:
        return {
            "id": str(model.id),
            "name": model.name,
            "description": model.description,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "updated_at": model.updated_at.isoformat() if model.updated_at else None,
        }

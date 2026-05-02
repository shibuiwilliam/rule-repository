"""MarketplaceService — package publishing, subscriptions, and composition conflict resolution.

Orchestrates the rule marketplace lifecycle: creating and publishing packages,
subscribing projects to packages, importing rules, and resolving composition
conflicts between overlapping packages.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from rulerepo_server.adapters.postgres.models import (
    CompositionConflictModel,
    PackageRuleModel,
    PackageSubscriptionModel,
    RuleModel,
    RulePackageModel,
)
from rulerepo_server.core.errors import ConflictError, NotFoundError, ValidationError
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class MarketplaceService:
    """Manages rule package marketplace operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Package CRUD
    # ------------------------------------------------------------------

    async def create_package(
        self,
        name: str,
        version: str,
        publisher_id: str = "system",
        description: str = "",
        license: str = "MIT",
        homepage: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new rule package."""
        # Check for duplicate name+version+publisher
        existing = await self._session.execute(
            select(RulePackageModel).where(
                RulePackageModel.name == name,
                RulePackageModel.version == version,
                RulePackageModel.publisher_id == publisher_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(f"Package '{name}' version '{version}' already exists for publisher '{publisher_id}'.")

        package = RulePackageModel(
            id=uuid4(),
            name=name,
            version=version,
            publisher_id=publisher_id,
            description=description,
            license=license,
            homepage=homepage,
            metadata_=metadata or {},
        )
        self._session.add(package)
        await self._session.flush()

        logger.info("package_created", package_id=str(package.id), name=name, version=version)
        return _package_to_dict(package)

    async def get_package(self, package_id: str) -> dict[str, Any]:
        """Load a package with its rules."""
        package = await self._load_package(package_id)
        result = _package_to_dict(package)
        result["rules"] = [
            {
                "id": str(pr.id),
                "rule_id": str(pr.rule_id),
                "package_rule_id": pr.package_rule_id,
                "test_cases": pr.test_cases or [],
            }
            for pr in package.rules
        ]
        return result

    async def list_packages(
        self,
        published_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List packages with optional filtering and pagination."""
        query = select(RulePackageModel)
        count_query = select(func.count(RulePackageModel.id))

        if published_only:
            query = query.where(RulePackageModel.published == True)  # noqa: E712
            count_query = count_query.where(RulePackageModel.published == True)  # noqa: E712

        total = (await self._session.execute(count_query)).scalar() or 0

        query = query.order_by(RulePackageModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        packages = result.scalars().all()

        return {
            "items": [_package_to_dict(p) for p in packages],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ------------------------------------------------------------------
    # Package Rules
    # ------------------------------------------------------------------

    async def add_rule_to_package(
        self,
        package_id: str,
        rule_id: str,
        package_rule_id: str,
    ) -> dict[str, Any]:
        """Add a rule to a package."""
        await self._load_package(package_id)

        # Verify rule exists
        rule_result = await self._session.execute(select(RuleModel.id).where(RuleModel.id == rule_id))
        if rule_result.scalar_one_or_none() is None:
            raise NotFoundError("Rule", rule_id)

        # Check for duplicate
        existing = await self._session.execute(
            select(PackageRuleModel).where(
                PackageRuleModel.package_id == package_id,
                PackageRuleModel.rule_id == rule_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(f"Rule '{rule_id}' is already in package '{package_id}'.")

        pr = PackageRuleModel(
            id=uuid4(),
            package_id=package_id,
            rule_id=rule_id,
            package_rule_id=package_rule_id,
        )
        self._session.add(pr)
        await self._session.flush()

        logger.info("rule_added_to_package", package_id=package_id, rule_id=rule_id)
        return {
            "id": str(pr.id),
            "package_id": str(pr.package_id),
            "rule_id": str(pr.rule_id),
            "package_rule_id": pr.package_rule_id,
            "test_cases": pr.test_cases or [],
        }

    async def remove_rule_from_package(
        self,
        package_id: str,
        rule_id: str,
    ) -> dict[str, Any]:
        """Remove a rule from a package."""
        result = await self._session.execute(
            select(PackageRuleModel).where(
                PackageRuleModel.package_id == package_id,
                PackageRuleModel.rule_id == rule_id,
            )
        )
        pr = result.scalar_one_or_none()
        if pr is None:
            raise NotFoundError("PackageRule", f"{package_id}/{rule_id}")

        await self._session.execute(delete(PackageRuleModel).where(PackageRuleModel.id == pr.id))
        await self._session.flush()

        logger.info("rule_removed_from_package", package_id=package_id, rule_id=rule_id)
        return {"removed": True, "package_id": package_id, "rule_id": rule_id}

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    async def publish_package(self, package_id: str) -> dict[str, Any]:
        """Publish a package, making it visible to subscribers."""
        package = await self._load_package(package_id)

        if package.published:
            raise ConflictError(f"Package '{package_id}' is already published.")

        package.published = True
        package.published_at = datetime.now(tz=UTC)
        await self._session.flush()

        logger.info("package_published", package_id=package_id)
        return _package_to_dict(package)

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        project_id: str,
        package_id: str,
        version_constraint: str = "*",
        auto_update: bool = False,
    ) -> dict[str, Any]:
        """Subscribe a project to a package and import its rules."""
        package = await self._load_package(package_id)

        # Check for existing subscription
        existing = await self._session.execute(
            select(PackageSubscriptionModel).where(
                PackageSubscriptionModel.project_id == project_id,
                PackageSubscriptionModel.package_id == package_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(f"Project '{project_id}' is already subscribed to package '{package_id}'.")

        subscription = PackageSubscriptionModel(
            id=uuid4(),
            project_id=project_id,
            package_id=package_id,
            version_constraint=version_constraint,
            auto_update=auto_update,
            installed_version=package.version,
        )
        self._session.add(subscription)

        # Import rules from the package into the project with marketplace tags
        imported_count = 0
        for pr in package.rules:
            rule_result = await self._session.execute(select(RuleModel).where(RuleModel.id == pr.rule_id))
            source_rule = rule_result.scalar_one_or_none()
            if source_rule is None:
                continue

            imported_rule = RuleModel(
                id=uuid4(),
                project_id=project_id,
                statement=source_rule.statement,
                modality=source_rule.modality,
                severity=source_rule.severity,
                scope=source_rule.scope,
                tags=["imported", "marketplace"],
                status=source_rule.status,
                maturity_level=source_rule.maturity_level,
            )
            self._session.add(imported_rule)
            imported_count += 1

        # Increment adoption count
        package.adoption_count = (package.adoption_count or 0) + 1

        await self._session.flush()

        logger.info(
            "project_subscribed",
            project_id=project_id,
            package_id=package_id,
            rules_imported=imported_count,
        )
        result = _subscription_to_dict(subscription)
        result["rules_imported"] = imported_count
        return result

    async def list_subscriptions(
        self,
        project_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List subscriptions for a project."""
        query = select(PackageSubscriptionModel).where(PackageSubscriptionModel.project_id == project_id)
        count_query = select(func.count(PackageSubscriptionModel.id)).where(
            PackageSubscriptionModel.project_id == project_id
        )

        total = (await self._session.execute(count_query)).scalar() or 0

        query = query.order_by(PackageSubscriptionModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        subscriptions = result.scalars().all()

        return {
            "items": [_subscription_to_dict(s) for s in subscriptions],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def unsubscribe(self, subscription_id: str) -> dict[str, Any]:
        """Remove a subscription."""
        result = await self._session.execute(
            select(PackageSubscriptionModel).where(PackageSubscriptionModel.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if subscription is None:
            raise NotFoundError("Subscription", subscription_id)

        await self._session.execute(
            delete(PackageSubscriptionModel).where(PackageSubscriptionModel.id == subscription.id)
        )
        await self._session.flush()

        logger.info("project_unsubscribed", subscription_id=subscription_id)
        return {"removed": True, "subscription_id": subscription_id}

    # ------------------------------------------------------------------
    # Composition Conflicts
    # ------------------------------------------------------------------

    async def list_conflicts(
        self,
        project_id: str,
        resolution: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List composition conflicts for a project."""
        query = select(CompositionConflictModel).where(CompositionConflictModel.project_id == project_id)
        count_query = select(func.count(CompositionConflictModel.id)).where(
            CompositionConflictModel.project_id == project_id
        )

        if resolution is not None:
            query = query.where(CompositionConflictModel.resolution == resolution)
            count_query = count_query.where(CompositionConflictModel.resolution == resolution)

        total = (await self._session.execute(count_query)).scalar() or 0

        query = query.order_by(CompositionConflictModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        conflicts = result.scalars().all()

        return {
            "items": [_conflict_to_dict(c) for c in conflicts],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        resolved_by: str = "system",
    ) -> dict[str, Any]:
        """Resolve a composition conflict."""
        valid_resolutions = {"keep_a", "keep_b", "keep_both", "dismiss"}
        if resolution not in valid_resolutions:
            raise ValidationError(
                f"Invalid resolution '{resolution}'. Must be one of: {', '.join(sorted(valid_resolutions))}."
            )

        result = await self._session.execute(
            select(CompositionConflictModel).where(CompositionConflictModel.id == conflict_id)
        )
        conflict = result.scalar_one_or_none()
        if conflict is None:
            raise NotFoundError("CompositionConflict", conflict_id)

        if conflict.resolution != "pending":
            raise ConflictError(f"Conflict '{conflict_id}' is already resolved as '{conflict.resolution}'.")

        conflict.resolution = resolution
        conflict.resolved_by = resolved_by
        conflict.resolved_at = datetime.now(tz=UTC)
        await self._session.flush()

        logger.info(
            "conflict_resolved",
            conflict_id=conflict_id,
            resolution=resolution,
            resolved_by=resolved_by,
        )
        return _conflict_to_dict(conflict)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _load_package(self, package_id: str) -> RulePackageModel:
        """Load a package by ID with its rules, raising NotFoundError if missing."""
        result = await self._session.execute(
            select(RulePackageModel)
            .options(selectinload(RulePackageModel.rules))
            .where(RulePackageModel.id == package_id)
        )
        package = result.scalar_one_or_none()
        if package is None:
            raise NotFoundError("RulePackage", package_id)
        return package


# ---------------------------------------------------------------------------
# Serialization Helpers
# ---------------------------------------------------------------------------


def _package_to_dict(package: RulePackageModel) -> dict[str, Any]:
    """Convert a RulePackageModel to a plain dict."""
    return {
        "id": str(package.id),
        "name": package.name,
        "version": package.version,
        "publisher_id": package.publisher_id,
        "description": package.description,
        "license": package.license,
        "homepage": package.homepage,
        "changelog": package.changelog or [],
        "metadata": package.metadata_ or {},
        "quality_score": package.quality_score,
        "adoption_count": package.adoption_count,
        "published": package.published,
        "published_at": package.published_at.isoformat() if package.published_at else None,
        "created_at": package.created_at.isoformat() if package.created_at else "",
    }


def _subscription_to_dict(subscription: PackageSubscriptionModel) -> dict[str, Any]:
    """Convert a PackageSubscriptionModel to a plain dict."""
    return {
        "id": str(subscription.id),
        "project_id": str(subscription.project_id),
        "package_id": str(subscription.package_id),
        "version_constraint": subscription.version_constraint,
        "auto_update": subscription.auto_update,
        "composition_policy": subscription.composition_policy or {},
        "installed_version": subscription.installed_version,
        "last_synced_at": subscription.last_synced_at.isoformat() if subscription.last_synced_at else "",
        "created_at": subscription.created_at.isoformat() if subscription.created_at else "",
    }


def _conflict_to_dict(conflict: CompositionConflictModel) -> dict[str, Any]:
    """Convert a CompositionConflictModel to a plain dict."""
    return {
        "id": str(conflict.id),
        "project_id": str(conflict.project_id),
        "rule_a_id": str(conflict.rule_a_id),
        "rule_b_id": str(conflict.rule_b_id),
        "package_a_id": str(conflict.package_a_id),
        "package_b_id": str(conflict.package_b_id),
        "conflict_type": conflict.conflict_type,
        "similarity_score": conflict.similarity_score,
        "resolution": conflict.resolution,
        "resolved_by": conflict.resolved_by,
        "resolved_at": conflict.resolved_at.isoformat() if conflict.resolved_at else None,
        "created_at": conflict.created_at.isoformat() if conflict.created_at else "",
    }

"""Pydantic request/response schemas for the Rule Marketplace API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class PackageCreate(BaseModel):
    """Request body for creating a new rule package."""

    name: str = Field(..., min_length=1, max_length=255, description="Package name.")
    version: str = Field(..., min_length=1, max_length=50, description="Semantic version string.")
    description: str = Field(default="", description="Package description.")
    license: str = Field(default="MIT", description="License identifier (e.g. MIT, Apache-2.0).")
    homepage: str | None = Field(default=None, description="URL to the package homepage.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata.")


class PackageRuleAdd(BaseModel):
    """Request body for adding a rule to a package."""

    rule_id: str = Field(..., description="ID of the rule to add.")
    package_rule_id: str = Field(..., description="Package-local identifier for the rule.")


class SubscribeRequest(BaseModel):
    """Request body for subscribing a project to a package."""

    project_id: str = Field(..., description="Project subscribing to the package.")
    package_id: str = Field(..., description="Package to subscribe to.")
    version_constraint: str = Field(default="*", description="Semver constraint (e.g. ^1.0.0).")
    auto_update: bool = Field(default=False, description="Automatically install new versions.")


class ConflictResolveRequest(BaseModel):
    """Request body for resolving a cross-package conflict."""

    resolution: str = Field(..., min_length=1, description="Resolution strategy or description.")
    resolved_by: str = Field(default="system", description="User or system resolving the conflict.")


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class PackageRuleResponse(BaseModel):
    """Response for a single rule within a package."""

    id: str
    package_id: str
    rule_id: str
    package_rule_id: str
    test_cases: list[dict[str, Any]] = Field(default_factory=list)


class PackageResponse(BaseModel):
    """Full package representation returned by the API."""

    id: str
    name: str
    version: str
    publisher_id: str
    description: str
    license: str
    homepage: str | None = None
    changelog: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    quality_score: float = 0.0
    adoption_count: int = 0
    published: bool = False
    published_at: str | None = None
    rule_count: int = 0
    created_at: str


class PackageListResponse(BaseModel):
    """Paginated list of packages."""

    items: list[PackageResponse]
    total: int
    page: int
    page_size: int


class SubscriptionResponse(BaseModel):
    """Response for a package subscription."""

    id: str
    project_id: str
    package_id: str
    package_name: str
    version_constraint: str
    auto_update: bool
    installed_version: str
    last_synced_at: str
    created_at: str


class ConflictResponse(BaseModel):
    """Response for a cross-package rule conflict."""

    id: str
    project_id: str
    rule_a_id: str
    rule_b_id: str
    package_a_id: str
    package_b_id: str
    conflict_type: str
    similarity_score: float
    resolution: str
    resolved_by: str | None = None
    created_at: str

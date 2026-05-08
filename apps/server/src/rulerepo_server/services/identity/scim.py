"""SCIM 2.0 provisioning service.

Implements the server-side SCIM 2.0 protocol for user and group
provisioning.  Identity providers (Okta, Azure AD, Google Workspace)
push user lifecycle events here so the Rule Repository stays in sync
with the corporate directory.

Reference: RFC 7643 (SCIM Core Schema), RFC 7644 (SCIM Protocol).
"""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

from rulerepo_server.core.errors import ConflictError, NotFoundError, ValidationError
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.tenant import Group, Principal, PrincipalKind

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# SCIM Pydantic schemas
# ---------------------------------------------------------------------------


class SCIMName(BaseModel):
    """SCIM user name components."""

    given_name: str = Field(default="", alias="givenName")
    family_name: str = Field(default="", alias="familyName")
    formatted: str = ""

    model_config = {"populate_by_name": True}


class SCIMEmail(BaseModel):
    """A single SCIM email entry."""

    value: str
    type: str = "work"
    primary: bool = False


class SCIMGroupMember(BaseModel):
    """A member reference within a SCIM group."""

    value: str  # user ID
    display: str = ""


class SCIMUser(BaseModel):
    """SCIM 2.0 User resource representation.

    Follows RFC 7643 core schema with the fields most commonly used
    by enterprise IdPs.
    """

    schemas: list[str] = Field(default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:User"])
    id: str = ""
    user_name: str = Field(default="", alias="userName")
    name: SCIMName = Field(default_factory=SCIMName)
    emails: list[SCIMEmail] = Field(default_factory=list)
    active: bool = True
    display_name: str = Field(default="", alias="displayName")
    groups: list[dict[str, str]] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    department: str = ""
    title: str = ""

    model_config = {"populate_by_name": True}


class SCIMGroup(BaseModel):
    """SCIM 2.0 Group resource representation."""

    schemas: list[str] = Field(default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:Group"])
    id: str = ""
    display_name: str = Field(default="", alias="displayName")
    members: list[SCIMGroupMember] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class SCIMListResponse(BaseModel):
    """SCIM 2.0 list response envelope."""

    schemas: list[str] = Field(default_factory=lambda: ["urn:ietf:params:scim:api:messages:2.0:ListResponse"])
    total_results: int = Field(default=0, alias="totalResults")
    start_index: int = Field(default=1, alias="startIndex")
    items_per_page: int = Field(default=100, alias="itemsPerPage")
    resources: list[SCIMUser | SCIMGroup] = Field(default_factory=list, alias="Resources")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SCIMService:
    """SCIM 2.0 provisioning endpoints for users and groups.

    Phase 7a uses an in-memory store.  The persistence adapter will be
    wired when the Postgres models for principals/groups ship.

    Args:
        user_store: Optional mapping of (tenant_id, user_id) -> Principal.
        group_store: Optional mapping of (tenant_id, group_id) -> Group.
    """

    def __init__(
        self,
        user_store: dict[tuple[str, str], Principal] | None = None,
        group_store: dict[tuple[str, str], Group] | None = None,
    ) -> None:
        self._users: dict[tuple[str, str], Principal] = user_store if user_store is not None else {}
        self._groups: dict[tuple[str, str], Group] = group_store if group_store is not None else {}

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def list_users(
        self,
        tenant_id: str,
        filter_expr: str | None = None,
        start_index: int = 1,
        count: int = 100,
    ) -> SCIMListResponse:
        """List users for a tenant, with optional filtering.

        Args:
            tenant_id: The tenant to scope the query to.
            filter_expr: Optional SCIM filter expression (simplified).
            start_index: 1-based start index for pagination.
            count: Maximum number of results to return.

        Returns:
            A SCIMListResponse with matching users.
        """
        all_users = [self._principal_to_scim(p) for (tid, _), p in self._users.items() if tid == tenant_id]

        # Simplified filter: support "userName eq \"value\""
        if filter_expr:
            all_users = self._apply_filter(all_users, filter_expr)

        total = len(all_users)
        start_idx = max(start_index - 1, 0)
        page = all_users[start_idx : start_idx + count]

        return SCIMListResponse(
            total_results=total,
            start_index=start_index,
            items_per_page=count,
            resources=page,
        )

    async def get_user(self, tenant_id: str, user_id: str) -> SCIMUser:
        """Get a SCIM user by ID.

        Raises:
            NotFoundError: If the user does not exist.
        """
        principal = self._users.get((tenant_id, user_id))
        if principal is None:
            raise NotFoundError("SCIMUser", user_id)
        return self._principal_to_scim(principal)

    async def create_user(self, tenant_id: str, scim_user: SCIMUser) -> SCIMUser:
        """Provision a new user from a SCIM request.

        Args:
            tenant_id: The tenant to create the user in.
            scim_user: The SCIM user representation.

        Returns:
            The created SCIMUser with a generated ID.

        Raises:
            ConflictError: If a user with the same userName already exists.
            ValidationError: If required fields are missing.
        """
        if not scim_user.user_name:
            raise ValidationError("userName is required")

        # Check for duplicates by userName
        for (tid, _), p in self._users.items():
            if tid == tenant_id and p.email == scim_user.user_name:
                raise ConflictError(f"User with userName '{scim_user.user_name}' already exists")

        user_id = str(uuid4())
        primary_email = next((e.value for e in scim_user.emails if e.primary), None)
        if not primary_email and scim_user.emails:
            primary_email = scim_user.emails[0].value

        display_name = scim_user.display_name or scim_user.name.formatted or scim_user.user_name

        principal = Principal(
            id=user_id,
            tenant_id=tenant_id,
            kind=PrincipalKind.USER,
            display_name=display_name,
            email=primary_email or scim_user.user_name,
            roles=scim_user.roles,
            clearance="internal",
        )
        self._users[(tenant_id, user_id)] = principal
        logger.info("scim_user_created", user_id=user_id, tenant_id=tenant_id)

        result = self._principal_to_scim(principal)
        result.active = scim_user.active
        return result

    async def update_user(self, tenant_id: str, user_id: str, scim_user: SCIMUser) -> SCIMUser:
        """Replace a user's attributes from a SCIM PUT/PATCH request.

        Args:
            tenant_id: The tenant the user belongs to.
            user_id: The user to update.
            scim_user: The updated SCIM user representation.

        Returns:
            The updated SCIMUser.

        Raises:
            NotFoundError: If the user does not exist.
        """
        existing = self._users.get((tenant_id, user_id))
        if existing is None:
            raise NotFoundError("SCIMUser", user_id)

        primary_email = next((e.value for e in scim_user.emails if e.primary), None)
        if not primary_email and scim_user.emails:
            primary_email = scim_user.emails[0].value

        display_name = scim_user.display_name or scim_user.name.formatted or existing.display_name

        updated = Principal(
            id=user_id,
            tenant_id=tenant_id,
            kind=PrincipalKind.USER,
            display_name=display_name,
            email=primary_email or existing.email,
            department_ids=existing.department_ids,
            clearance=existing.clearance,
            roles=scim_user.roles if scim_user.roles else existing.roles,
            groups=existing.groups,
            organization_id=existing.organization_id,
        )
        self._users[(tenant_id, user_id)] = updated
        logger.info("scim_user_updated", user_id=user_id, tenant_id=tenant_id)
        return self._principal_to_scim(updated)

    async def delete_user(self, tenant_id: str, user_id: str) -> None:
        """Deactivate a user (SCIM DELETE = soft-delete).

        The user is removed from the active store.  In production the
        record is marked inactive rather than deleted.

        Raises:
            NotFoundError: If the user does not exist.
        """
        key = (tenant_id, user_id)
        if key not in self._users:
            raise NotFoundError("SCIMUser", user_id)
        del self._users[key]
        logger.info("scim_user_deleted", user_id=user_id, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Groups
    # ------------------------------------------------------------------

    async def list_groups(self, tenant_id: str) -> SCIMListResponse:
        """List all groups for a tenant.

        Returns:
            A SCIMListResponse with all groups.
        """
        all_groups = [self._group_to_scim(g) for (tid, _), g in self._groups.items() if tid == tenant_id]
        return SCIMListResponse(
            total_results=len(all_groups),
            start_index=1,
            items_per_page=len(all_groups),
            resources=all_groups,
        )

    async def create_group(self, tenant_id: str, scim_group: SCIMGroup) -> SCIMGroup:
        """Provision a new group from a SCIM request.

        Args:
            tenant_id: The tenant to create the group in.
            scim_group: The SCIM group representation.

        Returns:
            The created SCIMGroup with a generated ID.

        Raises:
            ValidationError: If displayName is missing.
        """
        if not scim_group.display_name:
            raise ValidationError("displayName is required for groups")

        group_id = str(uuid4())
        member_ids = [m.value for m in scim_group.members]

        group = Group(
            id=group_id,
            tenant_id=tenant_id,
            name=scim_group.display_name,
            member_ids=member_ids,
        )
        self._groups[(tenant_id, group_id)] = group
        logger.info("scim_group_created", group_id=group_id, tenant_id=tenant_id)
        return self._group_to_scim(group)

    async def get_group(self, tenant_id: str, group_id: str) -> SCIMGroup:
        """Get a SCIM group by ID.

        Raises:
            NotFoundError: If the group does not exist.
        """
        group = self._groups.get((tenant_id, group_id))
        if group is None:
            raise NotFoundError("SCIMGroup", group_id)
        return self._group_to_scim(group)

    async def update_group(self, tenant_id: str, group_id: str, scim_group: SCIMGroup) -> SCIMGroup:
        """Replace a group's attributes.

        Raises:
            NotFoundError: If the group does not exist.
        """
        existing = self._groups.get((tenant_id, group_id))
        if existing is None:
            raise NotFoundError("SCIMGroup", group_id)

        member_ids = [m.value for m in scim_group.members]
        updated = Group(
            id=group_id,
            tenant_id=tenant_id,
            name=scim_group.display_name or existing.name,
            member_ids=member_ids,
        )
        self._groups[(tenant_id, group_id)] = updated
        logger.info("scim_group_updated", group_id=group_id, tenant_id=tenant_id)
        return self._group_to_scim(updated)

    async def delete_group(self, tenant_id: str, group_id: str) -> None:
        """Delete a group.

        Raises:
            NotFoundError: If the group does not exist.
        """
        key = (tenant_id, group_id)
        if key not in self._groups:
            raise NotFoundError("SCIMGroup", group_id)
        del self._groups[key]
        logger.info("scim_group_deleted", group_id=group_id, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _principal_to_scim(principal: Principal) -> SCIMUser:
        """Convert a domain Principal to a SCIM User representation."""
        emails = []
        if principal.email:
            emails.append(SCIMEmail(value=principal.email, type="work", primary=True))

        return SCIMUser(
            id=principal.id,
            userName=principal.email or principal.id,
            name=SCIMName(formatted=principal.display_name),
            emails=emails,
            active=True,
            displayName=principal.display_name,
            roles=list(principal.roles),
        )

    @staticmethod
    def _group_to_scim(group: Group) -> SCIMGroup:
        """Convert a domain Group to a SCIM Group representation."""
        members = [SCIMGroupMember(value=mid) for mid in group.member_ids]
        return SCIMGroup(
            id=group.id,
            displayName=group.name,
            members=members,
        )

    @staticmethod
    def _apply_filter(users: list[SCIMUser], filter_expr: str) -> list[SCIMUser]:
        """Apply a simplified SCIM filter expression.

        Supports: ``userName eq "value"`` and ``active eq "true"/"false"``.
        Full SCIM filter grammar is deferred.
        """
        parts = filter_expr.strip().split(" ", 2)
        if len(parts) != 3:
            return users

        attr, op, raw_value = parts
        if op.lower() != "eq":
            return users

        value = raw_value.strip('"').strip("'")

        filtered: list[SCIMUser] = []
        for user in users:
            if (
                (attr == "userName" and user.user_name == value)
                or (attr == "active" and str(user.active).lower() == value.lower())
                or (attr == "displayName" and user.display_name == value)
            ):
                filtered.append(user)
        return filtered

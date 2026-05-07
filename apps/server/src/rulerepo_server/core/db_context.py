"""Database session context helpers for classification-based RLS.

Sets PostgreSQL session variables that RLS policies read to enforce
classification-based access control. Must be called before any query
against classified tables (rules, evaluations, audit_log).

See CLAUDE.md section 14.2 and ADR 0003.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.domain.classification import Classification


@dataclass(frozen=True)
class AuthenticatedUser:
    """Represents an authenticated user for RLS context.

    Attributes:
        id: Unique user identifier.
        clearance: Maximum classification level the user may access.
        department_ids: List of department IDs the user belongs to.
    """

    id: str
    clearance: Classification
    department_ids: list[str] = field(default_factory=list)


async def with_user_context(session: AsyncSession, user: AuthenticatedUser) -> None:
    """Set RLS session variables for classification-based access control.

    Must be called within an active transaction before issuing queries
    against classified tables. Uses parameterized queries to prevent
    SQL injection.

    Args:
        session: The active async database session.
        user: The authenticated user whose context to set.
    """
    departments_csv = ",".join(user.department_ids)

    await session.execute(
        text("SET LOCAL app.user_id = :user_id"),
        {"user_id": user.id},
    )
    await session.execute(
        text("SET LOCAL app.user_departments = :departments"),
        {"departments": departments_csv},
    )
    await session.execute(
        text("SET LOCAL app.user_clearance = :clearance"),
        {"clearance": user.clearance.value},
    )

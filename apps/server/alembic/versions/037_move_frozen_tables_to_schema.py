"""Move frozen-feature tables to the ``frozen`` schema.

Per the v1 mission plan (§4 Sprint 1) and PROJECT.md §10.4, Phase 6 features
that are disabled by default under the Cross-Organizational direction have
their tables moved to a separate ``frozen`` schema.  This keeps them out of
the default public schema namespace while preserving all data and FKs.

Tables moved:
- ``governance_sessions`` — multi-agent governance sessions
  (MULTI_AGENT_SESSIONS_ENABLED=false)
- ``agent_negotiations`` — multi-agent negotiation records
  (MULTI_AGENT_SESSIONS_ENABLED=false)
- ``enforcement_policies`` — gateway policy engine
  (GATEWAY_ENABLED=false)
- ``gateway_evaluations`` — gateway evaluation records
  (GATEWAY_ENABLED=false, FK to enforcement_policies)

Tables NOT moved (still active):
- ``agent_profiles`` — single-agent profiles remain active
- ``agent_exception_requests`` — exception workflow remains active

Revision ID: 037
Revises: 036
"""

from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ``frozen`` schema and move frozen-feature tables into it."""
    # 1. Create the frozen schema
    op.execute("CREATE SCHEMA IF NOT EXISTS frozen")

    # 2. Move gateway tables (enforcement_policies first, then gateway_evaluations
    #    which has a FK to it)
    op.execute("ALTER TABLE public.enforcement_policies SET SCHEMA frozen")
    op.execute("ALTER TABLE public.gateway_evaluations SET SCHEMA frozen")

    # 3. Move multi-agent session tables
    op.execute("ALTER TABLE public.governance_sessions SET SCHEMA frozen")
    op.execute("ALTER TABLE public.agent_negotiations SET SCHEMA frozen")


def downgrade() -> None:
    """Move frozen tables back to public schema."""
    op.execute("ALTER TABLE frozen.agent_negotiations SET SCHEMA public")
    op.execute("ALTER TABLE frozen.governance_sessions SET SCHEMA public")
    op.execute("ALTER TABLE frozen.gateway_evaluations SET SCHEMA public")
    op.execute("ALTER TABLE frozen.enforcement_policies SET SCHEMA public")
    op.execute("DROP SCHEMA IF EXISTS frozen")

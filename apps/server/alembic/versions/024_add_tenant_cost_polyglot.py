"""Add tenant model, cost ledger columns, evaluations_daily_agg, and equivalence_id.

Tier 3: Multi-tenancy foundation (TenantModel + tenant_id FK on rules),
        cost tracking columns on evaluations,
        daily aggregation table for intelligence dashboard.
Tier 4: equivalence_id on rules for polyglot rule support.

Backfill: existing rules/evaluations get default tenant_id. Existing evaluations
have NULL cost columns (only new evaluations populate them).

Revision ID: 024
Revises: 023
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    """Add tenant, cost, aggregation, and polyglot infrastructure."""
    # 1. Tenant table
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("settings", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Insert default tenant
    op.execute(f"INSERT INTO tenants (id, name) VALUES ('{DEFAULT_TENANT_ID}', 'default') ON CONFLICT DO NOTHING")

    # 2. tenant_id on rules
    op.add_column(
        "rules",
        sa.Column("tenant_id", sa.Uuid(), nullable=False, server_default=DEFAULT_TENANT_ID),
    )
    op.create_index("ix_rules_tenant_id", "rules", ["tenant_id"])

    # 3. Cost ledger columns on evaluations
    op.add_column("evaluations", sa.Column("input_tokens", sa.Integer(), nullable=True))
    op.add_column("evaluations", sa.Column("output_tokens", sa.Integer(), nullable=True))
    op.add_column(
        "evaluations",
        sa.Column("estimated_cost_usd", sa.Numeric(precision=10, scale=6), nullable=True),
    )

    # 4. equivalence_id on rules (polyglot)
    op.add_column(
        "rules",
        sa.Column("equivalence_id", sa.String(100), nullable=True),
    )
    op.create_index("ix_rules_equivalence_id", "rules", ["equivalence_id"])

    # 5. Evaluations daily aggregation table
    op.create_table(
        "evaluations_daily_agg",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("allow_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deny_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("needs_confirmation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("p95_latency_ms", sa.Float(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.UniqueConstraint("rule_id", "tenant_id", "date", name="uq_eval_daily_agg"),
    )


def downgrade() -> None:
    """Remove tenant, cost, aggregation, and polyglot infrastructure."""
    op.drop_table("evaluations_daily_agg")
    op.drop_index("ix_rules_equivalence_id", table_name="rules")
    op.drop_column("rules", "equivalence_id")
    op.drop_column("evaluations", "estimated_cost_usd")
    op.drop_column("evaluations", "output_tokens")
    op.drop_column("evaluations", "input_tokens")
    op.drop_index("ix_rules_tenant_id", table_name="rules")
    op.drop_column("rules", "tenant_id")
    op.drop_table("tenants")

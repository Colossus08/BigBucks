"""Add custom_net_fortnightly_cents to income_profile

Revision ID: 0007_income_custom_net
Revises: 0006_budget_multi_per_category
Create Date: 2026-11-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_income_custom_net"
down_revision = "0006_budget_multi_per_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("income_profile")}
    if "custom_net_fortnightly_cents" not in cols:
        op.add_column(
            "income_profile",
            sa.Column("custom_net_fortnightly_cents", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("income_profile")}
    if "custom_net_fortnightly_cents" in cols:
        op.drop_column("income_profile", "custom_net_fortnightly_cents")

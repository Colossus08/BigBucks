"""Add optional custom name column to budget table

Revision ID: 0005_budget_name
Revises: 0004_roadmap_refinements
Create Date: 2026-11-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_budget_name"
down_revision = "0004_roadmap_refinements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("budget")}
    if "name" not in cols:
        op.add_column(
            "budget",
            sa.Column("name", sa.String(length=120), nullable=False, server_default=""),
        )


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("budget")}
    if "name" in cols:
        op.drop_column("budget", "name")

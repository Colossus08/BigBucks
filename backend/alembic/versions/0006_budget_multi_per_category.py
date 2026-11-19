"""Allow multiple budgets per category (drop uq_budget_period constraint)

Revision ID: 0006_budget_multi_per_category
Revises: 0005_budget_name
Create Date: 2026-11-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_budget_multi_per_category"
down_revision = "0005_budget_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    uniques = {u["name"] for u in insp.get_unique_constraints("budget")}
    if "uq_budget_period" in uniques:
        op.execute("ALTER TABLE budget RENAME TO _budget_old")
        op.create_table(
            "budget",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("category.id"), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("period", sa.String(length=20), nullable=False),
            sa.Column("effective_month", sa.String(length=7), nullable=False, server_default=""),
            sa.Column("limit_cents", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
        )
        op.execute(
            "INSERT INTO budget (id, category_id, name, period, effective_month, limit_cents, is_active) "
            "SELECT id, category_id, COALESCE(name, ''), period, COALESCE(effective_month, ''), limit_cents, is_active FROM _budget_old"
        )
        op.execute("DROP TABLE _budget_old")


def downgrade() -> None:
    pass

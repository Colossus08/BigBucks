"""Phase 3-6 tables: budgets, goals, investments, super, recurring payments

Revision ID: 0002_phase3_to_6
Revises: 0001_initial
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_phase3_to_6"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _missing(name: str) -> bool:
    return not sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if _missing("budget"):
        op.create_table(
            "budget",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("category.id"), nullable=False, unique=True),
            sa.Column("period", sa.String(length=20), nullable=False),
            sa.Column("limit_cents", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
        )
    if _missing("financial_goal"):
        op.create_table(
            "financial_goal",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("category", sa.String(length=40), nullable=False),
            sa.Column("target_cents", sa.Integer(), nullable=False),
            sa.Column("extra_costs_cents", sa.Integer(), nullable=False),
            sa.Column("current_cents", sa.Integer(), nullable=False),
            sa.Column("target_date", sa.Date(), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("planned_contribution_cents", sa.Integer(), nullable=False),
            sa.Column("contribution_frequency", sa.String(length=20), nullable=False),
        )
    if _missing("goal_contribution"):
        op.create_table(
            "goal_contribution",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("goal_id", sa.Integer(), sa.ForeignKey("financial_goal.id"), nullable=False),
            sa.Column("amount_cents", sa.Integer(), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("note", sa.String(length=200), nullable=False),
        )
    if _missing("investment_holding"):
        op.create_table(
            "investment_holding",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("symbol", sa.String(length=20), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("asset_type", sa.String(length=30), nullable=False),
            sa.Column("units_milli", sa.Integer(), nullable=False),
            sa.Column("avg_cost_cents", sa.Integer(), nullable=False),
            sa.Column("current_price_cents", sa.Integer(), nullable=False),
        )
    if _missing("super_account"):
        op.create_table(
            "super_account",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("fund_name", sa.String(length=120), nullable=False),
            sa.Column("balance_cents", sa.Integer(), nullable=False),
            sa.Column("personal_monthly_cents", sa.Integer(), nullable=False),
            sa.Column("expected_return_bps", sa.Integer(), nullable=False),
        )
    if _missing("recurring_payment"):
        op.create_table(
            "recurring_payment",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("merchant", sa.String(length=200), nullable=False),
            sa.Column("category_name", sa.String(length=80), nullable=False),
            sa.Column("amount_cents", sa.Integer(), nullable=False),
            sa.Column("cadence", sa.String(length=20), nullable=False),
        )


def downgrade() -> None:
    for table in (
        "recurring_payment",
        "super_account",
        "investment_holding",
        "goal_contribution",
        "financial_goal",
        "budget",
    ):
        op.drop_table(table)

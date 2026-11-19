"""Roadmap refinements: transfer pairing, tax/WFH ledger, recurring price-creep fields, multi-period budget constraint

Revision ID: 0004_roadmap_refinements
Revises: 0003_goal_linked_account
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_roadmap_refinements"
down_revision = "0003_goal_linked_account"
branch_labels = None
depends_on = None


def _col_names(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    # 1. Transaction additions: paired_transaction_id, is_tax_deductible, deduction_category, receipt_ref
    tx_cols = _col_names("transaction")
    if "paired_transaction_id" not in tx_cols:
        op.add_column("transaction", sa.Column("paired_transaction_id", sa.Integer(), nullable=True))
    if "is_tax_deductible" not in tx_cols:
        op.add_column(
            "transaction",
            sa.Column("is_tax_deductible", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )
    if "deduction_category" not in tx_cols:
        op.add_column("transaction", sa.Column("deduction_category", sa.String(length=20), nullable=True))
    if "receipt_ref" not in tx_cols:
        op.add_column("transaction", sa.Column("receipt_ref", sa.String(length=120), nullable=True))

    # 2. RecurringPayment additions: merchant_pattern, category_id, last_charged_cents, expected_day_of_month, next_due_date
    rec_cols = _col_names("recurring_payment")
    if "merchant_pattern" not in rec_cols:
        op.add_column(
            "recurring_payment",
            sa.Column("merchant_pattern", sa.String(length=200), nullable=False, server_default=""),
        )
    if "category_id" not in rec_cols:
        op.add_column("recurring_payment", sa.Column("category_id", sa.Integer(), nullable=True))
    if "last_charged_cents" not in rec_cols:
        op.add_column("recurring_payment", sa.Column("last_charged_cents", sa.Integer(), nullable=True))
    if "expected_day_of_month" not in rec_cols:
        op.add_column("recurring_payment", sa.Column("expected_day_of_month", sa.Integer(), nullable=True))
    if "next_due_date" not in rec_cols:
        op.add_column("recurring_payment", sa.Column("next_due_date", sa.Date(), nullable=True))

    # 3. Budget multi-period support: effective_month + compound unique constraint
    b_cols = _col_names("budget")
    if "effective_month" not in b_cols:
        op.execute("ALTER TABLE budget RENAME TO _budget_old")
        op.create_table(
            "budget",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("category.id"), nullable=False),
            sa.Column("period", sa.String(length=20), nullable=False),
            sa.Column("effective_month", sa.String(length=7), nullable=False, server_default=""),
            sa.Column("limit_cents", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.UniqueConstraint("category_id", "period", "effective_month", name="uq_budget_period"),
        )
        op.execute(
            "INSERT INTO budget (id, category_id, period, effective_month, limit_cents, is_active) "
            "SELECT id, category_id, period, '', limit_cents, is_active FROM _budget_old"
        )
        op.execute("DROP TABLE _budget_old")

    # 4. WfhLog table (§4.4)
    if not insp.has_table("wfh_log"):
        op.create_table(
            "wfh_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("work_date", sa.Date(), nullable=False),
            sa.Column("hours", sa.Float(), nullable=False, server_default=sa.text("0.0")),
            sa.Column("note", sa.String(length=200), nullable=False, server_default=""),
        )
        op.create_index("ix_wfh_log_work_date", "wfh_log", ["work_date"])


def downgrade() -> None:
    op.drop_index("ix_wfh_log_work_date", table_name="wfh_log")
    op.drop_table("wfh_log")

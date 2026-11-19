"""Initial schema for Phases 1-2

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Databases created before Alembic was wired in already have these tables.
    if sa.inspect(op.get_bind()).has_table("institution"):
        return

    op.create_table(
        "institution",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False, unique=True),
    )
    op.create_table(
        "account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), sa.ForeignKey("institution.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("account_number_mask", sa.String(length=20), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("is_own", sa.Boolean(), nullable=False),
        sa.Column("current_balance_cents", sa.Integer(), nullable=False),
    )
    op.create_table(
        "category",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("group", sa.String(length=40), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("category.id"), nullable=True),
        sa.Column("is_income", sa.Boolean(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("name", "group", name="uq_category_name_group"),
    )
    op.create_table(
        "merchant_rule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pattern", sa.String(length=200), nullable=False),
        sa.Column("match_type", sa.String(length=20), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("category.id"), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "import_batch",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("inserted_rows", sa.Integer(), nullable=False),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False),
        sa.Column("error_rows", sa.Integer(), nullable=False),
    )
    op.create_table(
        "transaction",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), sa.ForeignKey("import_batch.id"), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("description_raw", sa.String(length=500), nullable=False),
        sa.Column("merchant", sa.String(length=200), nullable=False),
        sa.Column("balance_cents", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("category.id"), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("is_transfer", sa.Boolean(), nullable=False),
        sa.Column("dedupe_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("category_source", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_transaction_account_id", "transaction", ["account_id"])
    op.create_index("ix_transaction_date", "transaction", ["date"])
    op.create_index("ix_transaction_merchant", "transaction", ["merchant"])
    op.create_index("ix_transaction_category_id", "transaction", ["category_id"])
    op.create_table(
        "income_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employer_name", sa.String(length=120), nullable=False),
        sa.Column("gross_annual_cents", sa.Integer(), nullable=False),
        sa.Column("pay_frequency", sa.String(length=20), nullable=False),
        sa.Column("super_rate_bps", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("income_profile")
    op.drop_index("ix_transaction_category_id", table_name="transaction")
    op.drop_index("ix_transaction_merchant", table_name="transaction")
    op.drop_index("ix_transaction_date", table_name="transaction")
    op.drop_index("ix_transaction_account_id", table_name="transaction")
    op.drop_table("transaction")
    op.drop_table("import_batch")
    op.drop_table("merchant_rule")
    op.drop_table("category")
    op.drop_table("account")
    op.drop_table("institution")

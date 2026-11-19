"""Link a goal to a tracked savings account

Revision ID: 0003_goal_linked_account
Revises: 0002_phase3_to_6
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_goal_linked_account"
down_revision = "0002_phase3_to_6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("financial_goal")}
    if "linked_account_id" not in columns:
        # Plain nullable integer: SQLite cannot add a foreign key constraint with ALTER TABLE.
        op.add_column("financial_goal", sa.Column("linked_account_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("financial_goal") as batch:
        batch.drop_column("linked_account_id")

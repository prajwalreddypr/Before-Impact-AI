"""Track preparation action owners.

Revision ID: 20261024_0003
Revises: 20261024_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_0003"
down_revision = "20261024_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("plan_items", sa.Column("assignee_name", sa.String(120), nullable=False, server_default="Unassigned"))


def downgrade():
    op.drop_column("plan_items", "assignee_name")

"""construction projects

Revision ID: 20261024_0004
Revises: 20261024_0003
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_0004"
down_revision = "20261024_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "construction_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("building_type", sa.String(80), nullable=False, server_default="School"),
        sa.Column("region", sa.String(120), nullable=False, server_default="Japan"),
        sa.Column("entry_mode", sa.String(30), nullable=False, server_default="find"),
        sa.Column("active_section", sa.String(40), nullable=False, server_default="projects"),
        sa.Column("selected_site_ids_json", sa.JSON(), nullable=False),
        sa.Column("project_data_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_construction_projects_owner_user_id", "construction_projects", ["owner_user_id"])


def downgrade():
    op.drop_index("ix_construction_projects_owner_user_id", table_name="construction_projects")
    op.drop_table("construction_projects")

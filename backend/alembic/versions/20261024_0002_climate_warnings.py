"""Add portfolio climate warnings.

Revision ID: 20261024_0002
Revises: 20261024_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "20261024_0002"
down_revision = "20261024_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "warnings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("facility_id", sa.Integer(), sa.ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weather_event_id", sa.Integer(), sa.ForeignKey("weather_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hazard_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(120), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_warnings_facility_id", "warnings", ["facility_id"])
    op.create_index("ix_warnings_weather_event_id", "warnings", ["weather_event_id"])
    op.create_index("ix_warnings_hazard_type", "warnings", ["hazard_type"])


def downgrade():
    op.drop_table("warnings")

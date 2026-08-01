"""Add focused one-panel regeneration run metadata."""

from alembic import op
import sqlalchemy as sa


revision = "0008_panel_regeneration"
down_revision = "0007_provider_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generation_runs",
        sa.Column("run_kind", sa.String(24), nullable=False, server_default="story"),
    )
    op.add_column("generation_runs", sa.Column("base_revision", sa.Integer()))
    op.add_column("generation_runs", sa.Column("panel_number", sa.Integer()))
    op.add_column("generation_runs", sa.Column("correction", sa.Text()))


def downgrade() -> None:
    for column in ("correction", "panel_number", "base_revision", "run_kind"):
        op.drop_column("generation_runs", column)

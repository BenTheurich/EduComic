"""Persist resumable story checkpoints and review candidates."""

from alembic import op
import sqlalchemy as sa


revision = "0010_generation_checkpoints"
down_revision = "0009_avatar_thumbnails"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generation_runs",
        sa.Column("checkpoint_panels", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column("generation_runs", sa.Column("provider_job", sa.JSON()))
    op.add_column(
        "generation_runs",
        sa.Column("reported_bfl_cost", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column("generation_runs", sa.Column("candidate_object_path", sa.String(500)))


def downgrade() -> None:
    for column in (
        "candidate_object_path",
        "reported_bfl_cost",
        "provider_job",
        "checkpoint_panels",
    ):
        op.drop_column("generation_runs", column)

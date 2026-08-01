"""Add durable local generation-run state."""

from alembic import op
import sqlalchemy as sa


revision = "0002_generation_durability"
down_revision = "0001_local_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("generation_runs", sa.Column("selected_idea_id", sa.String(80)))
    op.add_column("generation_runs", sa.Column("stage", sa.String(32)))
    op.add_column("generation_runs", sa.Column("error_code", sa.String(40)))
    op.add_column(
        "generation_runs",
        sa.Column("artifact_paths", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_index(
        "uq_generation_runs_active_chapter",
        "generation_runs",
        ["chapter_id"],
        unique=True,
        sqlite_where=sa.text("job_state IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_generation_runs_active_chapter", table_name="generation_runs")
    for column in ("artifact_paths", "error_code", "stage", "selected_idea_id"):
        op.drop_column("generation_runs", column)

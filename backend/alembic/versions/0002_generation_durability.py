"""Add durable local generation-run state."""

from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0002_generation_durability"
down_revision = "0001_local_foundation"
branch_labels = None
depends_on = None


def _reconcile_interrupted_runs() -> None:
    connection = op.get_bind()
    interrupted = connection.execute(
        sa.text(
            "SELECT id, chapter_id FROM generation_runs "
            "WHERE job_state IN ('queued', 'running')"
        )
    ).mappings().all()
    if not interrupted:
        return

    finished_at = datetime.now(timezone.utc)
    for run in interrupted:
        connection.execute(
            sa.text(
                "UPDATE generation_runs SET job_state = 'failed', stage = 'failed', "
                "error_code = 'interrupted', error_reference = :reference, "
                "finished_at = :finished_at WHERE id = :run_id"
            ).bindparams(
                sa.bindparam("finished_at", type_=sa.DateTime(timezone=True))
            ),
            {
                "reference": uuid4().hex,
                "finished_at": finished_at,
                "run_id": run["id"],
            },
        )

    for chapter_id in {run["chapter_id"] for run in interrupted}:
        readable_revision = connection.execute(
            sa.text(
                "SELECT chapters.revision FROM chapters "
                "WHERE chapters.id = :chapter_id AND chapters.revision > 0 "
                "AND EXISTS (SELECT 1 FROM panels WHERE panels.chapter_id = chapters.id "
                "AND panels.revision = chapters.revision)"
            ),
            {"chapter_id": chapter_id},
        ).scalar_one_or_none()
        connection.execute(
            sa.text("UPDATE chapters SET status = :status WHERE id = :chapter_id"),
            {
                "status": "ready" if readable_revision is not None else "failed",
                "chapter_id": chapter_id,
            },
        )


def upgrade() -> None:
    op.add_column("generation_runs", sa.Column("selected_idea_id", sa.String(80)))
    op.add_column("generation_runs", sa.Column("stage", sa.String(32)))
    op.add_column("generation_runs", sa.Column("error_code", sa.String(40)))
    op.add_column(
        "generation_runs",
        sa.Column("artifact_paths", sa.JSON(), nullable=False, server_default="[]"),
    )
    _reconcile_interrupted_runs()
    op.create_index(
        "uq_generation_runs_active_chapter",
        "generation_runs",
        ["chapter_id"],
        unique=True,
        sqlite_where=sa.text("job_state IN ('queued', 'running')"),
        postgresql_where=sa.text("job_state IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_generation_runs_active_chapter", table_name="generation_runs")
    for column in ("artifact_paths", "error_code", "stage", "selected_idea_id"):
        op.drop_column("generation_runs", column)

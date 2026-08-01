"""Add local mutation settings, provenance, and deletion recovery."""

from alembic import op
import sqlalchemy as sa
from uuid import uuid4


revision = "0003_local_mutations"
down_revision = "0002_generation_durability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generation_runs",
        sa.Column("settings_snapshot", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column("generation_runs", sa.Column("script_snapshot", sa.JSON()))
    op.create_table(
        "deletion_manifests",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("operation", sa.String(600), nullable=False),
        sa.Column("target_kind", sa.String(20), nullable=False),
        sa.Column("target_id", sa.String(80)),
        sa.Column("object_paths", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_reference", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('pending', 'failed')", name="ck_deletion_manifests_status"),
        sa.UniqueConstraint("operation", name="uq_deletion_manifests_operation"),
    )
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE settings SET default_design_style = COALESCE(default_design_style, 'comic'), "
            "openai_model = COALESCE(openai_model, 'gpt-5.1'), "
            "bfl_endpoint = COALESCE(bfl_endpoint, 'flux-2-pro'), "
            "generation_defaults = json_set(COALESCE(generation_defaults, '{}'), '$.story_length', "
            "COALESCE(json_extract(generation_defaults, '$.story_length'), 12))"
        )
    )
    legacy_chapters = connection.execute(
        sa.text(
            "SELECT c.id, c.chosen_idea_id, c.revision, c.story_script, c.created_at, c.updated_at "
            "FROM chapters c WHERE c.revision > 0 AND NOT EXISTS (SELECT 1 FROM generation_runs r "
            "WHERE r.chapter_id = c.id AND r.target_revision = c.revision)"
        )
    ).mappings().all()
    for chapter in legacy_chapters:
        connection.execute(
            sa.text(
                "INSERT INTO generation_runs (id, idempotency_key, chapter_id, selected_idea_id, target_revision, "
                "job_state, stage, artifact_paths, settings_snapshot, script_snapshot, finished_at, created_at, updated_at) "
                "VALUES (:id, :key, :chapter_id, :idea, :revision, 'succeeded', 'ready', '[]', "
                "json_object('story_length', COALESCE((SELECT json_extract(s.generation_defaults, '$.story_length') "
                "FROM settings s LIMIT 1), 12), 'student_ids', COALESCE((SELECT json_group_array(sc.student_id) "
                "FROM student_classrooms sc JOIN chapters c ON c.classroom_id = sc.classroom_id "
                "WHERE c.id = :chapter_id), json('[]'))), :script, :updated, :created, :updated)"
            ),
            {
                "id": str(uuid4()),
                "key": f"legacy-revision-{chapter['id']}-{chapter['revision']}",
                "chapter_id": chapter["id"],
                "idea": chapter["chosen_idea_id"],
                "revision": chapter["revision"],
                "script": chapter["story_script"],
                "created": chapter["created_at"],
                "updated": chapter["updated_at"],
            },
        )
    connection.execute(
        sa.text(
            "UPDATE generation_runs SET settings_snapshot = json_object("
            "'story_length', COALESCE((SELECT json_extract(s.generation_defaults, '$.story_length') "
            "FROM settings s LIMIT 1), 12), "
            "'student_ids', COALESCE((SELECT json_group_array(sc.student_id) FROM student_classrooms sc "
            "JOIN chapters c ON c.classroom_id = sc.classroom_id WHERE c.id = generation_runs.chapter_id), json('[]')))"
        )
    )


def downgrade() -> None:
    op.drop_table("deletion_manifests")
    op.drop_column("generation_runs", "script_snapshot")
    op.drop_column("generation_runs", "settings_snapshot")

"""Close Phase 4 provenance, cleanup, and provider-boundary gaps."""

from alembic import op
import sqlalchemy as sa


revision = "0004_review_fixes"
down_revision = "0003_local_mutations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chapters",
        sa.Column("option_student_ids", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "chapters",
        sa.Column("option_provenance_complete", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "chapters",
        sa.Column("option_settings_snapshot", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "students",
        sa.Column("superseded_avatar_paths", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_table(
        "active_work",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("work_kind", sa.String(24), nullable=False),
        sa.Column("target_kind", sa.String(20), nullable=False),
        sa.Column("target_id", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("work_kind", "target_kind", "target_id", name="uq_active_work_target"),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE settings SET generation_defaults = json_set(COALESCE(generation_defaults, '{}'), "
            "'$.story_length', CASE WHEN json_extract(generation_defaults, '$.story_length') IN (12, 20) "
            "THEN json_extract(generation_defaults, '$.story_length') ELSE 12 END), "
            "openai_model = CASE WHEN openai_model = 'gpt-5.1' THEN openai_model ELSE 'gpt-5.1' END, "
            "bfl_endpoint = CASE WHEN bfl_endpoint = 'flux-2-pro' THEN bfl_endpoint ELSE 'flux-2-pro' END"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE generation_runs SET settings_snapshot = json_set(settings_snapshot, "
            "'$.story_length', CASE WHEN json_extract(settings_snapshot, '$.story_length') IN (12, 20) "
            "THEN json_extract(settings_snapshot, '$.story_length') ELSE 12 END, "
            "'$.openai_model', 'gpt-5.1', '$.bfl_model', 'flux-2-pro', "
            "'$.provenance_complete', json('true')) "
            "WHERE json_type(settings_snapshot, '$.openai_model') IS NOT NULL"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE generation_runs SET settings_snapshot = json_object("
            "'story_length', CASE WHEN job_state = 'succeeded' THEN COALESCE(("
            "SELECT json_array_length(c.story_script, '$.panels') FROM chapters c "
            "WHERE c.id = generation_runs.chapter_id "
            "AND c.revision = generation_runs.target_revision "
            "AND json_type(c.story_script, '$.panels') = 'array' "
            "AND json_array_length(c.story_script, '$.panels') IN (12, 20) "
            "AND (SELECT COUNT(*) FROM json_each(c.story_script, '$.panels') p "
            "WHERE CAST(json_extract(p.value, '$.index') AS INTEGER) = CAST(p.key AS INTEGER) + 1) "
            "= json_array_length(c.story_script, '$.panels')), 12) ELSE 12 END, "
            "'default_design_style', 'comic', "
            "'openai_model', 'gpt-5.1', 'bfl_model', 'flux-2-pro', "
            "'automatic_panel_review', json('false'), 'panel_review_attempt_cap', 3, "
            "'student_ids', json('[]'), 'provenance_complete', json('false')) "
            "WHERE json_type(settings_snapshot, '$.openai_model') IS NULL"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE generation_runs SET script_snapshot = ("
            "SELECT c.story_script FROM chapters c WHERE c.id = generation_runs.chapter_id "
            "AND c.revision = generation_runs.target_revision "
            "AND json_type(c.story_script, '$.panels') = 'array' "
            "AND json_array_length(c.story_script, '$.panels') IN (12, 20) "
            "AND (SELECT COUNT(*) FROM json_each(c.story_script, '$.panels') p "
            "WHERE CAST(json_extract(p.value, '$.index') AS INTEGER) = CAST(p.key AS INTEGER) + 1) "
            "= json_array_length(c.story_script, '$.panels')) "
            "WHERE job_state = 'succeeded' "
            "AND json_extract(settings_snapshot, '$.provenance_complete') = 0"
        )
    )


def downgrade() -> None:
    op.drop_table("active_work")
    op.drop_column("students", "superseded_avatar_paths")
    op.drop_column("chapters", "option_settings_snapshot")
    op.drop_column("chapters", "option_provenance_complete")
    op.drop_column("chapters", "option_student_ids")

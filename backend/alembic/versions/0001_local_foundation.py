"""Create the local private application data contract."""

from alembic import op
import sqlalchemy as sa


revision = "0001_local_foundation"
down_revision = None
branch_labels = None
depends_on = None

uuid = sa.Uuid(as_uuid=False)


def timestamps():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def upgrade() -> None:
    op.create_table(
        "local_profiles",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="teacher"),
        sa.Column("display_settings", sa.JSON(), nullable=False, server_default="{}"),
        *timestamps(),
        sa.CheckConstraint("role = 'teacher'", name="ck_local_profiles_teacher_role"),
        sa.UniqueConstraint("role", name="uq_local_profiles_role"),
    )
    op.create_table(
        "classrooms",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("owner_id", uuid, sa.ForeignKey("local_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("subject", sa.String(120), nullable=False),
        sa.Column("grade_level", sa.String(60), nullable=False),
        sa.Column("story_theme", sa.String(160), nullable=False),
        sa.Column("design_style", sa.String(20), nullable=False),
        sa.Column("duration", sa.String(80)),
        *timestamps(),
        sa.CheckConstraint("design_style IN ('manga', 'comic', 'cartoon')", name="ck_classrooms_design_style"),
    )
    op.create_index("ix_classrooms_owner_created", "classrooms", ["owner_id", "created_at"])
    op.create_table(
        "students",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("interests", sa.Text(), nullable=False),
        sa.Column("avatar_object_path", sa.String(500)),
        sa.Column("photo_object_path", sa.String(500)),
        *timestamps(),
    )
    op.create_table(
        "student_classrooms",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("student_id", uuid, sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("classroom_id", uuid, sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("student_id", "classroom_id", name="uq_student_classroom"),
    )
    op.create_index("ix_student_classrooms_classroom", "student_classrooms", ["classroom_id"])
    op.create_table(
        "materials",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("classroom_id", uuid, sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_filename", sa.String(255), nullable=False),
        sa.Column("object_path", sa.String(500)),
        sa.Column("extraction_state", sa.String(20), nullable=False, server_default="uploaded"),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("extracted_pages", sa.JSON()),
        sa.Column("error_reference", sa.String(64)),
        *timestamps(),
        sa.CheckConstraint("extraction_state IN ('uploaded', 'processing', 'ready', 'failed', 'deleted')", name="ck_materials_extraction_state"),
        sa.UniqueConstraint("object_path", name="uq_materials_object_path"),
    )
    op.create_index("ix_materials_classroom_created", "materials", ["classroom_id", "created_at"])
    op.create_table(
        "chapters",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("classroom_id", uuid, sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("original_prompt", sa.Text(), nullable=False),
        sa.Column("story_ideas", sa.JSON()),
        sa.Column("chosen_idea_id", sa.String(80)),
        sa.Column("title", sa.String(255)),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("story_script", sa.JSON()),
        *timestamps(),
        sa.CheckConstraint("status IN ('draft', 'options_generated', 'idea_chosen', 'queued', 'generating', 'ready', 'failed', 'regenerating')", name="ck_chapters_status"),
        sa.CheckConstraint("revision >= 0", name="ck_chapters_revision"),
        sa.CheckConstraint('"index" > 0', name="ck_chapters_index"),
        sa.UniqueConstraint("classroom_id", "index", name="uq_chapters_classroom_index"),
    )
    op.create_index("ix_chapters_classroom_created", "chapters", ["classroom_id", "created_at"])
    op.create_table(
        "chapter_materials",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("chapter_id", uuid, sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", uuid, sa.ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("chapter_id", "material_id", name="uq_chapter_material"),
    )
    op.create_table(
        "panels",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("chapter_id", uuid, sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("panel_number", sa.Integer(), nullable=False),
        sa.Column("dialogue", sa.Text(), nullable=False),
        sa.Column("scene_description", sa.Text(), nullable=False),
        sa.Column("speakers", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("image_object_path", sa.String(500), nullable=False),
        *timestamps(),
        sa.CheckConstraint("revision >= 0", name="ck_panels_revision"),
        sa.CheckConstraint("panel_number > 0", name="ck_panels_number_positive"),
        sa.UniqueConstraint("chapter_id", "revision", "panel_number", name="uq_panels_chapter_revision_number"),
        sa.UniqueConstraint("image_object_path", name="uq_panels_image_object_path"),
    )
    op.create_index("ix_panels_chapter_revision", "panels", ["chapter_id", "revision"])
    op.create_table(
        "generation_runs",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("chapter_id", uuid, sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_revision", sa.Integer(), nullable=False),
        sa.Column("job_state", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("error_reference", sa.String(64)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.CheckConstraint("target_revision > 0", name="ck_generation_runs_target_revision"),
        sa.CheckConstraint("job_state IN ('queued', 'running', 'succeeded', 'failed')", name="ck_generation_runs_job_state"),
        sa.UniqueConstraint("idempotency_key", name="uq_generation_runs_idempotency_key"),
    )
    op.create_index("ix_generation_runs_chapter_state", "generation_runs", ["chapter_id", "job_state"])
    op.create_table(
        "settings",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("profile_id", uuid, sa.ForeignKey("local_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("default_design_style", sa.String(20)),
        sa.Column("openai_model", sa.String(120)),
        sa.Column("bfl_endpoint", sa.String(255)),
        sa.Column("automatic_panel_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("panel_review_attempt_cap", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("retain_original_photos", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("generation_defaults", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("reader_preferences", sa.JSON(), nullable=False, server_default="{}"),
        *timestamps(),
        sa.UniqueConstraint("profile_id", name="uq_settings_profile_id"),
    )


def downgrade() -> None:
    for table in (
        "settings",
        "generation_runs",
        "panels",
        "chapter_materials",
        "chapters",
        "materials",
        "student_classrooms",
        "students",
        "classrooms",
        "local_profiles",
    ):
        op.drop_table(table)

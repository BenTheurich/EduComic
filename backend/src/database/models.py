"""SQLAlchemy data contract for the local private application."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


def _uuid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def __init__(self):
        super().__init__(timezone=True)

    def process_bind_param(self, value: datetime | None, _dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, _dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class LocalProfile(TimestampMixin, Base):
    __tablename__ = "local_profiles"
    __table_args__ = (CheckConstraint("role = 'teacher'", name="ck_local_profiles_teacher_role"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, default="teacher")
    display_settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    classrooms: Mapped[list["Classroom"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Classroom(TimestampMixin, Base):
    __tablename__ = "classrooms"
    __table_args__ = (
        CheckConstraint("design_style IN ('manga', 'comic', 'cartoon')", name="ck_classrooms_design_style"),
        Index("ix_classrooms_owner_created", "owner_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("local_profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False)
    grade_level: Mapped[str] = mapped_column(String(60), nullable=False)
    story_theme: Mapped[str] = mapped_column(String(160), nullable=False)
    design_style: Mapped[str] = mapped_column(String(20), nullable=False)
    duration: Mapped[str | None] = mapped_column(String(80))
    owner: Mapped[LocalProfile] = relationship(back_populates="classrooms")


class Student(TimestampMixin, Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    interests: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_object_path: Mapped[str | None] = mapped_column(String(500))
    photo_object_path: Mapped[str | None] = mapped_column(String(500))
    superseded_avatar_paths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class StudentClassroom(TimestampMixin, Base):
    __tablename__ = "student_classrooms"
    __table_args__ = (
        UniqueConstraint("student_id", "classroom_id", name="uq_student_classroom"),
        Index("ix_student_classrooms_classroom", "classroom_id"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    classroom_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)


class Material(TimestampMixin, Base):
    __tablename__ = "materials"
    __table_args__ = (
        CheckConstraint(
            "extraction_state IN ('uploaded', 'processing', 'ready', 'failed', 'deleted')",
            name="ck_materials_extraction_state",
        ),
        UniqueConstraint("object_path", name="uq_materials_object_path"),
        Index("ix_materials_classroom_created", "classroom_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    classroom_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    object_path: Mapped[str | None] = mapped_column(String(500))
    extraction_state: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    content_hash: Mapped[str | None] = mapped_column(String(64))
    extracted_pages: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    error_reference: Mapped[str | None] = mapped_column(String(64))


class Chapter(TimestampMixin, Base):
    __tablename__ = "chapters"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'options_generated', 'idea_chosen', 'queued', 'generating', 'ready', 'failed', 'regenerating')",
            name="ck_chapters_status",
        ),
        CheckConstraint("revision >= 0", name="ck_chapters_revision"),
        CheckConstraint('"index" > 0', name="ck_chapters_index"),
        UniqueConstraint("classroom_id", "index", name="uq_chapters_classroom_index"),
        Index("ix_chapters_classroom_created", "classroom_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    classroom_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    original_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    story_ideas: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    option_student_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    option_provenance_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    option_settings_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    chosen_idea_id: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    story_script: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class ChapterMaterial(TimestampMixin, Base):
    __tablename__ = "chapter_materials"
    __table_args__ = (UniqueConstraint("chapter_id", "material_id", name="uq_chapter_material"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    chapter_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    material_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_label: Mapped[str] = mapped_column(String(255), nullable=False)
    excerpts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    grounding_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Panel(TimestampMixin, Base):
    __tablename__ = "panels"
    __table_args__ = (
        CheckConstraint("revision >= 0", name="ck_panels_revision"),
        CheckConstraint("panel_number > 0", name="ck_panels_number_positive"),
        UniqueConstraint("chapter_id", "revision", "panel_number", name="uq_panels_chapter_revision_number"),
        UniqueConstraint("image_object_path", name="uq_panels_image_object_path"),
        Index("ix_panels_chapter_revision", "chapter_id", "revision"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    chapter_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    panel_number: Mapped[int] = mapped_column(Integer, nullable=False)
    dialogue: Mapped[str] = mapped_column(Text, nullable=False)
    scene_description: Mapped[str] = mapped_column(Text, nullable=False)
    speakers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    image_object_path: Mapped[str] = mapped_column(String(500), nullable=False)


class GenerationRun(TimestampMixin, Base):
    __tablename__ = "generation_runs"
    __table_args__ = (
        CheckConstraint("target_revision > 0", name="ck_generation_runs_target_revision"),
        CheckConstraint(
            "job_state IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_generation_runs_job_state",
        ),
        UniqueConstraint("idempotency_key", name="uq_generation_runs_idempotency_key"),
        Index("ix_generation_runs_chapter_state", "chapter_id", "job_state"),
        Index(
            "uq_generation_runs_active_chapter",
            "chapter_id",
            unique=True,
            sqlite_where=text("job_state IN ('queued', 'running')"),
            postgresql_where=text("job_state IN ('queued', 'running')"),
        ),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    chapter_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    run_kind: Mapped[str] = mapped_column(String(24), nullable=False, default="story")
    selected_idea_id: Mapped[str | None] = mapped_column(String(80))
    base_revision: Mapped[int | None] = mapped_column(Integer)
    panel_number: Mapped[int | None] = mapped_column(Integer)
    correction: Mapped[str | None] = mapped_column(Text)
    target_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    job_state: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    stage: Mapped[str | None] = mapped_column(String(32))
    error_code: Mapped[str | None] = mapped_column(String(40))
    error_reference: Mapped[str | None] = mapped_column(String(64))
    artifact_paths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    settings_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    script_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class Setting(TimestampMixin, Base):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("local_profiles.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    default_design_style: Mapped[str | None] = mapped_column(String(20))
    openai_model: Mapped[str | None] = mapped_column(String(120))
    bfl_endpoint: Mapped[str | None] = mapped_column(String(255))
    automatic_panel_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    panel_review_attempt_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    retain_original_photos: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    generation_defaults: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reader_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DeletionManifest(TimestampMixin, Base):
    __tablename__ = "deletion_manifests"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'failed')", name="ck_deletion_manifests_status"),
        UniqueConstraint("operation", name="uq_deletion_manifests_operation"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    operation: Mapped[str] = mapped_column(String(600), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(80))
    object_paths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_reference: Mapped[str | None] = mapped_column(String(64))


class ActiveWork(TimestampMixin, Base):
    __tablename__ = "active_work"
    __table_args__ = (
        UniqueConstraint("work_kind", "target_kind", "target_id", name="uq_active_work_target"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    work_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str] = mapped_column(String(80), nullable=False)

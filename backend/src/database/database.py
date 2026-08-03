"""Concrete SQLite persistence used by the local/private application."""

import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Iterator
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from database.models import (
    ActiveWork,
    Chapter,
    ChapterMaterial,
    Classroom,
    DeletionManifest,
    GenerationRun,
    LocalProfile,
    Material,
    Panel,
    Setting,
    Student,
    StudentClassroom,
)
from database.session import create_session_factory
from local_runtime import local_database_url, resolve_local_paths
from local_storage import LocalStorage, StorageValidationError, media_url
from materials import snapshot_sources
from provider_config import (
    DEFAULT_BFL_MODEL,
    DEFAULT_OPENAI_MODEL,
    SUPPORTED_BFL_MODELS,
    SUPPORTED_OPENAI_MODELS,
    require_supported_model,
)

LOCAL_TEACHER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_SETTINGS = {
    "story_length": 12,
    "default_design_style": "comic",
    "openai_model": DEFAULT_OPENAI_MODEL,
    "bfl_model": DEFAULT_BFL_MODEL,
    "automatic_panel_review": False,
    "panel_review_attempt_cap": 3,
    "reader_preferences": {},
}


class GenerationConflict(RuntimeError):
    pass


@lru_cache(maxsize=8)
def _factory(database_url: str) -> sessionmaker:
    return create_session_factory(database_url)


@contextmanager
def _session(database_url: str | None = None) -> Iterator[Session]:
    factory = _factory(database_url or local_database_url(resolve_local_paths()))
    with factory() as session, session.begin():
        yield session


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _classroom(classroom: Classroom) -> dict[str, Any]:
    return {
        "id": classroom.id,
        "name": classroom.name,
        "subject": classroom.subject,
        "grade_level": classroom.grade_level,
        "story_theme": classroom.story_theme,
        "design_style": classroom.design_style,
        "duration": classroom.duration,
        "created_at": _iso(classroom.created_at),
        "updated_at": _iso(classroom.updated_at),
    }


def _student(student: Student) -> dict[str, Any]:
    return {
        "id": student.id,
        "name": student.name,
        "interests": student.interests,
        "avatar_url": media_url(student.avatar_object_path) if student.avatar_object_path else None,
        "avatar_thumbnail_url": (
            media_url(student.avatar_thumbnail_object_path)
            if student.avatar_thumbnail_object_path
            else None
        ),
        "created_at": _iso(student.created_at),
        "updated_at": _iso(student.updated_at),
    }


def _material(material: Material) -> dict[str, Any]:
    pages = list(material.extracted_pages or [])
    return {
        "id": material.id,
        "classroom_id": material.classroom_id,
        "source_filename": material.source_filename,
        "extraction_state": material.extraction_state,
        "content_hash": material.content_hash,
        "page_count": len(pages),
        "text_char_count": sum(len(str(page.get("text", ""))) for page in pages),
        "created_at": _iso(material.created_at),
        "updated_at": _iso(material.updated_at),
    }


def create_material(
    classroom_id: str,
    source_filename: str,
    object_path: str,
    content_hash: str,
    extracted_pages: list[dict[str, Any]],
) -> dict[str, Any]:
    with _session() as session:
        if session.get(Classroom, classroom_id) is None:
            raise ValueError("Classroom not found")
        material = Material(
            classroom_id=classroom_id,
            source_filename=source_filename,
            object_path=object_path,
            extraction_state="ready",
            content_hash=content_hash,
            extracted_pages=extracted_pages,
        )
        session.add(material)
        session.flush()
        return _material(material)


def get_materials_by_classroom(classroom_id: str) -> list[dict[str, Any]]:
    with _session() as session:
        rows = session.scalars(
            select(Material)
            .where(Material.classroom_id == classroom_id)
            .order_by(Material.created_at, Material.id)
        ).all()
        return [_material(row) for row in rows]


def _chapter(chapter: Chapter, session: Session) -> dict[str, Any]:
    material_provenance = [
        {
            "material_id": row.material_id,
            "content_hash": row.content_hash,
            "source_label": row.source_label,
            "excerpts": list(row.excerpts or []),
            "grounding_applied": row.grounding_applied,
        }
        for row in session.scalars(
            select(ChapterMaterial)
            .where(ChapterMaterial.chapter_id == chapter.id)
            .order_by(ChapterMaterial.created_at, ChapterMaterial.id)
        ).all()
    ]
    grounded_sources = [
        {key: value for key, value in source.items() if key != "grounding_applied"}
        for source in material_provenance
        if source["grounding_applied"]
    ]
    data = {
        "id": chapter.id,
        "classroom_id": chapter.classroom_id,
        "index": chapter.index,
        "original_prompt": chapter.original_prompt,
        "story_ideas": [_story_idea(idea) for idea in chapter.story_ideas or []],
        "option_student_ids": list(chapter.option_student_ids or []),
        "option_provenance_complete": chapter.option_provenance_complete,
        "option_settings_snapshot": dict(chapter.option_settings_snapshot or {}),
        "chosen_idea_id": chapter.chosen_idea_id,
        "status": chapter.status,
        "revision": chapter.revision,
        "story_script": chapter.story_script,
        "grounded_sources": grounded_sources,
        "material_provenance": material_provenance,
        "created_at": _iso(chapter.created_at),
        "updated_at": _iso(chapter.updated_at),
    }
    _add_story_metadata(data)
    return data


def _story_idea(idea: dict[str, Any]) -> dict[str, Any]:
    preview_path = idea.get("preview_object_path")
    preview_url = (
        media_url(preview_path)
        if idea.get("preview_status") == "ready"
        and isinstance(preview_path, str)
        and preview_path.startswith("story-images/")
        else None
    )
    return {
        "id": idea.get("id"),
        "title": idea.get("title"),
        "summary": idea.get("summary"),
        "theme": idea.get("theme"),
        "preview_status": idea.get("preview_status", "failed"),
        "preview_url": preview_url,
        "preview_error_reference": idea.get("preview_error_reference"),
    }


def _panel(panel: Panel) -> dict[str, Any]:
    return {
        "id": panel.id,
        "chapter_id": panel.chapter_id,
        "index": panel.panel_number,
        "image": media_url(panel.image_object_path),
        "dialogue": panel.dialogue,
        "scene_description": panel.scene_description,
        "speakers": panel.speakers,
        "created_at": _iso(panel.created_at),
    }


def _generation_run(run: GenerationRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "chapter_id": run.chapter_id,
        "run_kind": run.run_kind,
        "selected_idea_id": run.selected_idea_id,
        "base_revision": run.base_revision,
        "panel_number": run.panel_number,
        "target_revision": run.target_revision,
        "job_state": run.job_state,
        "stage": run.stage,
        "error_code": run.error_code,
        "error_reference": run.error_reference,
        "artifact_paths": list(run.artifact_paths or []),
        "checkpoint_panels": list(run.checkpoint_panels or []),
        "provider_job": dict(run.provider_job or {}) if run.provider_job else None,
        "reported_bfl_cost": float(run.reported_bfl_cost or 0),
        "candidate_object_path": run.candidate_object_path,
        "settings_snapshot": dict(run.settings_snapshot or {}),
        "script_snapshot": dict(run.script_snapshot or {}) if run.script_snapshot else None,
        "started_at": _iso(run.started_at) if run.started_at else None,
        "finished_at": _iso(run.finished_at) if run.finished_at else None,
        "cleanup_pending": bool(run.artifact_paths),
    }


def _media_object_path(url: str) -> str:
    return LocalStorage(resolve_local_paths().root).object_path_from_url(url)


def ensure_local_teacher(database_url: str | None = None) -> dict[str, Any]:
    with _session(database_url) as session:
        profile = session.get(LocalProfile, LOCAL_TEACHER_ID)
        if profile is None:
            profile = LocalProfile(
                id=LOCAL_TEACHER_ID,
                display_name="Local Teacher",
                role="teacher",
                display_settings={},
            )
            session.add(profile)
            session.flush()
        setting = session.scalar(select(Setting).where(Setting.profile_id == profile.id))
        if setting is None:
            session.add(
                Setting(
                    profile_id=profile.id,
                    default_design_style="comic",
                    openai_model=DEFAULT_OPENAI_MODEL,
                    bfl_endpoint=DEFAULT_BFL_MODEL,
                    automatic_panel_review=False,
                    panel_review_attempt_cap=3,
                    generation_defaults={"story_length": 12},
                    reader_preferences={},
                )
            )
        return {"id": profile.id, "display_name": profile.display_name, "role": profile.role}


def create_classroom(
    name: str,
    subject: str,
    grade_level: str,
    story_theme: str,
    design_style: str,
    duration: str | None = None,
) -> dict[str, Any]:
    with _session() as session:
        classroom = Classroom(
            owner_id=LOCAL_TEACHER_ID,
            name=name,
            subject=subject,
            grade_level=grade_level,
            story_theme=story_theme,
            design_style=design_style,
            duration=duration,
        )
        session.add(classroom)
        session.flush()
        return _classroom(classroom)


def get_classroom(classroom_id: str) -> dict[str, Any] | None:
    with _session() as session:
        classroom = session.get(Classroom, classroom_id)
        return _classroom(classroom) if classroom else None


def get_all_classrooms() -> list[dict[str, Any]]:
    with _session() as session:
        rows = session.scalars(select(Classroom).order_by(Classroom.created_at.desc())).all()
        return [_classroom(row) for row in rows]


def update_classroom(classroom_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"name", "subject", "grade_level", "story_theme", "design_style"}
    if set(updates) != allowed:
        raise ValueError("Classroom update must include every editable field")
    with _session() as session:
        classroom = session.get(Classroom, classroom_id)
        if classroom is None:
            return None
        for key, value in updates.items():
            setattr(classroom, key, value)
        session.flush()
        return _classroom(classroom)


def get_settings() -> dict[str, Any]:
    with _session() as session:
        setting = session.scalar(select(Setting).where(Setting.profile_id == LOCAL_TEACHER_ID))
        if setting is None:
            raise RuntimeError("Local settings are unavailable")
        return {
            "story_length": int((setting.generation_defaults or {}).get("story_length", 12)),
            "default_design_style": setting.default_design_style or "comic",
            "openai_model": setting.openai_model or DEFAULT_OPENAI_MODEL,
            "bfl_model": setting.bfl_endpoint or DEFAULT_BFL_MODEL,
            "automatic_panel_review": setting.automatic_panel_review,
            "panel_review_attempt_cap": setting.panel_review_attempt_cap,
            "reader_preferences": dict(setting.reader_preferences or {}),
        }


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    with _session() as session:
        setting = session.scalar(select(Setting).where(Setting.profile_id == LOCAL_TEACHER_ID))
        if setting is None:
            raise RuntimeError("Local settings are unavailable")
        if "story_length" in updates:
            setting.generation_defaults = {**(setting.generation_defaults or {}), "story_length": updates["story_length"]}
        for source, target in (
            ("default_design_style", "default_design_style"),
            ("openai_model", "openai_model"),
            ("bfl_model", "bfl_endpoint"),
            ("automatic_panel_review", "automatic_panel_review"),
            ("panel_review_attempt_cap", "panel_review_attempt_cap"),
            ("reader_preferences", "reader_preferences"),
        ):
            if source in updates:
                setattr(setting, target, updates[source])
        session.flush()
    return get_settings()


def create_student(
    name: str,
    interests: str,
    *,
    classroom_id: str | None = None,
    student_id: str | None = None,
) -> dict[str, Any]:
    """Create a profile and optional enrollment in one retry-safe transaction."""
    student_id = student_id or str(uuid4())
    try:
        with _session() as session:
            existing = session.get(Student, student_id)
            if existing:
                return _matching_student_retry(session, existing, name, interests, classroom_id)

            if classroom_id and session.get(Classroom, classroom_id) is None:
                raise ValueError("Classroom not found")
            student = Student(id=student_id, name=name, interests=interests)
            session.add(student)
            if classroom_id:
                session.add(StudentClassroom(student_id=student_id, classroom_id=classroom_id))
            session.flush()
            return _student(student)
    except IntegrityError:
        # A concurrent request with the same client UUID may have committed first.
        # The failed transaction has rolled back before this new session reloads it.
        with _session() as session:
            winner = session.get(Student, student_id)
            if winner is None:
                raise
            return _matching_student_retry(session, winner, name, interests, classroom_id)


def _matching_student_retry(
    session: Session,
    student: Student,
    name: str,
    interests: str,
    classroom_id: str | None,
) -> dict[str, Any]:
    if student.name != name or student.interests != interests:
        raise ValueError("Student identifier already exists")
    enrollments = set(
        session.scalars(
            select(StudentClassroom.classroom_id).where(StudentClassroom.student_id == student.id)
        ).all()
    )
    expected = {classroom_id} if classroom_id else set()
    if enrollments != expected:
        raise ValueError("Student retry does not match the original enrollment")
    return _student(student)


def get_student(student_id: str) -> dict[str, Any] | None:
    with _session() as session:
        student = session.get(Student, student_id)
        return _student(student) if student else None


def get_all_students() -> list[dict[str, Any]]:
    with _session() as session:
        rows = session.scalars(select(Student).order_by(Student.created_at.desc())).all()
        return [_student(row) for row in rows]


def get_students_by_classroom(classroom_id: str) -> list[dict[str, Any]]:
    with _session() as session:
        rows = session.scalars(
            select(Student)
            .join(StudentClassroom, StudentClassroom.student_id == Student.id)
            .where(StudentClassroom.classroom_id == classroom_id)
            .order_by(Student.created_at)
        ).all()
        return [_student(row) for row in rows]


def get_students_by_ids(student_ids: list[str]) -> list[dict[str, Any]]:
    """Load an immutable participant snapshot in its original order."""
    with _session() as session:
        students = {student.id: student for student in session.scalars(select(Student).where(Student.id.in_(student_ids)))}
        if set(students) != set(student_ids):
            raise GenerationConflict("Generation participant is unavailable")
        return [_student(students[student_id]) for student_id in student_ids]


def update_student(student_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"name", "interests", "avatar_url"}
    if set(updates) - allowed:
        raise ValueError("Unsupported student update")
    with _session() as session:
        student = session.get(Student, student_id)
        if student is None:
            return None
        for key, value in updates.items():
            if key == "avatar_url":
                student.avatar_object_path = _media_object_path(value)
            else:
                setattr(student, key, value)
        session.flush()
        return _student(student)


def replace_student_avatar(
    student_id: str,
    avatar_url: str,
    avatar_thumbnail_url: str | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Swap the visible avatar while durably retaining superseded cleanup work."""
    new_path = _media_object_path(avatar_url)
    new_thumbnail_path = _media_object_path(avatar_thumbnail_url) if avatar_thumbnail_url else None
    with _session() as session:
        student = session.get(Student, student_id)
        if student is None:
            return None, []
        old_paths = list(
            dict.fromkeys(
                path
                for path in (student.avatar_object_path, student.avatar_thumbnail_object_path)
                if path and path not in {new_path, new_thumbnail_path}
            )
        )
        if old_paths:
            student.superseded_avatar_paths = list(
                dict.fromkeys([*(student.superseded_avatar_paths or []), *old_paths])
            )
        student.avatar_object_path = new_path
        student.avatar_thumbnail_object_path = new_thumbnail_path
        session.flush()
        return _student(student), old_paths


def finish_superseded_avatar_cleanup(student_id: str, object_path: str) -> None:
    with _session() as session:
        student = session.get(Student, student_id)
        if student:
            student.superseded_avatar_paths = [
                path for path in student.superseded_avatar_paths or [] if path != object_path
            ]


def get_chapter(chapter_id: str) -> dict[str, Any] | None:
    with _session() as session:
        chapter = session.get(Chapter, chapter_id)
        return _chapter(chapter, session) if chapter else None


def create_chapter(data: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "classroom_id",
        "index",
        "original_prompt",
        "story_ideas",
        "option_student_ids",
        "option_provenance_complete",
        "option_settings_snapshot",
        "chosen_idea_id",
        "title",
        "status",
    }
    if set(data) - allowed:
        raise ValueError("Unsupported chapter field")
    with _session() as session:
        chapter = Chapter(**data)
        session.add(chapter)
        session.flush()
        return _chapter(chapter, session)


def update_chapter(chapter_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {
        "story_ideas",
        "option_student_ids",
        "option_provenance_complete",
        "option_settings_snapshot",
        "chosen_idea_id",
        "title",
        "status",
        "revision",
        "story_script",
    }
    if set(updates) - allowed:
        raise ValueError("Unsupported chapter update")
    with _session() as session:
        chapter = session.get(Chapter, chapter_id)
        if chapter is None:
            return None
        for key, value in updates.items():
            setattr(chapter, key, value)
        session.flush()
        return _chapter(chapter, session)


def _deletion_started(session: Session, target_kind: str, target_id: str) -> bool:
    if session.scalar(select(DeletionManifest.id).where(DeletionManifest.target_kind == "reset")):
        return True
    if session.scalar(
        select(DeletionManifest.id).where(
            DeletionManifest.target_kind == target_kind,
            DeletionManifest.target_id == target_id,
        )
    ):
        return True
    if target_kind == "chapter":
        classroom_id = session.scalar(select(Chapter.classroom_id).where(Chapter.id == target_id))
        return bool(
            classroom_id
            and session.scalar(
                select(DeletionManifest.id).where(
                    DeletionManifest.target_kind == "classroom",
                    DeletionManifest.target_id == classroom_id,
                )
            )
        )
    return False


def begin_story_options(
    classroom_id: str,
    index: int,
    original_prompt: str,
    material_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Create an option shell and durable provider-work lease in one transaction."""
    with _session() as session:
        if session.get(Classroom, classroom_id) is None:
            raise ValueError("Classroom not found")
        if _deletion_started(session, "classroom", classroom_id):
            raise GenerationConflict("Classroom deletion is active")
        snapshot = _generation_snapshot(session, classroom_id)
        chapter = Chapter(
            classroom_id=classroom_id,
            index=index,
            original_prompt=original_prompt,
            story_ideas=[],
            option_student_ids=list(snapshot["student_ids"]),
            option_provenance_complete=True,
            option_settings_snapshot=snapshot,
            status="draft",
        )
        session.add(chapter)
        session.flush()
        selected_ids = list(dict.fromkeys(material_ids or []))
        if selected_ids:
            rows = list(
                session.scalars(
                    select(Material).where(
                        Material.id.in_(selected_ids),
                        Material.classroom_id == classroom_id,
                        Material.extraction_state == "ready",
                    )
                ).all()
            )
            by_id = {row.id: row for row in rows}
            if len(by_id) != len(selected_ids):
                raise ValueError("Selected materials must be ready and belong to this classroom")
            snapshots = snapshot_sources(
                [
                    {
                        "id": by_id[material_id].id,
                        "source_filename": by_id[material_id].source_filename,
                        "content_hash": by_id[material_id].content_hash,
                        "extracted_pages": by_id[material_id].extracted_pages,
                    }
                    for material_id in selected_ids
                ]
            )
            session.add_all(
                [
                    ChapterMaterial(
                        chapter_id=chapter.id,
                        material_id=source["material_id"],
                        content_hash=source["content_hash"],
                        source_label=source["source_label"],
                        excerpts=source["excerpts"],
                        grounding_applied=True,
                    )
                    for source in snapshots
                ]
            )
        session.add(ActiveWork(work_kind="story_options", target_kind="chapter", target_id=chapter.id))
        session.flush()
        return _chapter(chapter, session)


def complete_story_options(chapter_id: str, story_ideas: list[dict[str, Any]]) -> dict[str, Any]:
    with _session() as session:
        work = session.scalar(
            select(ActiveWork).where(
                ActiveWork.work_kind == "story_options",
                ActiveWork.target_kind == "chapter",
                ActiveWork.target_id == chapter_id,
            )
        )
        chapter = session.get(Chapter, chapter_id)
        if work is None or chapter is None:
            raise GenerationConflict("Story option work is not active")
        chapter.story_ideas = story_ideas
        chapter.status = "options_generated"
        session.delete(work)
        session.flush()
        return _chapter(chapter, session)


def begin_story_previews(
    chapter_id: str, idea_ids: list[str] | None = None
) -> list[dict[str, Any]]:
    """Claim pending or failed idea previews and snapshot server-owned provider inputs."""
    with _session() as session:
        chapter = session.get(Chapter, chapter_id)
        if chapter is None:
            raise ValueError("Chapter not found")
        if chapter.status not in ("options_generated", "idea_chosen", "failed", "ready"):
            raise GenerationConflict("Story previews cannot start in the current chapter state")
        if _deletion_started(session, "chapter", chapter_id):
            raise GenerationConflict("Related deletion is active")
        classroom = session.get(Classroom, chapter.classroom_id)
        if classroom is None:
            raise ValueError("Classroom not found")

        ideas = [dict(idea) for idea in chapter.story_ideas or []]
        known_ids = {idea.get("id") for idea in ideas}
        requested = set(idea_ids) if idea_ids is not None else known_ids
        if not requested or not requested.issubset(known_ids):
            raise ValueError("Story preview choice is invalid")

        model = require_supported_model(
            (chapter.option_settings_snapshot or {}).get("bfl_model", DEFAULT_BFL_MODEL),
            SUPPORTED_BFL_MODELS,
            "BFL",
        )
        jobs = []
        for idea in ideas:
            idea_id = idea.get("id")
            if idea_id not in requested or idea.get("preview_status", "failed") not in ("pending", "failed"):
                continue
            target_id = f"{chapter_id}:{idea_id}"
            if session.scalar(
                select(ActiveWork.id).where(
                    ActiveWork.work_kind == "story_preview",
                    ActiveWork.target_kind == "story_idea",
                    ActiveWork.target_id == target_id,
                )
            ):
                continue
            idea["preview_status"] = "generating"
            idea["preview_error_reference"] = None
            session.add(
                ActiveWork(
                    work_kind="story_preview",
                    target_kind="story_idea",
                    target_id=target_id,
                )
            )
            jobs.append(
                {
                    "chapter_id": chapter_id,
                    "idea_id": idea_id,
                    "title": idea.get("title", ""),
                    "summary": idea.get("summary", ""),
                    "theme": idea.get("theme", classroom.story_theme),
                    "subject": classroom.subject,
                    "grade_level": classroom.grade_level,
                    "design_style": classroom.design_style,
                    "bfl_model": model,
                }
            )
        chapter.story_ideas = ideas
        session.flush()
        return jobs


def complete_story_preview(chapter_id: str, idea_id: str, object_path: str) -> None:
    storage = LocalStorage(resolve_local_paths().root)
    if not object_path.startswith("story-images/") or not storage.absolute_path(object_path).is_file():
        raise ValueError("Story preview requires durable local media")
    with _session() as session:
        chapter = session.get(Chapter, chapter_id)
        if chapter is None:
            raise GenerationConflict("Chapter no longer exists")
        ideas = [dict(idea) for idea in chapter.story_ideas or []]
        selected = next((idea for idea in ideas if idea.get("id") == idea_id), None)
        if selected is None or selected.get("preview_status") != "generating":
            raise GenerationConflict("Story preview is not active")
        selected["preview_status"] = "ready"
        selected["preview_object_path"] = object_path
        selected["preview_error_reference"] = None
        chapter.story_ideas = ideas
        session.execute(
            delete(ActiveWork).where(
                ActiveWork.work_kind == "story_preview",
                ActiveWork.target_kind == "story_idea",
                ActiveWork.target_id == f"{chapter_id}:{idea_id}",
            )
        )


def fail_story_preview(chapter_id: str, idea_id: str, error_reference: str) -> None:
    with _session() as session:
        chapter = session.get(Chapter, chapter_id)
        if chapter is not None:
            ideas = [dict(idea) for idea in chapter.story_ideas or []]
            selected = next((idea for idea in ideas if idea.get("id") == idea_id), None)
            if selected is not None and selected.get("preview_status") == "generating":
                selected["preview_status"] = "failed"
                selected["preview_object_path"] = None
                selected["preview_error_reference"] = error_reference
                chapter.story_ideas = ideas
        session.execute(
            delete(ActiveWork).where(
                ActiveWork.work_kind == "story_preview",
                ActiveWork.target_kind == "story_idea",
                ActiveWork.target_id == f"{chapter_id}:{idea_id}",
            )
        )


def fail_story_options(chapter_id: str) -> None:
    with _session() as session:
        work = session.scalar(
            select(ActiveWork).where(
                ActiveWork.work_kind == "story_options",
                ActiveWork.target_id == chapter_id,
            )
        )
        if work:
            session.delete(work)
        chapter = session.get(Chapter, chapter_id)
        if chapter and chapter.status == "draft":
            chapter.status = "failed"


def begin_avatar_work(student_id: str) -> tuple[dict[str, Any], str]:
    with _session() as session:
        student = session.get(Student, student_id)
        if student is None:
            raise ValueError("Student not found")
        if _deletion_started(session, "student", student_id):
            raise GenerationConflict("Student erasure is active")
        if session.scalar(
            select(ActiveWork.id).where(
                ActiveWork.work_kind == "avatar",
                ActiveWork.target_kind == "student",
                ActiveWork.target_id == student_id,
            )
        ):
            raise GenerationConflict("Avatar generation is already active")
        setting = session.scalar(select(Setting).where(Setting.profile_id == LOCAL_TEACHER_ID))
        model = require_supported_model(
            setting.bfl_endpoint if setting else DEFAULT_BFL_MODEL,
            SUPPORTED_BFL_MODELS,
            "BFL",
        )
        session.add(ActiveWork(work_kind="avatar", target_kind="student", target_id=student_id))
        session.flush()
        return _student(student), model


def finish_avatar_work(student_id: str) -> None:
    with _session() as session:
        session.execute(
            delete(ActiveWork).where(
                ActiveWork.work_kind == "avatar",
                ActiveWork.target_kind == "student",
                ActiveWork.target_id == student_id,
            )
        )


def choose_chapter_idea(chapter_id: str, idea_id: str) -> dict[str, Any] | None:
    """Choose an idea only while the chapter is in an explicit editable state."""
    with _session() as session:
        result = session.execute(
            update(Chapter)
            .where(
                Chapter.id == chapter_id,
                Chapter.status.in_(("options_generated", "idea_chosen", "failed")),
            )
            .values(chosen_idea_id=idea_id, status="idea_chosen")
        )
        if result.rowcount != 1:
            return None
        return _chapter(session.get(Chapter, chapter_id), session)


def claim_chapter_generation(chapter_id: str, chosen_idea_id: str) -> dict[str, Any] | None:
    """Atomically reserve the next revision for one generation request."""
    with _session() as session:
        result = session.execute(
            update(Chapter)
            .where(
                Chapter.id == chapter_id,
                Chapter.chosen_idea_id == chosen_idea_id,
                Chapter.status.in_(("idea_chosen", "failed")),
            )
            .values(status="generating")
        )
        if result.rowcount != 1:
            return None
        chapter = session.get(Chapter, chapter_id)
        claimed = _chapter(chapter, session)
        claimed["target_revision"] = chapter.revision + 1
        return claimed


def begin_generation_run(
    chapter_id: str, selected_idea_id: str, idempotency_key: str
) -> tuple[dict[str, Any], bool]:
    """Reserve at most one local run while returning identical retries unchanged."""
    if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 80:
        raise ValueError("Invalid idempotency key")
    scoped_key = hashlib.sha256(f"{chapter_id}:{idempotency_key}".encode()).hexdigest()
    try:
        with _session() as session:
            existing = session.scalar(
                select(GenerationRun).where(GenerationRun.idempotency_key == scoped_key)
            )
            if existing:
                if existing.chapter_id != chapter_id or existing.selected_idea_id != selected_idea_id:
                    raise GenerationConflict("Idempotency key does not match the original request")
                return _generation_run(existing), False

            active = session.scalar(
                select(GenerationRun).where(
                    GenerationRun.chapter_id == chapter_id,
                    GenerationRun.job_state.in_(("queued", "running")),
                )
            )
            if active:
                raise GenerationConflict("Chapter generation is already active")

            chapter = session.get(Chapter, chapter_id)
            if chapter is None:
                raise ValueError("Chapter not found")
            ideas = {idea.get("id") for idea in chapter.story_ideas or []}
            if selected_idea_id not in ideas or chapter.chosen_idea_id != selected_idea_id:
                raise ValueError("Story choice is invalid")
            if chapter.status not in ("idea_chosen", "failed", "ready"):
                raise GenerationConflict("Chapter cannot generate in its current state")

            snapshot = _generation_snapshot(session, chapter.classroom_id)
            snapshot["provider_input_student_ids"] = list(
                dict.fromkeys([*(chapter.option_student_ids or []), *snapshot["student_ids"]])
            )
            snapshot["provenance_complete"] = bool(chapter.option_provenance_complete)
            if _deletion_started(session, "chapter", chapter_id) or session.scalar(
                select(DeletionManifest.id).where(
                    DeletionManifest.target_kind == "student",
                    DeletionManifest.target_id.in_(snapshot["provider_input_student_ids"]),
                )
            ):
                raise GenerationConflict("Related deletion is active")

            run = GenerationRun(
                idempotency_key=scoped_key,
                chapter_id=chapter_id,
                selected_idea_id=selected_idea_id,
                target_revision=chapter.revision + 1,
                job_state="queued",
                stage="queued",
                artifact_paths=[],
                settings_snapshot=snapshot,
            )
            session.add(run)
            if chapter.revision == 0:
                chapter.status = "generating"
            session.flush()
            return _generation_run(run), True
    except IntegrityError:
        with _session() as session:
            winner = session.scalar(
                select(GenerationRun).where(GenerationRun.idempotency_key == scoped_key)
            )
            if winner and winner.chapter_id == chapter_id and winner.selected_idea_id == selected_idea_id:
                return _generation_run(winner), False
        raise GenerationConflict("Chapter generation is already active") from None


def begin_panel_regeneration(
    chapter_id: str,
    panel_number: int,
    base_revision: int,
    correction: str,
    idempotency_key: str,
) -> tuple[dict[str, Any], bool]:
    """Reserve one corrected panel while returning identical retries unchanged."""
    if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 80:
        raise ValueError("Invalid idempotency key")
    if not isinstance(panel_number, int) or not 1 <= panel_number <= 20:
        raise ValueError("Invalid panel number")
    correction = correction.strip() if isinstance(correction, str) else ""
    if not 1 <= len(correction) <= 500:
        raise ValueError("Invalid panel correction")
    scoped_key = hashlib.sha256(f"panel:{chapter_id}:{idempotency_key}".encode()).hexdigest()
    try:
        with _session() as session:
            existing = session.scalar(
                select(GenerationRun).where(GenerationRun.idempotency_key == scoped_key)
            )
            if existing:
                if (
                    existing.run_kind != "panel"
                    or existing.chapter_id != chapter_id
                    or existing.panel_number != panel_number
                    or existing.base_revision != base_revision
                    or existing.correction != correction
                ):
                    raise GenerationConflict("Idempotency key does not match the original request")
                return _generation_run(existing), False

            active = session.scalar(
                select(GenerationRun).where(
                    GenerationRun.chapter_id == chapter_id,
                    GenerationRun.job_state.in_(("queued", "running")),
                )
            )
            if active:
                raise GenerationConflict("Chapter generation is already active")

            chapter = session.get(Chapter, chapter_id)
            if chapter is None:
                raise ValueError("Chapter not found")
            if chapter.status != "ready":
                raise GenerationConflict("Only a ready chapter can be corrected")
            if chapter.revision != base_revision:
                raise GenerationConflict("Panel correction is stale")
            if session.scalar(
                select(Panel.id).where(
                    Panel.chapter_id == chapter_id,
                    Panel.revision == base_revision,
                    Panel.panel_number == panel_number,
                )
            ) is None:
                raise ValueError("Panel not found")
            if _deletion_started(session, "chapter", chapter_id):
                raise GenerationConflict("Related deletion is active")

            snapshot = _generation_snapshot(session, chapter.classroom_id)
            script_panel = next(
                (
                    panel
                    for panel in (chapter.story_script or {}).get("panels") or []
                    if panel.get("index") == panel_number
                ),
                {},
            )
            relevant_names = set(script_panel.get("featured_students") or [])
            relevant_names.update(
                line.get("speaker") for line in script_panel.get("dialogue") or [] if line.get("speaker")
            )
            relevant_ids = list(
                session.scalars(
                    select(Student.id)
                    .join(StudentClassroom, StudentClassroom.student_id == Student.id)
                    .where(
                        StudentClassroom.classroom_id == chapter.classroom_id,
                        Student.name.in_(relevant_names),
                    )
                    .order_by(StudentClassroom.created_at, Student.id)
                ).all()
            ) if relevant_names else []
            snapshot["student_ids"] = relevant_ids
            snapshot["provider_input_student_ids"] = relevant_ids
            snapshot["provenance_complete"] = True
            if relevant_ids and session.scalar(
                select(DeletionManifest.id).where(
                    DeletionManifest.target_kind == "student",
                    DeletionManifest.target_id.in_(relevant_ids),
                )
            ):
                raise GenerationConflict("Related deletion is active")

            run = GenerationRun(
                idempotency_key=scoped_key,
                chapter_id=chapter_id,
                run_kind="panel",
                base_revision=base_revision,
                panel_number=panel_number,
                correction=correction,
                target_revision=base_revision + 1,
                job_state="queued",
                stage="queued",
                artifact_paths=[],
                settings_snapshot=snapshot,
            )
            session.add(run)
            session.flush()
            return _generation_run(run), True
    except IntegrityError:
        with _session() as session:
            winner = session.scalar(
                select(GenerationRun).where(GenerationRun.idempotency_key == scoped_key)
            )
            if winner and winner.run_kind == "panel" and winner.chapter_id == chapter_id:
                if (
                    winner.panel_number == panel_number
                    and winner.base_revision == base_revision
                    and winner.correction == correction
                ):
                    return _generation_run(winner), False
                raise GenerationConflict("Idempotency key does not match the original request")
        raise GenerationConflict("Chapter generation is already active") from None


def get_generation_run(run_id: str) -> dict[str, Any] | None:
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        return _generation_run(run) if run else None


def _generation_snapshot(session: Session, classroom_id: str) -> dict[str, Any]:
    setting = session.scalar(select(Setting).where(Setting.profile_id == LOCAL_TEACHER_ID))
    student_ids = list(
        session.scalars(
            select(StudentClassroom.student_id)
            .where(StudentClassroom.classroom_id == classroom_id)
            .order_by(StudentClassroom.created_at, StudentClassroom.student_id)
        ).all()
    )
    story_length = int((setting.generation_defaults or {}).get("story_length", 12)) if setting else 12
    if story_length not in (12, 20):
        raise ValueError("Unsupported story length")
    openai_model = require_supported_model(
        setting.openai_model if setting else DEFAULT_OPENAI_MODEL, SUPPORTED_OPENAI_MODELS, "OpenAI"
    )
    bfl_model = require_supported_model(
        setting.bfl_endpoint if setting else DEFAULT_BFL_MODEL, SUPPORTED_BFL_MODELS, "BFL"
    )
    return {
        "story_length": story_length,
        "default_design_style": setting.default_design_style if setting else "comic",
        "openai_model": openai_model,
        "bfl_model": bfl_model,
        "automatic_panel_review": setting.automatic_panel_review if setting else False,
        "panel_review_attempt_cap": setting.panel_review_attempt_cap if setting else 3,
        "student_ids": student_ids,
        "provenance_complete": True,
    }


def start_generation_run(run_id: str) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    with _session() as session:
        result = session.execute(
            update(GenerationRun)
            .where(
                GenerationRun.id == run_id,
                GenerationRun.run_kind == "story",
                GenerationRun.job_state == "queued",
            )
            .values(job_state="running", stage="script", started_at=now)
        )
        if result.rowcount != 1:
            return None
        return _generation_run(session.get(GenerationRun, run_id))


def start_panel_regeneration_run(run_id: str) -> dict[str, Any] | None:
    """Start only a still-current one-panel correction lease."""
    now = datetime.now(timezone.utc)
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None or run.run_kind != "panel" or run.job_state != "queued":
            return None
        chapter = session.get(Chapter, run.chapter_id)
        if chapter is None or chapter.status != "ready" or chapter.revision != run.base_revision:
            run.job_state = "failed"
            run.stage = "failed"
            run.error_code = "stale"
            run.error_reference = uuid4().hex
            run.finished_at = now
            return None
        run.job_state = "running"
        run.stage = "context"
        run.started_at = now
        session.flush()
        data = _generation_run(run)
        data["correction"] = run.correction
        return data


def set_generation_stage(run_id: str, stage: str, panel_number: int | None = None) -> None:
    with _session() as session:
        values: dict[str, Any] = {"stage": stage}
        if panel_number is not None:
            values["panel_number"] = panel_number
        result = session.execute(
            update(GenerationRun)
            .where(GenerationRun.id == run_id, GenerationRun.job_state == "running")
            .values(**values)
        )
        if result.rowcount != 1:
            raise GenerationConflict("Generation run is not active")


def record_generation_script(run_id: str, script: dict[str, Any]) -> None:
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None or run.run_kind != "story" or run.job_state != "running":
            raise GenerationConflict("Generation run is not active")
        run.script_snapshot = script


def record_generation_provider_job(
    run_id: str,
    panel_number: int,
    job_id: str | None,
    polling_url: str,
    reported_cost: float | None,
) -> None:
    """Persist a paid BFL submission before its first poll."""
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None or run.job_state != "running":
            raise GenerationConflict("Generation run is not active")
        job = {
            "panel_number": panel_number,
            "job_id": job_id,
            "polling_url": polling_url,
            "reported_cost": reported_cost,
        }
        if run.provider_job == job:
            return
        run.provider_job = job
        if reported_cost is not None:
            run.reported_bfl_cost = float(run.reported_bfl_cost or 0) + reported_cost


def record_generation_checkpoint(run_id: str, panel_number: int, object_path: str) -> None:
    """Make one finalized panel resumable and remove it from cleanup bookkeeping."""
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None or run.run_kind != "story" or run.job_state != "running":
            raise GenerationConflict("Generation run is not active")
        checkpoints = list(run.checkpoint_panels or [])
        expected = len(checkpoints) + 1
        if panel_number != expected:
            raise GenerationConflict("Generation checkpoint sequence is invalid")
        checkpoints.append({"index": panel_number, "image_object_path": object_path})
        run.checkpoint_panels = checkpoints
        run.artifact_paths = [path for path in (run.artifact_paths or []) if path != object_path]
        run.provider_job = None
        run.error_code = None
        run.error_reference = None


def resume_generation_run(run_id: str) -> tuple[dict[str, Any], bool]:
    """Explicitly requeue a current failed story run without discarding paid checkpoints."""
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None or run.run_kind != "story":
            raise ValueError("Generation run not found")
        if run.job_state in ("queued", "running"):
            return _generation_run(run), False
        if run.job_state != "failed":
            raise GenerationConflict("Generation run cannot be resumed")
        chapter = session.get(Chapter, run.chapter_id)
        if (
            chapter is None
            or chapter.chosen_idea_id != run.selected_idea_id
            or run.target_revision != chapter.revision + 1
        ):
            raise GenerationConflict("Generation run is stale")
        active = session.scalar(
            select(GenerationRun.id).where(
                GenerationRun.chapter_id == run.chapter_id,
                GenerationRun.id != run.id,
                GenerationRun.job_state.in_(("queued", "running")),
            )
        )
        if active:
            raise GenerationConflict("Chapter generation is already active")
        if run.error_code in {
            "bfl_request_moderated",
            "bfl_content_moderated",
            "image_invalid",
        }:
            run.provider_job = None
        run.job_state = "queued"
        run.stage = "queued"
        run.finished_at = None
        chapter.status = "generating" if chapter.revision == 0 else "ready"
        session.flush()
        return _generation_run(run), True


def discard_generation_run(run_id: str) -> list[str]:
    """Abandon one failed story attempt and return every unpublished path for cleanup."""
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None or run.run_kind != "story":
            raise ValueError("Generation run not found")
        if run.job_state != "failed":
            raise GenerationConflict("Only a failed generation can be discarded")
        paths = [
            *(run.artifact_paths or []),
            *(
                panel.get("image_object_path")
                for panel in (run.checkpoint_panels or [])
                if isinstance(panel, dict)
            ),
        ]
        run.artifact_paths = []
        run.checkpoint_panels = []
        run.provider_job = None
        run.stage = "discarded"
        return list(dict.fromkeys(path for path in paths if isinstance(path, str)))


def record_generation_artifact(run_id: str, object_path: str) -> None:
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None or run.job_state not in ("queued", "running"):
            raise GenerationConflict("Generation run is not active")
        paths = list(run.artifact_paths or [])
        if object_path not in paths:
            run.artifact_paths = [*paths, object_path]


def finalize_generation_run(
    run_id: str, script: dict[str, Any], panels: list[dict[str, Any]]
) -> list[str]:
    with _session() as session:
        active = session.get(GenerationRun, run_id)
        if active is None or active.job_state != "running":
            raise GenerationConflict("Generation run is not active")
        expected_count = (active.settings_snapshot or {}).get("story_length")
    if expected_count not in (12, 20):
        raise ValueError("Generation run has an invalid story length snapshot")
    numbers = [panel["index"] for panel in panels]
    script_numbers = [panel.get("index") for panel in script.get("panels") or []]
    expected_numbers = list(range(1, expected_count + 1))
    if numbers != expected_numbers or script_numbers != expected_numbers:
        raise ValueError("Ready revision must match the exact snapshotted panel contract")
    storage = LocalStorage(resolve_local_paths().root)
    try:
        for panel in panels:
            object_path = panel.get("image_object_path")
            if not isinstance(object_path, str) or not object_path.startswith("story-images/"):
                raise ValueError
            if not storage.absolute_path(object_path).is_file():
                raise ValueError
    except ValueError:
        raise ValueError("Ready panels require durable local story media") from None

    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None or run.job_state != "running":
            raise GenerationConflict("Generation run is not active")
        chapter = session.get(Chapter, run.chapter_id)
        if chapter is None or run.target_revision != chapter.revision + 1:
            raise GenerationConflict("Generation target revision is stale")

        old_paths: list[str] = []
        for data in panels:
            session.add(
                Panel(
                    chapter_id=chapter.id,
                    revision=run.target_revision,
                    panel_number=data["index"],
                    dialogue=json.dumps(data.get("dialogue") or [], ensure_ascii=False),
                    scene_description=data.get("description") or "",
                    speakers=data.get("speakers") or [],
                    image_object_path=data["image_object_path"],
                )
            )
        chapter.chosen_idea_id = run.selected_idea_id
        chapter.title = script["episode_title"]
        chapter.story_script = script
        chapter.revision = run.target_revision
        chapter.status = "ready"
        run.job_state = "succeeded"
        run.stage = "ready"
        run.artifact_paths = old_paths
        run.checkpoint_panels = []
        run.provider_job = None
        run.script_snapshot = script
        run.finished_at = datetime.now(timezone.utc)
        session.flush()
        return old_paths


def complete_panel_regeneration_candidate(run_id: str, image_object_path: str) -> None:
    """Persist a generated candidate without changing the readable chapter."""
    storage = LocalStorage(resolve_local_paths().root)
    try:
        if not image_object_path.startswith("story-images/") or not storage.absolute_path(image_object_path).is_file():
            raise ValueError
    except (AttributeError, ValueError):
        raise ValueError("Corrected panel requires durable local story media") from None

    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None or run.run_kind != "panel" or run.job_state != "running":
            raise GenerationConflict("Panel regeneration run is not active")
        chapter = session.get(Chapter, run.chapter_id)
        if (
            chapter is None
            or chapter.status != "ready"
            or chapter.revision != run.base_revision
            or run.target_revision != run.base_revision + 1
        ):
            raise GenerationConflict("Panel regeneration target revision is stale")
        if session.scalar(
            select(Panel.id).where(
                Panel.chapter_id == chapter.id,
                Panel.revision == run.base_revision,
                Panel.panel_number == run.panel_number,
            )
        ) is None:
            raise GenerationConflict("Panel regeneration target is missing")
        run.candidate_object_path = image_object_path
        run.artifact_paths = [path for path in (run.artifact_paths or []) if path != image_object_path]
        run.provider_job = None
        run.stage = "candidate_ready"


def accept_panel_regeneration(run_id: str) -> list[str]:
    """Atomically publish an approved candidate while changing only its panel."""
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None or run.run_kind != "panel":
            raise ValueError("Panel regeneration not found")
        if run.job_state == "succeeded" and run.stage == "ready":
            return list(run.artifact_paths or [])
        if run.job_state != "running" or run.stage != "candidate_ready" or not run.candidate_object_path:
            raise GenerationConflict("Panel candidate is not ready")
        chapter = session.get(Chapter, run.chapter_id)
        if (
            chapter is None
            or chapter.status != "ready"
            or chapter.revision != run.base_revision
            or run.target_revision != run.base_revision + 1
        ):
            raise GenerationConflict("Panel regeneration target revision is stale")
        panels = list(
            session.scalars(
                select(Panel)
                .where(Panel.chapter_id == chapter.id, Panel.revision == run.base_revision)
                .order_by(Panel.panel_number)
            ).all()
        )
        selected = next((panel for panel in panels if panel.panel_number == run.panel_number), None)
        if selected is None:
            raise GenerationConflict("Panel regeneration target is missing")
        old_path = selected.image_object_path
        for panel in panels:
            panel.revision = run.target_revision
        selected.image_object_path = run.candidate_object_path
        chapter.revision = run.target_revision
        chapter.status = "ready"
        run.job_state = "succeeded"
        run.stage = "ready"
        run.script_snapshot = chapter.story_script
        run.candidate_object_path = None
        run.artifact_paths = [old_path]
        run.finished_at = datetime.now(timezone.utc)
        session.flush()
        still_referenced = session.scalar(
            select(Panel.id).where(Panel.image_object_path == old_path)
        )
        old_paths = [] if still_referenced else [old_path]
        run.artifact_paths = old_paths
        return old_paths


def reject_panel_regeneration(run_id: str) -> list[str]:
    """Keep the original panel and release the unpublished candidate for cleanup."""
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None or run.run_kind != "panel":
            raise ValueError("Panel regeneration not found")
        if run.job_state == "succeeded" and run.stage == "rejected":
            return list(run.artifact_paths or [])
        if run.job_state != "running" or run.stage != "candidate_ready" or not run.candidate_object_path:
            raise GenerationConflict("Panel candidate is not ready")
        path = run.candidate_object_path
        run.candidate_object_path = None
        run.artifact_paths = [path]
        run.job_state = "succeeded"
        run.stage = "rejected"
        run.finished_at = datetime.now(timezone.utc)
        return [path]


def fail_generation_run(run_id: str, error_code: str, error_reference: str) -> list[str]:
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None:
            return []
        if run.job_state not in ("queued", "running"):
            return list(run.artifact_paths or [])
        run.job_state = "failed"
        run.stage = "failed"
        run.error_code = error_code
        run.error_reference = error_reference
        run.finished_at = datetime.now(timezone.utc)
        chapter = session.get(Chapter, run.chapter_id)
        if chapter and chapter.revision == 0:
            chapter.status = "failed"
        elif chapter:
            chapter.status = "ready"
        return list(run.artifact_paths or [])


def fail_interrupted_generation_runs(database_url: str | None = None) -> list[str]:
    paths: list[str] = []
    with _session(database_url) as session:
        runs = session.scalars(
            select(GenerationRun).where(
                GenerationRun.job_state.in_(("queued", "running")),
                GenerationRun.stage != "candidate_ready",
            )
        ).all()
        for run in runs:
            run.job_state = "failed"
            run.stage = "failed"
            run.error_code = "interrupted"
            run.error_reference = uuid4().hex
            run.finished_at = datetime.now(timezone.utc)
            paths.extend(run.artifact_paths or [])
            chapter = session.get(Chapter, run.chapter_id)
            if chapter:
                chapter.status = "ready" if chapter.revision > 0 else "failed"
    return paths


def clear_interrupted_active_work(database_url: str | None = None) -> None:
    """Provider calls do not survive a local process restart."""
    with _session(database_url) as session:
        for chapter in session.scalars(select(Chapter)).all():
            ideas = [dict(idea) for idea in chapter.story_ideas or []]
            changed = False
            for idea in ideas:
                if idea.get("preview_status") in ("pending", "generating"):
                    idea["preview_status"] = "failed"
                    idea["preview_object_path"] = None
                    idea["preview_error_reference"] = uuid4().hex
                    changed = True
            if changed:
                chapter.story_ideas = ideas
        session.execute(delete(ActiveWork))


def get_pending_generation_artifacts(
    database_url: str | None = None,
) -> list[tuple[str, list[str]]]:
    with _session(database_url) as session:
        runs = session.scalars(select(GenerationRun)).all()
        return [(run.id, list(run.artifact_paths or [])) for run in runs if run.artifact_paths]


def replace_generation_artifacts(
    run_id: str, artifact_paths: list[str], database_url: str | None = None
) -> None:
    with _session(database_url) as session:
        run = session.get(GenerationRun, run_id)
        if run is not None:
            run.artifact_paths = list(dict.fromkeys(artifact_paths))


def get_chapters_by_classroom(classroom_id: str) -> list[dict[str, Any]]:
    with _session() as session:
        rows = session.scalars(
            select(Chapter).where(Chapter.classroom_id == classroom_id).order_by(Chapter.index)
        ).all()
        return [_chapter(row, session) for row in rows]


def _add_story_metadata(chapter: dict[str, Any]) -> None:
    chosen = chapter.get("chosen_idea_id")
    for idea in chapter.get("story_ideas") or []:
        if idea.get("id") == chosen:
            chapter["story_title"] = idea.get("title") or f"Chapter {chapter.get('index', '')}"
            chapter["story_description"] = idea.get("summary") or ""
            chapter["thumbnail_url"] = idea.get("preview_url")
            return
    chapter["story_title"] = f"Chapter {chapter.get('index', '')}"
    chapter["story_description"] = ""
    chapter["thumbnail_url"] = None


def create_panel(
    chapter_id: str,
    index: int,
    image: str,
    *,
    revision: int | None = None,
    dialogue: Any = "",
    scene_description: str = "",
    speakers: list[str] | None = None,
) -> dict[str, Any]:
    with _session() as session:
        chapter = session.get(Chapter, chapter_id)
        if chapter is None:
            raise ValueError("Chapter not found")
        panel = Panel(
            chapter_id=chapter_id,
            revision=chapter.revision if revision is None else revision,
            panel_number=index,
            image_object_path=_media_object_path(image),
            dialogue=dialogue if isinstance(dialogue, str) else json.dumps(dialogue, ensure_ascii=False),
            scene_description=scene_description,
            speakers=speakers or [],
        )
        session.add(panel)
        session.flush()
        return _panel(panel)


def get_panels_by_chapter(chapter_id: str) -> list[dict[str, Any]]:
    with _session() as session:
        chapter = session.get(Chapter, chapter_id)
        if chapter is None:
            return []
        rows = session.scalars(
            select(Panel)
            .where(Panel.chapter_id == chapter_id, Panel.revision == chapter.revision)
            .order_by(Panel.panel_number)
        ).all()
        return [_panel(row) for row in rows]


def delete_panels_by_chapter(
    chapter_id: str,
    *,
    revision: int | None = None,
    except_revision: int | None = None,
) -> list[str]:
    if revision is not None and except_revision is not None:
        raise ValueError("Specify revision or except_revision, not both")
    with _session() as session:
        filters = [Panel.chapter_id == chapter_id]
        if revision is not None:
            filters.append(Panel.revision == revision)
        if except_revision is not None:
            filters.append(Panel.revision != except_revision)
        object_paths = list(session.scalars(select(Panel.image_object_path).where(*filters)).all())
        session.execute(delete(Panel).where(*filters))
        return object_paths


def add_student_to_classroom(student_id: str, classroom_id: str) -> dict[str, Any]:
    with _session() as session:
        existing = session.scalar(
            select(StudentClassroom).where(
                StudentClassroom.student_id == student_id,
                StudentClassroom.classroom_id == classroom_id,
            )
        )
        if existing:
            return {"id": existing.id, "student_id": student_id, "classroom_id": classroom_id}
        if session.get(Student, student_id) is None or session.get(Classroom, classroom_id) is None:
            raise ValueError("Student or classroom not found")
        enrollment = StudentClassroom(student_id=student_id, classroom_id=classroom_id)
        session.add(enrollment)
        session.flush()
        return {"id": enrollment.id, "student_id": student_id, "classroom_id": classroom_id}


def remove_student_from_classroom(student_id: str, classroom_id: str) -> bool:
    with _session() as session:
        result = session.execute(
            delete(StudentClassroom).where(
                StudentClassroom.student_id == student_id,
                StudentClassroom.classroom_id == classroom_id,
            )
        )
        return result.rowcount > 0


def get_classrooms_by_student(student_id: str) -> list[dict[str, Any]]:
    with _session() as session:
        rows = session.scalars(
            select(Classroom)
            .join(StudentClassroom, StudentClassroom.classroom_id == Classroom.id)
            .where(StudentClassroom.student_id == student_id)
            .order_by(Classroom.created_at)
        ).all()
        return [_classroom(row) for row in rows]


def is_student_in_classroom(student_id: str, classroom_id: str) -> bool:
    with _session() as session:
        return session.scalar(
            select(StudentClassroom.id).where(
                StudentClassroom.student_id == student_id,
                StudentClassroom.classroom_id == classroom_id,
            )
        ) is not None


def delete_chapter(chapter_id: str) -> list[str] | None:
    with _session() as session:
        chapter = session.get(Chapter, chapter_id)
        if chapter is None:
            return None
        object_paths = list(
            session.scalars(select(Panel.image_object_path).where(Panel.chapter_id == chapter_id)).all()
        )
        object_paths.extend(_story_preview_paths(chapter))
        session.delete(chapter)
        return object_paths


def execute_deletion(target_kind: str, target_id: str | None = None) -> bool:
    """Delete managed files first, then rows; return false while cleanup is incomplete."""
    operation = f"{target_kind}:{target_id or 'all'}"
    with _session() as session:
        if target_kind != "reset" and session.scalar(
            select(DeletionManifest.id).where(DeletionManifest.target_kind == "reset")
        ):
            return False
        if _deletion_blocked(session, target_kind, target_id):
            return False
        manifest = session.scalar(select(DeletionManifest).where(DeletionManifest.operation == operation))
        if manifest is None:
            paths = _deletion_paths(session, target_kind, target_id)
            if target_kind == "reset":
                for outstanding in session.scalars(select(DeletionManifest)).all():
                    paths.extend(outstanding.object_paths or [])
            manifest = DeletionManifest(
                operation=operation,
                target_kind=target_kind,
                target_id=target_id,
                object_paths=paths,
                status="pending",
            )
            session.add(manifest)
            session.flush()
        elif target_kind == "reset":
            accumulated = list(manifest.object_paths or [])
            for outstanding in session.scalars(select(DeletionManifest)).all():
                accumulated.extend(outstanding.object_paths or [])
            accumulated.extend(_deletion_paths(session, target_kind, target_id))
            manifest.object_paths = list(dict.fromkeys(accumulated))
        paths = list(manifest.object_paths or [])

    storage = LocalStorage(resolve_local_paths().root)
    remaining = []
    for object_path in paths:
        try:
            storage.delete(object_path)
        except Exception:
            remaining.append(object_path)
    if remaining:
        with _session() as session:
            manifest = session.scalar(select(DeletionManifest).where(DeletionManifest.operation == operation))
            if manifest:
                manifest.object_paths = remaining
                manifest.status = "failed"
                manifest.error_reference = uuid4().hex
        return False

    with _session() as session:
        _apply_deletion(session, target_kind, target_id)
        if target_kind == "reset":
            session.execute(delete(DeletionManifest))
        else:
            manifest = session.scalar(select(DeletionManifest).where(DeletionManifest.operation == operation))
            if manifest:
                session.delete(manifest)
    return True


def _deletion_blocked(session: Session, target_kind: str, target_id: str | None) -> bool:
    active_runs = [
        run
        for run in session.scalars(
            select(GenerationRun).where(GenerationRun.job_state.in_(("queued", "running")))
        ).all()
        if run.stage != "candidate_ready"
    ]
    if target_kind == "reset" and (active_runs or session.scalar(select(ActiveWork.id))):
        return True
    if target_kind == "chapter" and any(run.chapter_id == target_id for run in active_runs):
        return True
    if target_kind == "classroom":
        chapter_ids = set(
            session.scalars(select(Chapter.id).where(Chapter.classroom_id == target_id)).all()
        )
        if any(run.chapter_id in chapter_ids for run in active_runs):
            return True
    if target_kind == "student" and any(run in _affected_runs(session, target_id) for run in active_runs):
        return True

    for work in session.scalars(select(ActiveWork)).all():
        if target_kind == "chapter" and work.target_kind == "chapter" and work.target_id == target_id:
            return True
        if target_kind == "student" and work.target_kind == "student" and work.target_id == target_id:
            return True
        work_chapter_id = (
            work.target_id.split(":", 1)[0]
            if work.target_kind == "story_idea"
            else work.target_id if work.target_kind == "chapter" else None
        )
        if work_chapter_id is None:
            continue
        if target_kind == "chapter" and work_chapter_id == target_id:
            return True
        chapter = session.get(Chapter, work_chapter_id)
        if chapter is None:
            continue
        if target_kind == "classroom" and chapter.classroom_id == target_id:
            return True
        if target_kind == "student" and (
            not chapter.option_provenance_complete
            or target_id in (chapter.option_student_ids or [])
        ):
            return True
    return False


def _deletion_paths(session: Session, target_kind: str, target_id: str | None) -> list[str]:
    paths: list[str | None] = []
    if target_kind == "chapter":
        chapter = session.get(Chapter, target_id)
        if chapter:
            paths.extend(_story_preview_paths(chapter))
        paths.extend(session.scalars(select(Panel.image_object_path).where(Panel.chapter_id == target_id)).all())
        for run in session.scalars(select(GenerationRun).where(GenerationRun.chapter_id == target_id)).all():
            paths.extend(_unpublished_generation_paths(run))
    elif target_kind == "classroom":
        chapter_ids = select(Chapter.id).where(Chapter.classroom_id == target_id)
        for chapter in session.scalars(select(Chapter).where(Chapter.classroom_id == target_id)).all():
            paths.extend(_story_preview_paths(chapter))
        paths.extend(session.scalars(select(Panel.image_object_path).where(Panel.chapter_id.in_(chapter_ids))).all())
        paths.extend(session.scalars(select(Material.object_path).where(Material.classroom_id == target_id)).all())
        for run in session.scalars(select(GenerationRun).where(GenerationRun.chapter_id.in_(chapter_ids))).all():
            paths.extend(_unpublished_generation_paths(run))
    elif target_kind == "material":
        material = session.get(Material, target_id)
        if material:
            paths.append(material.object_path)
    elif target_kind == "student":
        student = session.get(Student, target_id)
        if student:
            paths.extend(
                (
                    student.photo_object_path,
                    student.avatar_object_path,
                    student.avatar_thumbnail_object_path,
                )
            )
            paths.extend(student.superseded_avatar_paths or [])
        for run in _affected_runs(session, target_id):
            if run.job_state == "succeeded":
                continue
            paths.extend(_unpublished_generation_paths(run))
            paths.extend(
                session.scalars(
                    select(Panel.image_object_path).where(
                        Panel.chapter_id == run.chapter_id, Panel.revision == run.target_revision
                    )
                ).all()
            )
    elif target_kind == "reset":
        for chapter in session.scalars(select(Chapter)).all():
            paths.extend(_story_preview_paths(chapter))
        paths.extend(session.scalars(select(Panel.image_object_path)).all())
        paths.extend(session.scalars(select(Material.object_path)).all())
        for student in session.scalars(select(Student)).all():
            paths.extend(
                (
                    student.photo_object_path,
                    student.avatar_object_path,
                    student.avatar_thumbnail_object_path,
                )
            )
            paths.extend(student.superseded_avatar_paths or [])
        for run in session.scalars(select(GenerationRun)).all():
            paths.extend(_unpublished_generation_paths(run))
    else:
        raise ValueError("Unsupported deletion target")
    return list(dict.fromkeys(path for path in paths if path))


def _unpublished_generation_paths(run: GenerationRun) -> list[str]:
    paths = [
        *(run.artifact_paths or []),
        *(
            panel.get("image_object_path")
            for panel in (run.checkpoint_panels or [])
            if isinstance(panel, dict)
        ),
        run.candidate_object_path,
    ]
    return [path for path in paths if isinstance(path, str)]


def _story_preview_paths(chapter: Chapter) -> list[str]:
    return [
        object_path
        for idea in chapter.story_ideas or []
        if isinstance((object_path := idea.get("preview_object_path")), str)
        and object_path.startswith("story-images/")
    ]


def _affected_runs(session: Session, student_id: str | None) -> list[GenerationRun]:
    return [
        run
        for run in session.scalars(select(GenerationRun)).all()
        if not (run.settings_snapshot or {}).get("provenance_complete", False)
        or student_id in (run.settings_snapshot or {}).get("provider_input_student_ids", [])
    ]


def _apply_deletion(session: Session, target_kind: str, target_id: str | None) -> None:
    if target_kind == "chapter":
        chapter = session.get(Chapter, target_id)
        if chapter:
            session.delete(chapter)
        return
    if target_kind == "classroom":
        classroom = session.get(Classroom, target_id)
        if classroom:
            session.delete(classroom)
        return
    if target_kind == "material":
        material = session.get(Material, target_id)
        if material:
            session.delete(material)
        return
    if target_kind == "reset":
        session.execute(delete(Classroom))
        session.execute(delete(Student))
        session.execute(delete(ActiveWork))
        setting = session.scalar(select(Setting).where(Setting.profile_id == LOCAL_TEACHER_ID))
        if setting:
            setting.default_design_style = "comic"
            setting.openai_model = DEFAULT_OPENAI_MODEL
            setting.bfl_endpoint = DEFAULT_BFL_MODEL
            setting.automatic_panel_review = False
            setting.panel_review_attempt_cap = 3
            setting.generation_defaults = {"story_length": 12}
            setting.reader_preferences = {}
        return
    if target_kind != "student":
        raise ValueError("Unsupported deletion target")
    affected = [run for run in _affected_runs(session, target_id) if run.job_state != "succeeded"]
    option_chapters = [
        chapter
        for chapter in session.scalars(select(Chapter)).all()
        if (
            chapter.status != "ready"
            and (
                not chapter.option_provenance_complete
                or target_id in (chapter.option_student_ids or [])
            )
        )
    ]
    chapter_ids = {run.chapter_id for run in affected} | {chapter.id for chapter in option_chapters}
    for run in affected:
        session.execute(
            delete(Panel).where(Panel.chapter_id == run.chapter_id, Panel.revision == run.target_revision)
        )
        session.delete(run)
    student = session.get(Student, target_id)
    if student:
        session.delete(student)
    session.flush()
    for chapter_id in chapter_ids:
        chapter = session.get(Chapter, chapter_id)
        if chapter is None:
            continue
        if chapter.status == "ready":
            continue
        option_affected = chapter in option_chapters
        if option_affected:
            chapter.story_ideas = (
                [
                    {
                        "id": chapter.chosen_idea_id,
                        "title": "Classroom story",
                        "summary": "Create a new story with the current classroom.",
                    }
                ]
                if chapter.chosen_idea_id
                else []
            )
            chapter.option_student_ids = []
            chapter.option_settings_snapshot = {}
            chapter.option_provenance_complete = True
        candidates = session.scalars(
            select(GenerationRun)
            .where(GenerationRun.chapter_id == chapter_id, GenerationRun.job_state == "succeeded")
            .order_by(GenerationRun.target_revision.desc())
        ).all()
        latest = next((run for run in candidates if _valid_script_snapshot(run)), None)
        if latest:
            chapter.revision = latest.target_revision
            chapter.story_script = latest.script_snapshot
            chapter.title = (latest.script_snapshot or {}).get("episode_title")
            chapter.status = "ready"
        else:
            chapter.revision = 0
            chapter.story_script = None
            chapter.title = None
            if option_affected:
                chapter.status = "idea_chosen" if chapter.chosen_idea_id else "draft"
            else:
                chapter.status = "idea_chosen" if chapter.chosen_idea_id else "options_generated"


def _valid_script_snapshot(run: GenerationRun) -> bool:
    expected = (run.settings_snapshot or {}).get("story_length")
    panels = (run.script_snapshot or {}).get("panels") or []
    return expected in (12, 20) and [panel.get("index") for panel in panels] == list(
        range(1, expected + 1)
    )


def get_classroom_with_students(classroom_id: str) -> dict[str, Any] | None:
    classroom = get_classroom(classroom_id)
    if classroom:
        classroom["students"] = get_students_by_classroom(classroom_id)
    return classroom


def get_chapter_with_panels(chapter_id: str) -> dict[str, Any] | None:
    chapter = get_chapter(chapter_id)
    if chapter:
        chapter["panels"] = get_panels_by_chapter(chapter_id)
        chapter["temporary_panel_previews"] = _temporary_panel_previews(chapter_id)
        chapter["generation_failure"] = _latest_story_generation_failure(chapter_id)
        chapter["panel_regeneration_candidate"] = _panel_regeneration_candidate(chapter_id)
    return chapter


def _panel_regeneration_candidate(chapter_id: str) -> dict[str, Any] | None:
    with _session() as session:
        run = session.scalar(
            select(GenerationRun)
            .where(
                GenerationRun.chapter_id == chapter_id,
                GenerationRun.run_kind == "panel",
                GenerationRun.job_state == "running",
                GenerationRun.stage == "candidate_ready",
            )
            .order_by(GenerationRun.created_at.desc())
        )
        if run is None or not run.candidate_object_path:
            return None
        return {
            "run_id": run.id,
            "panel_number": run.panel_number,
            "candidate_url": media_url(run.candidate_object_path),
            "reported_bfl_cost": float(run.reported_bfl_cost) if run.reported_bfl_cost else None,
        }


def _latest_story_generation_failure(chapter_id: str) -> dict[str, Any] | None:
    with _session() as session:
        run = session.scalar(
            select(GenerationRun)
            .where(
                GenerationRun.chapter_id == chapter_id,
                GenerationRun.run_kind == "story",
            )
            .order_by(GenerationRun.created_at.desc())
        )
        if run is None or run.job_state != "failed":
            return None
        return {
            "run_id": run.id,
            "error_code": run.error_code,
            "error_reference": run.error_reference,
            "panel_number": run.panel_number,
            "completed_panels": len(run.checkpoint_panels or []),
            "expected_panels": int((run.settings_snapshot or {}).get("story_length", 0)),
            "reported_bfl_cost": float(run.reported_bfl_cost or 0),
            "resumable": bool(run.script_snapshot),
        }


def _temporary_panel_previews(chapter_id: str) -> list[dict[str, Any]]:
    with _session() as session:
        run = session.scalar(
            select(GenerationRun)
            .where(
                GenerationRun.chapter_id == chapter_id,
                GenerationRun.run_kind == "story",
                GenerationRun.job_state.in_(("queued", "running", "failed")),
            )
            .order_by(GenerationRun.created_at.desc())
        )
        checkpoints = list(run.checkpoint_panels or []) if run else []
    storage = LocalStorage(resolve_local_paths().root)
    previews = []
    for checkpoint in checkpoints:
        try:
            object_path = checkpoint["image_object_path"]
            if object_path.startswith("story-images/") and storage.absolute_path(object_path).is_file():
                previews.append({"index": int(checkpoint["index"]), "image": media_url(object_path)})
        except (AttributeError, KeyError, TypeError, ValueError, StorageValidationError):
            continue
    return previews

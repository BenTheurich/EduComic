"""Concrete SQLite persistence used by the local/private application."""

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Iterator
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from database.models import Chapter, Classroom, LocalProfile, Panel, Student, StudentClassroom
from database.session import create_session_factory
from local_runtime import local_database_url, resolve_local_paths
from local_storage import LocalStorage, media_url

LOCAL_TEACHER_ID = "00000000-0000-0000-0000-000000000001"


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
        "created_at": _iso(student.created_at),
        "updated_at": _iso(student.updated_at),
    }


def _chapter(chapter: Chapter) -> dict[str, Any]:
    data = {
        "id": chapter.id,
        "classroom_id": chapter.classroom_id,
        "index": chapter.index,
        "original_prompt": chapter.original_prompt,
        "story_ideas": chapter.story_ideas or [],
        "chosen_idea_id": chapter.chosen_idea_id,
        "status": chapter.status,
        "revision": chapter.revision,
        "story_script": chapter.story_script,
        "thumbnail_url": None,
        "created_at": _iso(chapter.created_at),
        "updated_at": _iso(chapter.updated_at),
    }
    _add_story_title(data)
    return data


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


def get_chapter(chapter_id: str) -> dict[str, Any] | None:
    with _session() as session:
        chapter = session.get(Chapter, chapter_id)
        return _chapter(chapter) if chapter else None


def create_chapter(data: dict[str, Any]) -> dict[str, Any]:
    allowed = {"classroom_id", "index", "original_prompt", "story_ideas", "chosen_idea_id", "title", "status"}
    if set(data) - allowed:
        raise ValueError("Unsupported chapter field")
    with _session() as session:
        chapter = Chapter(**data)
        session.add(chapter)
        session.flush()
        return _chapter(chapter)


def update_chapter(chapter_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"story_ideas", "chosen_idea_id", "title", "status", "revision", "story_script"}
    if set(updates) - allowed:
        raise ValueError("Unsupported chapter update")
    with _session() as session:
        chapter = session.get(Chapter, chapter_id)
        if chapter is None:
            return None
        for key, value in updates.items():
            setattr(chapter, key, value)
        session.flush()
        return _chapter(chapter)


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
        claimed = _chapter(chapter)
        claimed["target_revision"] = chapter.revision + 1
        return claimed


def get_chapters_by_classroom(classroom_id: str) -> list[dict[str, Any]]:
    with _session() as session:
        rows = session.scalars(
            select(Chapter).where(Chapter.classroom_id == classroom_id).order_by(Chapter.index)
        ).all()
        return [_chapter(row) for row in rows]


def _add_story_title(chapter: dict[str, Any]) -> None:
    chosen = chapter.get("chosen_idea_id")
    for idea in chapter.get("story_ideas") or []:
        if idea.get("id") == chosen:
            chapter["story_title"] = idea.get("title") or f"Chapter {chapter.get('index', '')}"
            return
    chapter["story_title"] = f"Chapter {chapter.get('index', '')}"


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
        session.delete(chapter)
        return object_paths


def get_classroom_with_students(classroom_id: str) -> dict[str, Any] | None:
    classroom = get_classroom(classroom_id)
    if classroom:
        classroom["students"] = get_students_by_classroom(classroom_id)
    return classroom


def get_chapter_with_panels(chapter_id: str) -> dict[str, Any] | None:
    chapter = get_chapter(chapter_id)
    if chapter:
        chapter["panels"] = get_panels_by_chapter(chapter_id)
    return chapter

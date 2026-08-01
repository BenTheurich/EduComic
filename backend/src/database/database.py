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

from database.models import Chapter, Classroom, GenerationRun, LocalProfile, Panel, Student, StudentClassroom
from database.session import create_session_factory
from local_runtime import local_database_url, resolve_local_paths
from local_storage import LocalStorage, media_url

LOCAL_TEACHER_ID = "00000000-0000-0000-0000-000000000001"


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


def _generation_run(run: GenerationRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "chapter_id": run.chapter_id,
        "selected_idea_id": run.selected_idea_id,
        "target_revision": run.target_revision,
        "job_state": run.job_state,
        "stage": run.stage,
        "error_code": run.error_code,
        "error_reference": run.error_reference,
        "artifact_paths": list(run.artifact_paths or []),
        "started_at": _iso(run.started_at) if run.started_at else None,
        "finished_at": _iso(run.finished_at) if run.finished_at else None,
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
        return _chapter(session.get(Chapter, chapter_id))


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

            run = GenerationRun(
                idempotency_key=scoped_key,
                chapter_id=chapter_id,
                selected_idea_id=selected_idea_id,
                target_revision=chapter.revision + 1,
                job_state="queued",
                stage="queued",
                artifact_paths=[],
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


def get_generation_run(run_id: str) -> dict[str, Any] | None:
    with _session() as session:
        run = session.get(GenerationRun, run_id)
        return _generation_run(run) if run else None


def start_generation_run(run_id: str) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc)
    with _session() as session:
        result = session.execute(
            update(GenerationRun)
            .where(GenerationRun.id == run_id, GenerationRun.job_state == "queued")
            .values(job_state="running", stage="script", started_at=now)
        )
        if result.rowcount != 1:
            return None
        return _generation_run(session.get(GenerationRun, run_id))


def set_generation_stage(run_id: str, stage: str) -> None:
    with _session() as session:
        result = session.execute(
            update(GenerationRun)
            .where(GenerationRun.id == run_id, GenerationRun.job_state == "running")
            .values(stage=stage)
        )
        if result.rowcount != 1:
            raise GenerationConflict("Generation run is not active")


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
    numbers = [panel["index"] for panel in panels]
    if not numbers or numbers != list(range(1, len(numbers) + 1)):
        raise ValueError("Ready panel sequence must be complete")
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

        old_paths = list(
            session.scalars(select(Panel.image_object_path).where(Panel.chapter_id == chapter.id)).all()
        )
        session.execute(delete(Panel).where(Panel.chapter_id == chapter.id))
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
        run.finished_at = datetime.now(timezone.utc)
        session.flush()
        return old_paths


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
            select(GenerationRun).where(GenerationRun.job_state.in_(("queued", "running")))
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

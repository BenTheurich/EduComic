"""Local database migration and constraint behavior."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.migrations import upgrade_database
from database.models import Chapter, Classroom, LocalProfile, Panel, Student, StudentClassroom
from database.session import create_local_engine


def _database_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_blank_database_upgrades_to_migration_head(tmp_path):
    """Catches missing initial tables or an unapplied Alembic head revision."""
    url = _database_url(tmp_path / "educomic.db")

    upgrade_database(url)

    engine = create_engine(url)
    assert set(inspect(engine).get_table_names()) == {
        "alembic_version",
        "chapter_materials",
        "chapters",
        "classrooms",
        "generation_runs",
        "local_profiles",
        "materials",
        "panels",
        "settings",
        "student_classrooms",
        "students",
    }
    assert engine.connect().execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_local_foundation"


def test_database_records_survive_engine_restart(tmp_path):
    """Catches local writes being held only in process memory or a transient connection."""
    url = _database_url(tmp_path / "educomic.db")
    upgrade_database(url)
    first_engine = create_local_engine(url)
    owner = LocalProfile(display_name="Local Teacher")
    classroom = Classroom(
        owner=owner,
        name="Fictional Science Lab",
        subject="Science",
        grade_level="5",
        story_theme="Space",
        design_style="comic",
    )
    with Session(first_engine) as session:
        session.add(classroom)
        session.commit()
        classroom_id = classroom.id
    first_engine.dispose()

    restarted_engine = create_local_engine(url)
    with Session(restarted_engine) as session:
        assert session.get(Classroom, classroom_id).name == "Fictional Science Lab"


def test_sqlite_connections_enforce_foreign_keys(tmp_path):
    """Catches orphan enrollment rows being accepted by SQLite."""
    url = _database_url(tmp_path / "educomic.db")
    upgrade_database(url)
    engine = create_local_engine(url)

    with Session(engine) as session:
        session.add(StudentClassroom(student_id="00000000-0000-0000-0000-000000000001", classroom_id="00000000-0000-0000-0000-000000000002"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_schema_rejects_duplicate_enrollment(tmp_path):
    """Catches the enrollment uniqueness constraint disappearing."""
    url = _database_url(tmp_path / "educomic.db")
    upgrade_database(url)
    engine = create_local_engine(url)
    owner = LocalProfile(display_name="Local Teacher")
    classroom = Classroom(owner=owner, name="History", subject="History", grade_level="6", story_theme="Voyage", design_style="manga")
    student = Student(name="Avery Example", interests="maps")

    with Session(engine) as session:
        session.add_all([classroom, student])
        session.flush()
        session.add(StudentClassroom(student_id=student.id, classroom_id=classroom.id))
        session.commit()
        session.add(StudentClassroom(student_id=student.id, classroom_id=classroom.id))
        with pytest.raises(IntegrityError):
            session.commit()


def test_schema_rejects_invalid_panel_number(tmp_path):
    """Catches the positive panel-sequence constraint disappearing."""
    url = _database_url(tmp_path / "educomic.db")
    upgrade_database(url)
    engine = create_local_engine(url)
    owner = LocalProfile(display_name="Local Teacher")
    classroom = Classroom(owner=owner, name="History", subject="History", grade_level="6", story_theme="Voyage", design_style="manga")

    with Session(engine) as session:
        session.add(classroom)
        session.flush()
        chapter = Chapter(classroom_id=classroom.id, index=1, original_prompt="Fictional lesson", status="draft", revision=0)
        session.add(chapter)
        session.flush()
        session.add(Panel(chapter_id=chapter.id, revision=0, panel_number=0, dialogue="", scene_description="Opening", speakers=[], image_object_path="story-images/example/panel.png"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_deleting_classroom_cascades_owned_story_rows(tmp_path):
    """Catches classroom deletion leaving chapter rows behind."""
    url = _database_url(tmp_path / "educomic.db")
    upgrade_database(url)
    engine = create_local_engine(url)
    owner = LocalProfile(display_name="Local Teacher")
    classroom = Classroom(owner=owner, name="Math", subject="Math", grade_level="4", story_theme="Robots", design_style="cartoon")

    with Session(engine) as session:
        session.add(classroom)
        session.flush()
        classroom_id = classroom.id
        session.add(Chapter(classroom_id=classroom_id, index=1, original_prompt="Fractions", status="draft", revision=0))
        session.commit()
        session.delete(classroom)
        session.commit()
        assert session.execute(text("SELECT COUNT(*) FROM chapters WHERE classroom_id = :id"), {"id": classroom_id}).scalar_one() == 0

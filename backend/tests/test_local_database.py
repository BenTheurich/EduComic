"""Local database migration and constraint behavior."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from database.migrations import upgrade_database
from database.models import (
    Base,
    Chapter,
    ChapterMaterial,
    Classroom,
    GenerationRun,
    LocalProfile,
    Material,
    Panel,
    Student,
    StudentClassroom,
)
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
    assert engine.connect().execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002_generation_durability"
    generation_columns = {column["name"] for column in inspect(engine).get_columns("generation_runs")}
    assert {"selected_idea_id", "stage", "error_code", "artifact_paths"} <= generation_columns
    indexes = {index["name"] for index in inspect(engine).get_indexes("generation_runs")}
    assert "uq_generation_runs_active_chapter" in indexes


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


def test_material_provenance_foreign_key_cascades(tmp_path):
    """Catches a PostgreSQL-hostile immediate restriction on owned provenance rows."""
    url = _database_url(tmp_path / "educomic.db")
    upgrade_database(url)

    foreign_keys = inspect(create_engine(url)).get_foreign_keys("chapter_materials")
    material_key = next(key for key in foreign_keys if key["constrained_columns"] == ["material_id"])

    assert material_key["options"]["ondelete"] == "CASCADE"


def test_deleting_classroom_cascades_material_provenance_graph(tmp_path):
    """Catches classroom deletion leaving material provenance rows behind."""
    url = _database_url(tmp_path / "educomic.db")
    upgrade_database(url)
    engine = create_local_engine(url)
    owner = LocalProfile(display_name="Local Teacher")
    classroom = Classroom(owner=owner, name="Science", subject="Science", grade_level="5", story_theme="Space", design_style="comic")
    material = Material(
        classroom_id=classroom.id,
        source_filename="fictional.pdf",
        object_path="materials/example/fictional.pdf",
        extraction_state="ready",
        content_hash="a" * 64,
        extracted_pages=[],
    )
    chapter = Chapter(classroom_id=classroom.id, index=1, original_prompt="Orbits", status="draft", revision=0)

    with Session(engine) as session:
        session.add(classroom)
        session.flush()
        material.classroom_id = classroom.id
        chapter.classroom_id = classroom.id
        session.add_all([material, chapter])
        session.flush()
        session.add(ChapterMaterial(chapter_id=chapter.id, material_id=material.id, content_hash=material.content_hash))
        session.commit()
        session.delete(classroom)
        session.commit()

        for table in ("chapter_materials", "chapters", "materials"):
            assert session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one() == 0


def test_timestamps_reload_normalized_to_utc(tmp_path):
    """Catches SQLite returning naive or non-UTC persisted timestamps."""
    url = _database_url(tmp_path / "educomic.db")
    upgrade_database(url)
    first_engine = create_local_engine(url)
    owner = LocalProfile(
        display_name="Local Teacher",
        created_at=datetime(2026, 8, 1, 12, 30, tzinfo=timezone(timedelta(hours=2))),
    )
    with Session(first_engine) as session:
        session.add(owner)
        session.commit()
        owner_id = owner.id
    first_engine.dispose()

    restarted_engine = create_local_engine(url)
    with Session(restarted_engine) as session:
        loaded = session.get(LocalProfile, owner_id)
        assert loaded.created_at == datetime(2026, 8, 1, 10, 30, tzinfo=timezone.utc)
        assert loaded.updated_at.utcoffset() == timedelta(0)


def test_generation_run_timestamps_reload_normalized_to_utc(tmp_path):
    """Catches generation-run lifecycle timestamps bypassing UTC normalization."""
    url = _database_url(tmp_path / "educomic.db")
    upgrade_database(url)
    first_engine = create_local_engine(url)
    owner = LocalProfile(display_name="Local Teacher")
    classroom = Classroom(owner=owner, name="Science", subject="Science", grade_level="5", story_theme="Space", design_style="comic")
    with Session(first_engine) as session:
        session.add(classroom)
        session.flush()
        chapter = Chapter(classroom_id=classroom.id, index=1, original_prompt="Orbits", status="draft", revision=0)
        session.add(chapter)
        session.flush()
        run = GenerationRun(
            idempotency_key="fictional-run",
            chapter_id=chapter.id,
            target_revision=1,
            job_state="running",
            started_at=datetime(2026, 8, 1, 12, 30, tzinfo=timezone(timedelta(hours=2))),
        )
        session.add(run)
        session.commit()
        run_id = run.id
    first_engine.dispose()

    restarted_engine = create_local_engine(url)
    with Session(restarted_engine) as session:
        loaded = session.get(GenerationRun, run_id)
        assert loaded.started_at == datetime(2026, 8, 1, 10, 30, tzinfo=timezone.utc)


def test_schema_compiles_for_postgresql_dialect():
    """Catches SQLite-only column definitions entering the portable model contract."""
    statements = [str(CreateTable(table).compile(dialect=postgresql.dialect())) for table in Base.metadata.sorted_tables]

    assert len(statements) == 10

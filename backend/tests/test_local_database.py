"""Local database migration and constraint behavior."""

from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
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


def _upgrade_to(database_url: str, revision: str) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, revision)


def _downgrade_to(database_url: str, revision: str) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.downgrade(config, revision)


def test_blank_database_upgrades_to_migration_head(tmp_path):
    """Catches missing initial tables or an unapplied Alembic head revision."""
    url = _database_url(tmp_path / "educomic.db")

    upgrade_database(url)

    engine = create_engine(url)
    assert set(inspect(engine).get_table_names()) == {
        "active_work",
        "alembic_version",
            "chapter_materials",
            "chapters",
            "classrooms",
            "deletion_manifests",
        "generation_runs",
        "local_profiles",
        "materials",
        "panels",
        "settings",
        "student_classrooms",
        "students",
    }
    assert engine.connect().execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0010_generation_checkpoints"
    student_columns = {column["name"] for column in inspect(engine).get_columns("students")}
    assert "avatar_thumbnail_object_path" in student_columns
    generation_columns = {column["name"] for column in inspect(engine).get_columns("generation_runs")}
    assert {
        "selected_idea_id",
        "stage",
        "error_code",
        "artifact_paths",
        "checkpoint_panels",
        "provider_job",
        "reported_bfl_cost",
        "candidate_object_path",
    } <= generation_columns
    indexes = {index["name"] for index in inspect(engine).get_indexes("generation_runs")}
    assert "uq_generation_runs_active_chapter" in indexes


def test_populated_0001_database_reconciles_active_runs_before_unique_index(tmp_path):
    """Catches migration failure or story loss when legacy active rows already collide."""
    url = _database_url(tmp_path / "educomic.db")
    _upgrade_to(url, "0001_local_foundation")
    engine = create_engine(url)
    owner = "00000000-0000-4000-8000-000000000001"
    classroom = "00000000-0000-4000-8000-000000000002"
    readable = "00000000-0000-4000-8000-000000000003"
    initial = "00000000-0000-4000-8000-000000000004"
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO local_profiles (id, display_name, role, display_settings) VALUES (:id, 'Teacher', 'teacher', '{}')"),
            {"id": owner},
        )
        connection.execute(
            text("""
                INSERT INTO classrooms
                    (id, owner_id, name, subject, grade_level, story_theme, design_style)
                VALUES (:id, :owner, 'Class', 'Science', '6', 'Space', 'comic')
            """),
            {"id": classroom, "owner": owner},
        )
        connection.execute(
            text("""
                INSERT INTO chapters
                    (id, classroom_id, "index", original_prompt, story_ideas, chosen_idea_id, status, revision)
                VALUES
                    (:readable, :classroom, 1, 'Orbits', '[]', 'idea_1', 'generating', 1),
                    (:initial, :classroom, 2, 'Forces', '[]', 'idea_1', 'generating', 0)
            """),
            {"readable": readable, "initial": initial, "classroom": classroom},
        )
        connection.execute(
            text("""
                INSERT INTO panels
                    (id, chapter_id, revision, panel_number, dialogue, scene_description, speakers, image_object_path)
                VALUES
                    ('00000000-0000-4000-8000-000000000005', :chapter, 1, 1, '', 'Old', '[]',
                     'story-images/00000000-0000-4000-8000-000000000003/old.png')
            """),
            {"chapter": readable},
        )
        for suffix, chapter_id in (("6", readable), ("7", readable), ("8", initial)):
            connection.execute(
                text("""
                    INSERT INTO generation_runs
                        (id, idempotency_key, chapter_id, target_revision, job_state)
                    VALUES (:id, :key, :chapter, 2, 'running')
                """),
                {
                    "id": f"00000000-0000-4000-8000-00000000000{suffix}",
                    "key": f"legacy-{suffix}",
                    "chapter": chapter_id,
                },
            )

    upgrade_database(url)

    with engine.connect() as connection:
        runs = connection.execute(
            text(
                "SELECT job_state, stage, error_code, error_reference FROM generation_runs WHERE id IN ("
                "'00000000-0000-4000-8000-000000000006', '00000000-0000-4000-8000-000000000007', "
                "'00000000-0000-4000-8000-000000000008')"
            )
        ).mappings().all()
        statuses = dict(connection.execute(text("SELECT id, status FROM chapters")).all())
    assert all(
        run["job_state"] == "failed"
        and run["stage"] == "failed"
        and run["error_code"] == "interrupted"
        and run["error_reference"]
        for run in runs
    )
    assert statuses[readable] == "ready"
    assert statuses[initial] == "failed"
    index = next(index for index in GenerationRun.__table__.indexes if index.name == "uq_generation_runs_active_chapter")
    assert str(index.dialect_options["sqlite"]["where"]) == str(index.dialect_options["postgresql"]["where"])


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


def test_material_provenance_does_not_reference_deletable_source_row(tmp_path):
    """Catches source deletion erasing immutable chapter provenance."""
    url = _database_url(tmp_path / "educomic.db")
    upgrade_database(url)

    foreign_keys = inspect(create_engine(url)).get_foreign_keys("chapter_materials")
    assert all(key["constrained_columns"] != ["material_id"] for key in foreign_keys)


def test_material_grounding_migration_marks_real_legacy_provenance_incomplete(tmp_path):
    """Catches legacy ID/hash/filename rows being fabricated or serialized as applied grounding."""
    url = _database_url(tmp_path / "educomic.db")
    _upgrade_to(url, "0005_provider_provenance")
    engine = create_engine(url)
    ids = {name: uuid4().hex for name in ("profile", "classroom", "material", "chapter", "link")}
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO local_profiles (id, display_name, role, display_settings) "
            "VALUES (:profile, 'Teacher', 'teacher', '{}')"
        ), ids)
        connection.execute(text(
            "INSERT INTO classrooms (id, owner_id, name, subject, grade_level, story_theme, design_style) "
            "VALUES (:classroom, :profile, 'Science', 'Space', '7', 'Moons', 'comic')"
        ), ids)
        connection.execute(text(
            "INSERT INTO materials (id, classroom_id, source_filename, extraction_state, content_hash) "
            "VALUES (:material, :classroom, 'legacy.pdf', 'ready', :hash)"
        ), {**ids, "hash": "b" * 64})
        connection.execute(text(
            "INSERT INTO chapters (id, classroom_id, \"index\", original_prompt, status, revision, "
            "option_student_ids, option_provenance_complete, option_settings_snapshot) "
            "VALUES (:chapter, :classroom, 1, 'Moons', 'draft', 0, '[]', 1, '{}')"
        ), ids)
        connection.execute(text(
            "INSERT INTO chapter_materials (id, chapter_id, material_id, content_hash) "
            "VALUES (:link, :chapter, :material, :hash)"
        ), {**ids, "hash": "b" * 64})

    upgrade_database(url)
    columns = {column["name"] for column in inspect(engine).get_columns("chapter_materials")}
    assert "grounding_applied" in columns
    with engine.begin() as connection:
        retained = connection.execute(text(
            "SELECT material_id, content_hash, source_label, excerpts, grounding_applied FROM chapter_materials"
        )).one()
        connection.execute(text("DELETE FROM materials WHERE id = :material"), ids)
        count = connection.execute(text("SELECT COUNT(*) FROM chapter_materials")).scalar_one()

    assert tuple(retained) == (ids["material"], "b" * 64, "legacy.pdf", "[]", 0)
    assert count == 1
    import database.database as database

    with database._session(url) as session:
        serialized = database._chapter(session.get(Chapter, ids["chapter"]), session)
    assert serialized["grounded_sources"] == []
    assert serialized["material_provenance"] == [{
        "material_id": str(UUID(ids["material"])),
        "content_hash": "b" * 64,
        "source_label": "legacy.pdf",
        "excerpts": [],
        "grounding_applied": False,
    }]


def test_populated_material_migration_downgrades_filters_deleted_sources_and_reupgrades(tmp_path):
    """Catches a no-op downgrade, broken v5 FKs, or deleted provenance reappearing on re-upgrade."""
    url = _database_url(tmp_path / "educomic.db")
    _upgrade_to(url, "0005_provider_provenance")
    engine = create_engine(url)
    ids = {name: str(uuid4()) for name in (
        "profile", "classroom", "chapter", "live_material", "deleted_material", "live_link", "deleted_link"
    )}
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO local_profiles (id, display_name, role, display_settings) "
            "VALUES (:profile, 'Teacher', 'teacher', '{}')"
        ), ids)
        connection.execute(text(
            "INSERT INTO classrooms (id, owner_id, name, subject, grade_level, story_theme, design_style) "
            "VALUES (:classroom, :profile, 'Science', 'Space', '7', 'Moons', 'comic')"
        ), ids)
        connection.execute(text(
            "INSERT INTO chapters (id, classroom_id, \"index\", original_prompt, status, revision, "
            "option_student_ids, option_provenance_complete, option_settings_snapshot) "
            "VALUES (:chapter, :classroom, 1, 'Moons', 'draft', 0, '[]', 1, '{}')"
        ), ids)
        connection.execute(text(
            "INSERT INTO materials (id, classroom_id, source_filename, extraction_state, content_hash) VALUES "
            "(:live_material, :classroom, 'live.pdf', 'ready', :live_hash), "
            "(:deleted_material, :classroom, 'deleted.pdf', 'ready', :deleted_hash)"
        ), {**ids, "live_hash": "c" * 64, "deleted_hash": "d" * 64})
        connection.execute(text(
            "INSERT INTO chapter_materials (id, chapter_id, material_id, content_hash) VALUES "
            "(:live_link, :chapter, :live_material, :live_hash), "
            "(:deleted_link, :chapter, :deleted_material, :deleted_hash)"
        ), {**ids, "live_hash": "c" * 64, "deleted_hash": "d" * 64})

    upgrade_database(url)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM materials WHERE id = :deleted_material"), ids)
        assert connection.execute(text("SELECT COUNT(*) FROM chapter_materials")).scalar_one() == 2

    _downgrade_to(url, "0005_provider_provenance")
    assert any(
        foreign_key["constrained_columns"] == ["material_id"]
        for foreign_key in inspect(engine).get_foreign_keys("chapter_materials")
    )
    with engine.connect() as connection:
        assert connection.execute(text("SELECT material_id FROM chapter_materials")).scalar_one() == ids["live_material"]

    upgrade_database(url)
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT material_id, source_label, grounding_applied FROM chapter_materials"
        )).one()
    assert tuple(row) == (ids["live_material"], "live.pdf", 0)


def test_material_migration_postgresql_ddl_uses_collision_free_temporary_names():
    """Catches rename-first PostgreSQL DDL reusing schema-scoped v5 constraint names."""
    backend_root = Path(__file__).resolve().parents[1]
    output = StringIO()
    config = Config(str(backend_root / "alembic.ini"), output_buffer=output)
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", "postgresql://example.invalid/educomic")

    command.upgrade(config, "0005_provider_provenance:0006_material_grounding", sql=True)

    ddl = output.getvalue()
    assert "CREATE TABLE chapter_materials_v6" in ddl
    assert "CONSTRAINT fk_chapter_materials_v6_chapter" in ddl
    assert "CONSTRAINT uq_chapter_material_v6" in ddl
    assert "ALTER TABLE chapter_materials RENAME TO chapter_materials_v5" not in ddl


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
        session.add(ChapterMaterial(
            chapter_id=chapter.id,
            material_id=material.id,
            content_hash=material.content_hash,
            source_label="fictional.pdf",
            excerpts=[{"page": 1, "text": "Fictional orbit fact."}],
        ))
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

    assert len(statements) == 12

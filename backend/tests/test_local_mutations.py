"""Behavioral coverage for durable local edits, settings, and deletion."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from local_storage import LocalStorage, media_url


def _client(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    import database.database as database
    from main import app

    database._factory.cache_clear()
    return TestClient(app), database


def _classroom(client: TestClient):
    return client.post(
        "/classrooms",
        json={
            "name": "Fictional Lab",
            "subject": "Science",
            "grade_level": "6",
            "story_theme": "Space",
            "design_style": "comic",
        },
    ).json()["classroom"]


def test_edits_and_settings_persist_and_generation_snapshots_the_selected_contract(monkeypatch, tmp_path):
    """Catches edits being cosmetic or later settings mutating a queued run."""
    client, database = _client(monkeypatch, tmp_path)
    with client:
        classroom = _classroom(client)
        student = client.post(
            "/students/create",
            json={"name": "Ari", "interests": "orbits", "classroom_id": classroom["id"]},
        ).json()["student"]

        edited_classroom = client.patch(
            f"/classrooms/{classroom['id']}",
            json={**{key: classroom[key] for key in ("name", "subject", "grade_level", "story_theme", "design_style")}, "name": "Orbital Lab"},
        )
        edited_student = client.patch(
            f"/students/{student['id']}", json={"name": "Ari Moon", "interests": "orbits"}
        )
        settings = client.patch(
            "/settings",
            json={
                "story_length": 20,
                "default_design_style": "manga",
                "openai_model": "gpt-5.1",
                "bfl_model": "flux-2-pro",
                "automatic_panel_review": True,
                "panel_review_attempt_cap": 2,
                "reader_preferences": {"large_text": True},
            },
        )

        assert edited_classroom.status_code == edited_student.status_code == settings.status_code == 200
        chapter = database.create_chapter(
            {
                "classroom_id": classroom["id"],
                "index": 1,
                "original_prompt": "Teach orbits",
                "story_ideas": [{"id": "idea_1", "title": "Orbit", "summary": "Learn"}],
                "chosen_idea_id": "idea_1",
                "status": "idea_chosen",
            }
        )
        run, _ = database.begin_generation_run(chapter["id"], "idea_1", "fictional-run")
        client.patch("/settings", json={"story_length": 12})

    with client:
        assert client.get(f"/classrooms/{classroom['id']}").json()["classroom"]["name"] == "Orbital Lab"
        assert client.get(f"/students/{student['id']}").json()["student"]["name"] == "Ari Moon"
        assert client.get("/settings").json()["settings"]["story_length"] == 12
        snapshot = database.get_generation_run(run["id"])["settings_snapshot"]
        assert snapshot["story_length"] == 20
        assert snapshot["student_ids"] == [student["id"]]
        assert "key" not in " ".join(snapshot).lower()


def test_chapter_delete_reports_cleanup_failure_and_retry_is_idempotent(monkeypatch, tmp_path):
    """Catches deletion success while a required panel file or row remains."""
    client, database = _client(monkeypatch, tmp_path)
    with client:
        classroom = _classroom(client)
        chapter = database.create_chapter(
            {"classroom_id": classroom["id"], "index": 1, "original_prompt": "Fractions", "status": "draft"}
        )
        storage = LocalStorage(tmp_path)
        object_path = storage.new_object_path("story-images", chapter["id"], ".png")
        storage.finalize(storage.stage_bytes(b"fictional", ".png", max_bytes=20), object_path)
        database.create_panel(chapter["id"], 1, media_url(object_path))

        original = LocalStorage.delete
        monkeypatch.setattr(LocalStorage, "delete", lambda self, path: (_ for _ in ()).throw(OSError("busy")))
        failed = client.delete(f"/chapters/{chapter['id']}?confirm=true")

        assert failed.status_code == 409
        assert failed.json()["detail"] == "Local file cleanup is incomplete; retry deletion"
        assert database.get_chapter(chapter["id"]) is not None
        assert storage.absolute_path(object_path).is_file()
        from local_runtime import local_readiness_details
        assert local_readiness_details(tmp_path)["cleanup"] is False

        monkeypatch.setattr(LocalStorage, "delete", original)
        assert client.delete(f"/chapters/{chapter['id']}?confirm=true").status_code == 200
        assert client.delete(f"/chapters/{chapter['id']}?confirm=true").status_code == 200
        assert database.get_chapter(chapter["id"]) is None
        assert not storage.absolute_path(object_path).exists()


def test_full_student_erasure_removes_affected_revision_and_preserves_chapter_shell(monkeypatch, tmp_path):
    """Catches profile deletion leaving an identifiable story revision readable."""
    client, database = _client(monkeypatch, tmp_path)
    with client:
        classroom = _classroom(client)
        student = client.post(
            "/students/create",
            json={"name": "Mina", "interests": "bridges", "classroom_id": classroom["id"]},
        ).json()["student"]
        chapter = database.create_chapter(
            {
                "classroom_id": classroom["id"],
                "index": 1,
                "original_prompt": "Teach forces",
                "story_ideas": [{"id": "idea_1", "title": "Bridge", "summary": "Learn"}],
                "chosen_idea_id": "idea_1",
                "status": "idea_chosen",
            }
        )
        run, _ = database.begin_generation_run(chapter["id"], "idea_1", "student-run")
        database.start_generation_run(run["id"])
        storage = LocalStorage(tmp_path)
        object_paths = []
        for _index in range(12):
            object_path = storage.new_object_path("story-images", chapter["id"], ".png")
            storage.finalize(storage.stage_bytes(b"fictional", ".png", max_bytes=20), object_path)
            object_paths.append(object_path)
        script = {
            "episode_title": "Bridge Story",
            "learning_objectives": ["Forces"],
            "panels": [
                {"index": index, "featured_students": ["Mina"]}
                for index in range(1, 13)
            ],
        }
        database.finalize_generation_run(
            run["id"],
            script,
            [
                {
                    "index": index,
                    "description": "Mina builds",
                    "image_object_path": object_path,
                }
                for index, object_path in enumerate(object_paths, 1)
            ],
        )

        erased = client.delete(f"/students/{student['id']}?confirm=true")

        assert erased.status_code == 200
        assert database.get_student(student["id"]) is None
        shell = database.get_chapter(chapter["id"])
        assert shell["revision"] == 0
        assert shell["chosen_idea_id"] == "idea_1"
        assert shell["story_script"] is None
        assert database.get_panels_by_chapter(chapter["id"]) == []
        assert all(not storage.absolute_path(path).exists() for path in object_paths)


def test_migration_backfills_old_runs_conservatively(monkeypatch, tmp_path):
    """Catches migrated revisions silently omitting enrolled student provenance."""
    client, _database = _client(monkeypatch, tmp_path)
    with client:
        classroom = _classroom(client)
        student = client.post(
            "/students/create",
            json={"name": "Noor", "interests": "maps", "classroom_id": classroom["id"]},
        ).json()["student"]
    engine = create_engine(f"sqlite:///{(tmp_path / 'educomic.db').as_posix()}")
    with engine.connect() as connection:
        head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert head == "0004_review_fixes"
        defaults = connection.execute(text("SELECT generation_defaults FROM settings")).scalar_one()
        assert '"story_length": 12' in defaults
        assert student["id"]

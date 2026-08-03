"""Regression coverage for Phase 4 review invariants."""

import asyncio
import json
from pathlib import Path

import pytest
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


def _script(count: int = 12):
    return {
        "episode_title": "Orbit Lesson",
        "learning_objectives": ["Explain orbits"],
        "panels": [
            {
                "index": index,
                "setting": "Classroom",
                "description": f"Panel {index}",
                "narration": "",
                "dialogue": [{"speaker": "Teacher", "text": "Watch the orbit."}],
                "featured_students": [],
            }
            for index in range(1, count + 1)
        ],
    }


def test_story_options_snapshot_participants_model_and_block_classroom_deletion(monkeypatch, tmp_path):
    """Catches option provider work lacking immutable provenance or a deletion lease."""
    client, database = _client(monkeypatch, tmp_path)
    import services.story_idea as story_idea

    observed = {}

    def generate(classroom, students, outline, *, model):
        observed.update(student_ids=[student["id"] for student in students], model=model)
        observed["delete_during_provider"] = database.execute_deletion("classroom", classroom["id"])
        return [
            {"id": f"idea_{index}", "title": f"Idea {index}", "summary": outline}
            for index in range(1, 4)
        ]

    monkeypatch.setattr(story_idea, "generate_story_ideas", generate)
    with client:
        classroom = _classroom(client)
        student = client.post(
            "/students/create",
            json={"name": "Ari", "interests": "orbits", "classroom_id": classroom["id"]},
        ).json()["student"]
        response = client.post(
            f"/classrooms/{classroom['id']}/chapters/start", json={"lesson_prompt": "Teach orbits"}
        )

    assert response.status_code == 200
    chapter = response.json()["chapter"]
    assert observed == {
        "student_ids": [student["id"]],
        "model": "gpt-5.6-terra",
        "delete_during_provider": False,
    }
    assert chapter["option_student_ids"] == [student["id"]]
    assert chapter["option_provenance_complete"] is True
    assert chapter["option_settings_snapshot"]["openai_model"] == "gpt-5.6-terra"


def test_generation_uses_snapshotted_cast_and_provider_models(monkeypatch, tmp_path):
    """Catches queued generation re-reading enrollment or ignoring snapshotted models."""
    client, database = _client(monkeypatch, tmp_path)
    import services.comic_creation as comic
    import services.generation as generation
    monkeypatch.setattr(generation, "database", database)
    monkeypatch.setattr(generation, "comic_creation", comic)

    with client:
        classroom = _classroom(client)
        first = client.post(
            "/students/create",
            json={"name": "Ari", "interests": "orbits", "classroom_id": classroom["id"]},
        ).json()["student"]
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
        run, _ = database.begin_generation_run(chapter["id"], "idea_1", "snapshot-cast")
        assert database.remove_student_from_classroom(first["id"], classroom["id"])
        client.post(
            "/students/create",
            json={"name": "Bea", "interests": "rockets", "classroom_id": classroom["id"]},
        )

    observed = {}

    def script_provider(**kwargs):
        observed["student_ids"] = [student["id"] for student in kwargs["students"]]
        observed["openai_model"] = kwargs["model"]
        return _script()

    monkeypatch.setattr(comic, "generate_full_script_and_panels", script_provider)
    monkeypatch.setattr(
        generation,
        "submit_bfl_generation",
        lambda *_args, **kwargs: observed.setdefault("bfl_model", kwargs["model"]) or "poll://job",
    )
    monkeypatch.setattr(generation, "poll_bfl_generation", lambda *_args, **_kwargs: "delivery://image")
    monkeypatch.setattr(generation, "download_bfl_image", lambda *_args, **_kwargs: b"fictional")
    monkeypatch.setattr(generation, "validate_image_bytes", lambda _content: None)

    generation.run_generation(run["id"])

    assert observed == {
        "student_ids": [first["id"]],
        "openai_model": "gpt-5.6-terra",
        "bfl_model": "flux-2-pro",
    }
    assert database.get_generation_run(run["id"])["job_state"] == "succeeded"


def test_student_erasure_blocks_active_run_then_clears_affected_option_output(monkeypatch, tmp_path):
    """Catches deletion racing generation or retaining identifying story options."""
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
                "story_ideas": [{"id": "idea_1", "title": "Mina's bridge", "summary": "Mina builds"}],
                "option_student_ids": [student["id"]],
                "option_provenance_complete": True,
                "option_settings_snapshot": {"openai_model": "gpt-5.1"},
                "chosen_idea_id": "idea_1",
                "status": "idea_chosen",
            }
        )
        run, _ = database.begin_generation_run(chapter["id"], "idea_1", "active-erasure")

        blocked = client.delete(f"/students/{student['id']}?confirm=true")
        assert blocked.status_code == 409
        assert database.get_student(student["id"]) is not None

        database.fail_generation_run(run["id"], "cancelled", "fictional-reference")
        erased = client.delete(f"/students/{student['id']}?confirm=true")

    assert erased.status_code == 200
    shell = database.get_chapter(chapter["id"])
    assert shell["story_ideas"] == [
        {
            "id": "idea_1",
            "title": "Classroom story",
            "summary": "Create a new story with the current classroom.",
            "theme": None,
            "preview_status": "failed",
            "preview_url": None,
            "preview_error_reference": None,
        }
    ]
    assert shell["chosen_idea_id"] == "idea_1"
    assert shell["status"] == "idea_chosen"
    assert shell["revision"] == 0


def test_avatar_work_blocks_erasure_and_failed_superseded_cleanup_is_retried(monkeypatch, tmp_path):
    """Catches avatar/delete races and forgotten superseded avatar files."""
    client, database = _client(monkeypatch, tmp_path)
    import services.avatar as avatar

    with client:
        student = client.post(
            "/students/create", json={"name": "Noor", "interests": "maps"}
        ).json()["student"]
    storage = LocalStorage(tmp_path)
    old_path = storage.new_object_path("avatars", student["id"], ".png")
    new_path = storage.new_object_path("avatars", student["id"], ".png")
    for path in (old_path, new_path):
        storage.finalize(storage.stage_bytes(b"fictional", ".png", max_bytes=20), path)
    database.update_student(student["id"], {"avatar_url": media_url(old_path)})
    observed = {}

    async def provider(_prompt, _key, *, model):
        observed["model"] = model
        observed["delete_during_provider"] = database.execute_deletion("student", student["id"])
        return "https://provider.invalid/avatar"

    monkeypatch.setenv("BFL_API_KEY", "fictional-key")
    monkeypatch.setattr(avatar, "_call_black_forest_api", provider)
    monkeypatch.setattr(
        avatar,
        "_upload_avatar_to_storage",
        lambda *_args: asyncio.sleep(0, result=(media_url(new_path), None)),
    )
    original_delete = LocalStorage.delete

    def fail_old(self, object_path):
        if object_path == old_path:
            raise PermissionError("locked")
        return original_delete(self, object_path)

    monkeypatch.setattr(LocalStorage, "delete", fail_old)
    updated = asyncio.run(avatar.generate_avatar(student["id"]))

    assert updated["avatar_url"] == media_url(new_path)
    assert observed == {"model": "flux-2-pro", "delete_during_provider": False}
    assert storage.absolute_path(old_path).is_file()

    monkeypatch.setattr(LocalStorage, "delete", original_delete)
    assert database.execute_deletion("student", student["id"]) is True
    assert not storage.absolute_path(old_path).exists()
    assert not storage.absolute_path(new_path).exists()


def test_finalization_rejects_less_than_the_snapshotted_panel_contract(monkeypatch, tmp_path):
    """Catches direct database finalization publishing a partial revision."""
    client, database = _client(monkeypatch, tmp_path)
    with client:
        classroom = _classroom(client)
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
    run, _ = database.begin_generation_run(chapter["id"], "idea_1", "partial-finalize")
    database.start_generation_run(run["id"])
    storage = LocalStorage(tmp_path)
    object_path = storage.new_object_path("story-images", chapter["id"], ".png")
    storage.finalize(storage.stage_bytes(b"fictional", ".png", max_bytes=20), object_path)

    with pytest.raises(ValueError, match="exact snapshotted panel contract"):
        database.finalize_generation_run(
            run["id"],
            _script(1),
            [{"index": 1, "description": "Partial", "image_object_path": object_path}],
        )

    assert database.get_chapter(chapter["id"])["revision"] == 0


def test_reset_absorbs_outstanding_manifests_and_unblocks_readiness(monkeypatch, tmp_path):
    """Catches reset returning success while an older cleanup manifest remains."""
    client, database = _client(monkeypatch, tmp_path)
    with client:
        classroom = _classroom(client)
    chapter = database.create_chapter(
        {"classroom_id": classroom["id"], "index": 1, "original_prompt": "Forces", "status": "draft"}
    )
    storage = LocalStorage(tmp_path)
    object_path = storage.new_object_path("story-images", chapter["id"], ".png")
    storage.finalize(storage.stage_bytes(b"fictional", ".png", max_bytes=20), object_path)
    database.create_panel(chapter["id"], 1, media_url(object_path))
    original_delete = LocalStorage.delete
    monkeypatch.setattr(LocalStorage, "delete", lambda *_args: (_ for _ in ()).throw(PermissionError("locked")))
    assert database.execute_deletion("chapter", chapter["id"]) is False

    monkeypatch.setattr(LocalStorage, "delete", original_delete)
    assert database.execute_deletion("reset") is True

    from local_runtime import local_readiness_details

    assert local_readiness_details(tmp_path)["cleanup"] is True
    engine = create_engine(f"sqlite:///{(tmp_path / 'educomic.db').as_posix()}")
    assert engine.connect().execute(text("SELECT COUNT(*) FROM deletion_manifests")).scalar_one() == 0


def test_confirmation_and_placeholder_readiness_are_consistent(monkeypatch, tmp_path):
    """Catches unconfirmed enrollment removal and placeholder keys reported as ready."""
    monkeypatch.setenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
    monkeypatch.setenv("BFL_API_KEY", "<BFL_API_KEY>")
    client, _database = _client(monkeypatch, tmp_path)
    with client:
        classroom = _classroom(client)
        student = client.post(
            "/students/create",
            json={"name": "Ari", "interests": "orbits", "classroom_id": classroom["id"]},
        ).json()["student"]
        unconfirmed = client.delete(
            f"/students/{student['id']}/leave-classroom/{classroom['id']}"
        )
        settings = client.get("/settings").json()

    assert unconfirmed.status_code == 400
    assert settings["provider_readiness"] == {"openai": False, "bfl": False}


def test_provider_model_allowlists_reject_unsupported_values(monkeypatch):
    """Catches environment or persisted values selecting arbitrary provider endpoints."""
    import services.generation as generation
    import services.story_idea as story_idea

    with pytest.raises(ValueError, match="OpenAI model"):
        story_idea.generate_story_ideas({}, [], "Outline", model="unsupported-model")
    with pytest.raises(ValueError, match="BFL model"):
        generation.submit_bfl_generation("Panel", model="unsupported-endpoint")


def test_review_migration_marks_legacy_provenance_incomplete_and_repairs_current_script(tmp_path):
    """Catches unsafe enrollment inference, invalid legacy length, or missing fallback script."""
    from test_local_database import _database_url, _upgrade_to
    from database.migrations import upgrade_database

    url = _database_url(tmp_path / "legacy.db")
    _upgrade_to(url, "0002_generation_durability")
    engine = create_engine(url)
    ids = {
        "profile": "00000000-0000-4000-8000-000000000001",
        "classroom": "00000000-0000-4000-8000-000000000002",
        "student": "00000000-0000-4000-8000-000000000003",
        "chapter": "00000000-0000-4000-8000-000000000004",
        "run": "00000000-0000-4000-8000-000000000005",
    }
    script = _script(20)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO local_profiles (id, display_name, role, display_settings) VALUES (:id, 'Teacher', 'teacher', '{}')"),
            {"id": ids["profile"]},
        )
        connection.execute(
            text(
                "INSERT INTO settings (id, profile_id, generation_defaults) "
                "VALUES ('00000000-0000-4000-8000-000000000006', :profile, :defaults)"
            ),
            {"profile": ids["profile"], "defaults": json.dumps({"story_length": 8})},
        )
        connection.execute(
            text(
                "INSERT INTO classrooms (id, owner_id, name, subject, grade_level, story_theme, design_style) "
                "VALUES (:id, :owner, 'Class', 'Science', '6', 'Space', 'comic')"
            ),
            {"id": ids["classroom"], "owner": ids["profile"]},
        )
        connection.execute(
            text("INSERT INTO students (id, name, interests) VALUES (:id, 'Noor', 'maps')"),
            {"id": ids["student"]},
        )
        connection.execute(
            text(
                "INSERT INTO chapters (id, classroom_id, \"index\", original_prompt, story_ideas, "
                "chosen_idea_id, status, revision, story_script) VALUES "
                "(:id, :classroom, 1, 'Maps', :ideas, 'idea_1', 'ready', 1, :script)"
            ),
            {
                "id": ids["chapter"],
                "classroom": ids["classroom"],
                "ideas": json.dumps([{"id": "idea_1", "title": "Noor maps", "summary": "Noor explores"}]),
                "script": json.dumps(script),
            },
        )
        connection.execute(
            text(
                "INSERT INTO generation_runs (id, idempotency_key, chapter_id, selected_idea_id, target_revision, "
                "job_state, stage, artifact_paths) VALUES "
                "(:id, 'legacy-success', :chapter, 'idea_1', 1, 'succeeded', 'ready', '[]')"
            ),
            {"id": ids["run"], "chapter": ids["chapter"]},
        )

    upgrade_database(url)

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0009_avatar_thumbnails"
        defaults = json.loads(connection.execute(text("SELECT generation_defaults FROM settings")).scalar_one())
        run = connection.execute(
            text("SELECT settings_snapshot, script_snapshot FROM generation_runs WHERE id = :id"),
            {"id": ids["run"]},
        ).mappings().one()
        chapter = connection.execute(
            text("SELECT option_provenance_complete FROM chapters WHERE id = :id"),
            {"id": ids["chapter"]},
        ).mappings().one()

    assert defaults["story_length"] == 12
    snapshot = json.loads(run["settings_snapshot"])
    assert snapshot["story_length"] == 20
    assert snapshot["provenance_complete"] is False
    assert ids["student"] not in snapshot["student_ids"]
    assert json.loads(run["script_snapshot"])["panels"] == script["panels"]
    assert chapter["option_provenance_complete"] in (False, 0)

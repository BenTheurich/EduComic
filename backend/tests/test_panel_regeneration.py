"""One-panel correction without risking the readable story."""

import base64
import importlib

import pytest
from fastapi.testclient import TestClient


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _ready_story(monkeypatch, tmp_path):
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    storage_module = importlib.import_module("local_storage")
    runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Fictional Class", "Science", "6", "Space", "comic")
    student = database.create_student("Ada Fiction", "robots", classroom_id=classroom["id"])
    storage = storage_module.LocalStorage(tmp_path)
    avatar_path = storage.new_object_path("avatars", student["id"], ".png")
    storage.finalize(storage.stage_bytes(PNG, ".png", max_bytes=len(PNG)), avatar_path)
    database.replace_student_avatar(student["id"], storage_module.media_url(avatar_path))
    script = {
        "episode_title": "Orbit Lesson",
        "panels": [
            {
                "index": index,
                "setting": "Moon lab",
                "description": f"Fictional panel {index}",
                "narration": "Gravity guides the orbit.",
                "dialogue": [{"speaker": "Ada Fiction", "text": "I can see the orbit."}],
                "featured_students": ["Ada Fiction"],
            }
            for index in range(1, 4)
        ],
    }
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
    paths = []
    for index in range(1, 4):
        path = storage.new_object_path("story-images", chapter["id"], ".png")
        storage.finalize(storage.stage_bytes(PNG, ".png", max_bytes=len(PNG)), path)
        database.create_panel(
            chapter["id"],
            index,
            storage_module.media_url(path),
            revision=1,
            dialogue=script["panels"][index - 1]["dialogue"],
            scene_description=script["panels"][index - 1]["description"],
            speakers=["Ada Fiction"],
        )
        paths.append(path)
    database.update_chapter(
        chapter["id"], {"revision": 1, "status": "ready", "story_script": script}
    )
    return database, storage, chapter["id"], paths


def test_panel_correction_claim_is_idempotent_and_rejects_stale_or_concurrent_work(monkeypatch, tmp_path):
    """Catches duplicate/stale requests spending twice or reserving the wrong revision."""
    database, _storage, chapter_id, _paths = _ready_story(monkeypatch, tmp_path)

    first, created = database.begin_panel_regeneration(chapter_id, 2, 1, "Fix the orbit arrow.", "panel-1")
    retry, retry_created = database.begin_panel_regeneration(chapter_id, 2, 1, "Fix the orbit arrow.", "panel-1")

    assert created is True
    assert retry_created is False
    assert retry["id"] == first["id"]
    assert retry["target_revision"] == 2
    with pytest.raises(database.GenerationConflict, match="already active"):
        database.begin_panel_regeneration(chapter_id, 2, 1, "Try another arrow.", "panel-2")

    database.fail_generation_run(first["id"], "fictional_failure", "safe-reference")
    with pytest.raises(database.GenerationConflict, match="stale"):
        database.begin_panel_regeneration(chapter_id, 2, 0, "Old browser state.", "panel-3")


def test_successful_panel_correction_changes_only_one_panel_and_survives_reload(monkeypatch, tmp_path):
    """Catches a correction rewriting adjacent panels or publishing provider URLs/partial state."""
    database, storage, chapter_id, old_paths = _ready_story(monkeypatch, tmp_path)
    regeneration = importlib.import_module("services.panel_regeneration")
    calls = []
    monkeypatch.setattr(
        regeneration,
        "submit_bfl_generation",
        lambda prompt, aspect_ratio, references, **kwargs: calls.append(
            (prompt, aspect_ratio, references, kwargs)
        ) or "poll://fictional-correction",
    )
    monkeypatch.setattr(regeneration, "poll_bfl_generation", lambda _url: "delivery://fictional-correction")
    monkeypatch.setattr(regeneration, "download_bfl_image", lambda _url: PNG)
    run, _created = database.begin_panel_regeneration(
        chapter_id, 2, 1, "Make the orbit arrow point clockwise.", "success-1"
    )

    regeneration.run_panel_regeneration(run["id"])
    regeneration.run_panel_regeneration(run["id"])

    current = database.get_chapter_with_panels(chapter_id)
    assert current["status"] == "ready"
    assert current["revision"] == 2
    assert [panel["index"] for panel in current["panels"]] == [1, 2, 3]
    assert current["panels"][0]["image"] == f"/media/{old_paths[0]}"
    assert current["panels"][2]["image"] == f"/media/{old_paths[2]}"
    assert current["panels"][1]["image"] != f"/media/{old_paths[1]}"
    assert [panel["scene_description"] for panel in current["panels"]] == [
        "Fictional panel 1", "Fictional panel 2", "Fictional panel 3"
    ]
    assert storage.absolute_path(old_paths[0]).is_file()
    assert not storage.absolute_path(old_paths[1]).exists()
    assert storage.absolute_path(old_paths[2]).is_file()
    assert len(calls) == 1
    prompt, aspect_ratio, references, kwargs = calls[0]
    assert "Fictional panel 2" in prompt
    assert "Make the orbit arrow point clockwise." in prompt
    assert "Fictional panel 1" in prompt and "Fictional panel 3" in prompt
    assert aspect_ratio == "3:2"
    assert references[:3] == [
        f"/media/{old_paths[1]}", f"/media/{old_paths[0]}", f"/media/{old_paths[2]}"
    ]
    assert references[3].startswith("/media/avatars/")
    assert kwargs == {"model": "flux-2-pro"}
    assert database.get_generation_run(run["id"])["job_state"] == "succeeded"

    importlib.import_module("local_runtime").initialize_local_backend(tmp_path)
    reloaded = database.get_chapter_with_panels(chapter_id)
    assert [panel["image"] for panel in reloaded["panels"]] == [
        panel["image"] for panel in current["panels"]
    ]


@pytest.mark.parametrize(
    ("fault", "error_code"),
    [
        ("submit", "bfl_submit_failed"),
        ("poll", "bfl_poll_failed"),
        ("download", "bfl_download_failed"),
        ("validation", "image_invalid"),
        ("finalization", "finalization_failed"),
        ("swap", "database_swap_failed"),
    ],
)
def test_every_panel_correction_failure_keeps_the_old_story_readable(
    monkeypatch, tmp_path, fault, error_code
):
    """Catches any correction boundary replacing readable rows or leaking partial media."""
    database, storage, chapter_id, old_paths = _ready_story(monkeypatch, tmp_path)
    regeneration = importlib.import_module("services.panel_regeneration")
    monkeypatch.setattr(regeneration, "submit_bfl_generation", lambda *_args, **_kwargs: "poll://job")
    monkeypatch.setattr(regeneration, "poll_bfl_generation", lambda _url: "delivery://temporary")
    monkeypatch.setattr(regeneration, "download_bfl_image", lambda _url: PNG)

    def fail(*_args, **_kwargs):
        raise RuntimeError("sensitive fictional provider detail")

    if fault == "submit":
        monkeypatch.setattr(regeneration, "submit_bfl_generation", fail)
    elif fault == "poll":
        monkeypatch.setattr(regeneration, "poll_bfl_generation", fail)
    elif fault == "download":
        monkeypatch.setattr(regeneration, "download_bfl_image", fail)
    elif fault == "validation":
        monkeypatch.setattr(regeneration, "validate_image_bytes", fail)
    elif fault == "finalization":
        monkeypatch.setattr(type(storage), "finalize", fail)
    else:
        monkeypatch.setattr(database, "finalize_panel_regeneration", fail)
    run, _created = database.begin_panel_regeneration(
        chapter_id, 2, 1, "Correct only this fictional panel.", f"fault-{fault}"
    )

    regeneration.run_panel_regeneration(run["id"])

    current = database.get_chapter_with_panels(chapter_id)
    failed = database.get_generation_run(run["id"])
    assert current["status"] == "ready"
    assert current["revision"] == 1
    assert [panel["image"] for panel in current["panels"]] == [f"/media/{path}" for path in old_paths]
    assert all(storage.absolute_path(path).is_file() for path in old_paths)
    assert failed["job_state"] == "failed"
    assert failed["error_code"] == error_code
    assert failed["error_reference"]
    assert "sensitive" not in str(failed)
    assert list((tmp_path / "staging").iterdir()) == []
    assert sorted(path.name for path in (tmp_path / "story-images" / chapter_id).iterdir()) == sorted(
        path.rsplit("/", 1)[1] for path in old_paths
    )


def test_stale_queued_correction_fails_before_provider_spend(monkeypatch, tmp_path):
    """Catches a queued browser request spending after its ready state changed."""
    database, _storage, chapter_id, _old_paths = _ready_story(monkeypatch, tmp_path)
    regeneration = importlib.import_module("services.panel_regeneration")
    provider_calls = []
    monkeypatch.setattr(regeneration, "submit_bfl_generation", lambda *_args, **_kwargs: provider_calls.append(1))
    run, _created = database.begin_panel_regeneration(
        chapter_id, 2, 1, "A correction from the old screen.", "queued-stale"
    )
    database.update_chapter(chapter_id, {"status": "failed"})

    regeneration.run_panel_regeneration(run["id"])

    failed = database.get_generation_run(run["id"])
    assert provider_calls == []
    assert failed["job_state"] == "failed"
    assert failed["error_code"] == "stale"


def test_failed_superseded_file_cleanup_remains_durable(monkeypatch, tmp_path):
    """Catches a successful database swap forgetting a locked superseded file."""
    database, storage, chapter_id, old_paths = _ready_story(monkeypatch, tmp_path)
    regeneration = importlib.import_module("services.panel_regeneration")
    monkeypatch.setattr(regeneration, "submit_bfl_generation", lambda *_args, **_kwargs: "poll://job")
    monkeypatch.setattr(regeneration, "poll_bfl_generation", lambda _url: "delivery://temporary")
    monkeypatch.setattr(regeneration, "download_bfl_image", lambda _url: PNG)
    original_delete = type(storage).delete

    def keep_superseded(self, object_path):
        if object_path == old_paths[1]:
            raise PermissionError("locked")
        return original_delete(self, object_path)

    monkeypatch.setattr(type(storage), "delete", keep_superseded)
    run, _created = database.begin_panel_regeneration(
        chapter_id, 2, 1, "Make the arrow clear.", "cleanup-pending"
    )

    regeneration.run_panel_regeneration(run["id"])

    succeeded = database.get_generation_run(run["id"])
    assert succeeded["job_state"] == "succeeded"
    assert succeeded["cleanup_pending"] is True
    assert succeeded["artifact_paths"] == [old_paths[1]]
    assert storage.absolute_path(old_paths[1]).is_file()
    assert database.get_chapter_with_panels(chapter_id)["panels"][1]["image"] != f"/media/{old_paths[1]}"


def test_panel_correction_api_is_idempotent_and_exposes_truthful_progress(monkeypatch, tmp_path):
    """Catches the HTTP retry launching duplicate paid work or hiding persisted run state."""
    database, _storage, chapter_id, _old_paths = _ready_story(monkeypatch, tmp_path)
    main = importlib.import_module("main")
    background_runs = []
    monkeypatch.setattr(main, "_run_panel_regeneration", background_runs.append)
    payload = {
        "expected_revision": 1,
        "correction": "Make the fictional orbit arrow clockwise.",
        "idempotency_key": "api-panel-1",
    }

    with TestClient(main.app) as client:
        first = client.post(f"/chapters/{chapter_id}/panels/2/regenerate", json=payload)
        retry = client.post(f"/chapters/{chapter_id}/panels/2/regenerate", json=payload)
        status = client.get(f"/panel-regenerations/{first.json()['run_id']}")

    assert first.status_code == 202
    assert first.json()["status"] == "regenerating"
    assert retry.status_code == 202
    assert retry.json()["run_id"] == first.json()["run_id"]
    assert background_runs == [first.json()["run_id"]]
    assert status.status_code == 200
    assert status.json() == {
        "run_id": first.json()["run_id"],
        "chapter_id": chapter_id,
        "panel_number": 2,
        "status": "regenerating",
        "error_code": None,
        "error_reference": None,
        "cleanup_pending": False,
    }


def test_post_publish_cleanup_bookkeeping_failure_never_deletes_the_ready_replacement(monkeypatch, tmp_path):
    """Catches a post-commit exception entering pre-publication compensation and causing data loss."""
    database, storage, chapter_id, _old_paths = _ready_story(monkeypatch, tmp_path)
    regeneration = importlib.import_module("services.panel_regeneration")
    monkeypatch.setattr(regeneration, "submit_bfl_generation", lambda *_args, **_kwargs: "poll://job")
    monkeypatch.setattr(regeneration, "poll_bfl_generation", lambda _url: "delivery://temporary")
    monkeypatch.setattr(regeneration, "download_bfl_image", lambda _url: PNG)
    monkeypatch.setattr(
        database,
        "replace_generation_artifacts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    run, _created = database.begin_panel_regeneration(
        chapter_id, 2, 1, "Make the arrow clear.", "post-publish-failure"
    )

    regeneration.run_panel_regeneration(run["id"])

    current = database.get_chapter_with_panels(chapter_id)
    replacement_path = current["panels"][1]["image"].removeprefix("/media/")
    assert current["status"] == "ready"
    assert current["revision"] == 2
    assert storage.absolute_path(replacement_path).is_file()
    assert database.get_generation_run(run["id"])["job_state"] == "succeeded"


def test_story_worker_cannot_consume_a_panel_correction_lease(monkeypatch, tmp_path):
    """Catches internal task misrouting turning a valid correction into a failed full generation."""
    database, _storage, chapter_id, _old_paths = _ready_story(monkeypatch, tmp_path)
    generation = importlib.import_module("services.generation")
    run, _created = database.begin_panel_regeneration(
        chapter_id, 2, 1, "Make the arrow clear.", "wrong-worker"
    )

    generation.run_generation(run["id"])

    persisted = database.get_generation_run(run["id"])
    assert persisted["job_state"] == "queued"
    assert persisted["error_code"] is None

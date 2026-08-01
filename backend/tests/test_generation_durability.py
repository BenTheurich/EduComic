"""Durable, non-destructive local story generation."""

import base64
import importlib
from pathlib import Path

import pytest


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _script():
    return {
        "episode_title": "Orbit Lesson",
        "learning_objectives": ["Explain orbits"],
        "panels": [
            {
                "index": index,
                "setting": "Classroom",
                "description": f"Fictional panel {index}",
                "narration": "",
                "dialogue": [{"speaker": "Teacher", "text": "Watch the orbit."}],
                "featured_students": [],
            }
            for index in range(1, 9)
        ],
    }


def _ready_chapter(monkeypatch, tmp_path):
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    storage_module = importlib.import_module("local_storage")
    runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Class", "Science", "6", "Space", "comic")
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
    storage = storage_module.LocalStorage(tmp_path)
    staged = storage.stage_bytes(PNG, ".png", max_bytes=len(PNG))
    old_path = storage.new_object_path("story-images", chapter["id"], ".png")
    storage.finalize(staged, old_path)
    database.create_panel(
        chapter["id"],
        1,
        storage_module.media_url(old_path),
        revision=1,
        scene_description="Readable old panel",
    )
    database.update_chapter(
        chapter["id"],
        {"revision": 1, "status": "ready", "story_script": {"episode_title": "Old"}},
    )
    return database, storage, chapter["id"], old_path


def _mock_successful_providers(monkeypatch, generation):
    comic = importlib.import_module("services.comic_creation")
    monkeypatch.setattr(comic, "generate_full_script_and_panels", lambda **_kwargs: _script())
    monkeypatch.setattr(generation, "submit_bfl_generation", lambda *_args, **_kwargs: "poll://job")
    monkeypatch.setattr(generation, "poll_bfl_generation", lambda *_args, **_kwargs: "delivery://temporary")
    monkeypatch.setattr(generation, "download_bfl_image", lambda *_args, **_kwargs: PNG)


def test_generation_claim_is_idempotent_and_rejects_a_conflicting_active_key(monkeypatch, tmp_path):
    """Catches retries duplicating runs or a second active key reserving provider spend."""
    database, _storage, chapter_id, _old_path = _ready_chapter(monkeypatch, tmp_path)

    first, created = database.begin_generation_run(chapter_id, "idea_1", "request-1")
    retry, retry_created = database.begin_generation_run(chapter_id, "idea_1", "request-1")

    assert created is True
    assert retry_created is False
    assert retry["id"] == first["id"]
    assert retry["target_revision"] == 2
    with pytest.raises(database.GenerationConflict):
        database.begin_generation_run(chapter_id, "idea_1", "request-2")


@pytest.mark.parametrize(
    ("fault", "error_code"),
    [
        ("script", "script_invalid"),
        ("submit", "bfl_submit_failed"),
        ("poll", "bfl_poll_failed"),
        ("download", "bfl_download_failed"),
        ("validation", "image_invalid"),
        ("finalization", "finalization_failed"),
        ("swap", "database_swap_failed"),
    ],
)
def test_every_generation_fault_preserves_the_ready_revision(monkeypatch, tmp_path, fault, error_code):
    """Catches any provider/storage/database fault replacing readable rows or media."""
    database, storage, chapter_id, old_path = _ready_chapter(monkeypatch, tmp_path)
    generation = importlib.import_module("services.generation")
    _mock_successful_providers(monkeypatch, generation)
    comic = importlib.import_module("services.comic_creation")

    def fail(*_args, **_kwargs):
        raise RuntimeError("sensitive provider detail")

    if fault == "script":
        monkeypatch.setattr(comic, "generate_full_script_and_panels", fail)
    elif fault == "submit":
        monkeypatch.setattr(generation, "submit_bfl_generation", fail)
    elif fault == "poll":
        monkeypatch.setattr(generation, "poll_bfl_generation", fail)
    elif fault == "download":
        monkeypatch.setattr(generation, "download_bfl_image", fail)
    elif fault == "validation":
        monkeypatch.setattr(generation, "validate_image_bytes", fail)
    elif fault == "finalization":
        monkeypatch.setattr(type(storage), "finalize", fail)
    elif fault == "swap":
        monkeypatch.setattr(database, "finalize_generation_run", fail)

    run, _created = database.begin_generation_run(chapter_id, "idea_1", f"fault-{fault}")
    generation.run_generation(run["id"])

    current = database.get_chapter_with_panels(chapter_id)
    failed = database.get_generation_run(run["id"])
    assert current["status"] == "ready"
    assert current["revision"] == 1
    assert [panel["scene_description"] for panel in current["panels"]] == ["Readable old panel"]
    assert storage.absolute_path(old_path).is_file()
    assert failed["job_state"] == "failed"
    assert failed["error_code"] == error_code
    assert failed["error_reference"]
    assert "sensitive" not in str(failed)
    assert list((Path(tmp_path) / "staging").iterdir()) == []


def test_success_publishes_one_complete_local_revision_and_retires_old_media(monkeypatch, tmp_path):
    """Catches partial panel publication or temporary provider/staging URLs reaching ready rows."""
    database, storage, chapter_id, old_path = _ready_chapter(monkeypatch, tmp_path)
    generation = importlib.import_module("services.generation")
    _mock_successful_providers(monkeypatch, generation)
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "success-1")

    generation.run_generation(run["id"])

    current = database.get_chapter_with_panels(chapter_id)
    succeeded = database.get_generation_run(run["id"])
    assert current["status"] == "ready"
    assert current["revision"] == 2
    assert [panel["index"] for panel in current["panels"]] == list(range(1, 9))
    assert all(panel["image"].startswith("/media/story-images/") for panel in current["panels"])
    assert all("delivery" not in panel["image"] and "staging" not in panel["image"] for panel in current["panels"])
    assert succeeded["job_state"] == "succeeded"
    assert not storage.absolute_path(old_path).exists()


def test_successful_swap_persists_failed_old_media_retirement(monkeypatch, tmp_path):
    """Catches a cleanup fault hiding an unretired old file after successful publication."""
    database, storage, chapter_id, old_path = _ready_chapter(monkeypatch, tmp_path)
    generation = importlib.import_module("services.generation")
    runtime = importlib.import_module("local_runtime")
    _mock_successful_providers(monkeypatch, generation)
    original_delete = type(storage).delete

    def fail_old_media(self, object_path):
        if object_path == old_path:
            raise PermissionError("locked")
        return original_delete(self, object_path)

    monkeypatch.setattr(type(storage), "delete", fail_old_media)
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "retirement-retry")

    generation.run_generation(run["id"])

    current = database.get_chapter_with_panels(chapter_id)
    assert current["status"] == "ready"
    assert current["revision"] == 2
    assert database.get_generation_run(run["id"])["artifact_paths"] == [old_path]
    assert storage.absolute_path(old_path).is_file()
    assert runtime.local_readiness_details(tmp_path)["cleanup"] is False
    with pytest.raises(RuntimeError, match="cleanup"):
        runtime.initialize_local_backend(tmp_path)

    monkeypatch.setattr(type(storage), "delete", original_delete)
    runtime.initialize_local_backend(tmp_path)

    assert not storage.absolute_path(old_path).exists()
    assert database.get_generation_run(run["id"])["artifact_paths"] == []
    assert database.get_chapter_with_panels(chapter_id)["revision"] == 2


def test_finalization_crash_after_replace_cleans_the_unpublished_file(monkeypatch, tmp_path):
    """Catches the replace-to-manifest crash window orphaning unpublished story media."""
    database, storage, chapter_id, old_path = _ready_chapter(monkeypatch, tmp_path)
    generation = importlib.import_module("services.generation")
    _mock_successful_providers(monkeypatch, generation)
    original_finalize = type(storage).finalize

    def replace_then_crash(self, staged_path, object_path):
        original_finalize(self, staged_path, object_path)
        raise RuntimeError("simulated interruption after replace")

    monkeypatch.setattr(type(storage), "finalize", replace_then_crash)
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "replace-crash")

    generation.run_generation(run["id"])

    story_files = list((Path(tmp_path) / "story-images" / chapter_id).iterdir())
    assert story_files == [storage.absolute_path(old_path)]
    assert database.get_generation_run(run["id"])["error_code"] == "finalization_failed"


def test_database_swap_rejects_missing_or_traversing_media(monkeypatch, tmp_path):
    """Catches a ready transaction bypassing the local storage boundary."""
    database, _storage, chapter_id, _old_path = _ready_chapter(monkeypatch, tmp_path)
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "unsafe-media")
    database.start_generation_run(run["id"])

    with pytest.raises(ValueError, match="durable local story media"):
        database.finalize_generation_run(
            run["id"],
            {"episode_title": "Unsafe"},
            [
                {
                    "index": 1,
                    "description": "Unsafe",
                    "image_object_path": f"story-images/{chapter_id}/../outside.png",
                }
            ],
        )

    assert database.get_chapter_with_panels(chapter_id)["revision"] == 1


def test_startup_fails_interrupted_runs_and_cleans_only_their_new_artifacts(monkeypatch, tmp_path):
    """Catches restart recovery losing the previous revision or leaving abandoned files."""
    database, storage, chapter_id, old_path = _ready_chapter(monkeypatch, tmp_path)
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "interrupted-1")
    staged = storage.stage_bytes(PNG, ".png", max_bytes=len(PNG))
    abandoned = storage.new_object_path("story-images", chapter_id, ".png")
    storage.finalize(staged, abandoned)
    database.record_generation_artifact(run["id"], abandoned)

    importlib.import_module("local_runtime").initialize_local_backend(tmp_path)

    current = database.get_chapter_with_panels(chapter_id)
    failed = database.get_generation_run(run["id"])
    assert current["status"] == "ready"
    assert current["revision"] == 1
    assert failed["job_state"] == "failed"
    assert failed["error_code"] == "interrupted"
    assert storage.absolute_path(old_path).is_file()
    assert not storage.absolute_path(abandoned).exists()


def test_failed_cleanup_remains_pending_and_retries_on_next_startup(monkeypatch, tmp_path):
    """Catches a terminal run losing its cleanup manifest after one filesystem failure."""
    database, storage, chapter_id, old_path = _ready_chapter(monkeypatch, tmp_path)
    runtime = importlib.import_module("local_runtime")
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "cleanup-retry")
    staged = storage.stage_bytes(PNG, ".png", max_bytes=len(PNG))
    abandoned = storage.new_object_path("story-images", chapter_id, ".png")
    storage.finalize(staged, abandoned)
    database.record_generation_artifact(run["id"], abandoned)
    database.fail_generation_run(run["id"], "interrupted", "safe-reference")
    original_delete = type(storage).delete

    def fail_abandoned_once(self, object_path):
        if object_path == abandoned:
            raise PermissionError("locked")
        return original_delete(self, object_path)

    monkeypatch.setattr(type(storage), "delete", fail_abandoned_once)
    with pytest.raises(RuntimeError, match="cleanup"):
        runtime.initialize_local_backend(tmp_path)

    assert storage.absolute_path(abandoned).is_file()
    assert database.get_generation_run(run["id"])["artifact_paths"] == [abandoned]
    assert runtime.local_readiness_details(tmp_path)["cleanup"] is False
    current = database.get_chapter_with_panels(chapter_id)
    assert current["revision"] == 1
    assert storage.absolute_path(old_path).is_file()

    monkeypatch.setattr(type(storage), "delete", original_delete)
    runtime.initialize_local_backend(tmp_path)

    assert not storage.absolute_path(abandoned).exists()
    assert database.get_generation_run(run["id"])["artifact_paths"] == []
    assert runtime.local_readiness_details(tmp_path)["cleanup"] is True

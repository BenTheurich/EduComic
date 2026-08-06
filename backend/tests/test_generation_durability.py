"""Durable, non-destructive local story generation."""

import base64
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


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
            for index in range(1, 13)
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


@pytest.mark.parametrize(
    ("status", "error_code"),
    [
        ("Request Moderated", "bfl_request_moderated"),
        ("Content Moderated", "bfl_content_moderated"),
    ],
)
def test_moderation_failure_keeps_script_and_blocked_panel_diagnostics(
    monkeypatch, tmp_path, status, error_code
):
    """Catches one moderated panel erasing the evidence needed before another paid attempt."""
    database, _storage, chapter_id, _old_path = _ready_chapter(monkeypatch, tmp_path)
    generation = importlib.import_module("services.generation")
    _mock_successful_providers(monkeypatch, generation)
    monkeypatch.setattr(
        generation,
        "poll_bfl_generation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(generation.BFLModerationError(status)),
    )
    run, _created = database.begin_generation_run(chapter_id, "idea_1", f"moderated-{status}")

    generation.run_generation(run["id"])

    failed = database.get_generation_run(run["id"])
    chapter = database.get_chapter_with_panels(chapter_id)
    assert failed["error_code"] == error_code
    assert failed["panel_number"] == 1
    assert failed["script_snapshot"] == _script()
    assert chapter["generation_failure"] == {
        "run_id": run["id"],
        "error_code": error_code,
        "error_reference": failed["error_reference"],
        "panel_number": 1,
        "completed_panels": 0,
        "expected_panels": 12,
        "reported_bfl_cost": 0.0,
        "resumable": True,
    }


def test_success_publishes_one_complete_local_revision_and_preserves_provenance_history(monkeypatch, tmp_path):
    """Catches partial publication or loss of history needed for later erasure."""
    database, storage, chapter_id, old_path = _ready_chapter(monkeypatch, tmp_path)
    generation = importlib.import_module("services.generation")
    _mock_successful_providers(monkeypatch, generation)
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "success-1")

    generation.run_generation(run["id"])

    current = database.get_chapter_with_panels(chapter_id)
    succeeded = database.get_generation_run(run["id"])
    assert current["status"] == "ready"
    assert current["revision"] == 2
    assert [panel["index"] for panel in current["panels"]] == list(range(1, 13))
    assert all(panel["image"].startswith("/media/story-images/") for panel in current["panels"])
    assert all("delivery" not in panel["image"] and "staging" not in panel["image"] for panel in current["panels"])
    assert succeeded["job_state"] == "succeeded"
    assert storage.absolute_path(old_path).exists()


def test_snapshotted_panel_review_setting_reviews_each_selected_panel_once(monkeypatch, tmp_path):
    """Catches the visible review setting being decorative in the active durable path."""
    database, _storage, chapter_id, _old_path = _ready_chapter(monkeypatch, tmp_path)
    database.update_settings({"automatic_panel_review": True, "panel_review_attempt_cap": 2})
    generation = importlib.import_module("services.generation")
    _mock_successful_providers(monkeypatch, generation)
    reviews = []
    monkeypatch.setattr(
        generation,
        "review_panel_image",
        lambda *_args, **_kwargs: reviews.append(1) or {
            "score": 10,
            "visible_text": [{"kind": "dialogue", "text": "Watch the orbit."}],
            "dimensions": {
                "bubble_ownership": True,
                "reference_identity_continuity": True,
                "requested_action": True,
                "layout_readability": True,
            },
            "issues": [],
            "suggested_fix_prompt": "",
            "notes": "",
        },
        raising=False,
    )
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "review-enabled")

    generation.run_generation(run["id"])

    assert len(reviews) == 12
    assert database.get_generation_run(run["id"])["job_state"] == "succeeded"


def test_generation_orders_featured_avatars_before_previous_style_reference():
    """Catches a previous panel overriding the current cast's identity references."""
    generation = importlib.import_module("services.generation")

    references = generation.ordered_panel_references(
        "/media/story-images/previous.png",
        {"featured_students": ["Ada"]},
        [
            {"name": "Ada", "avatar_url": "/media/avatars/ada.png"},
            {"name": "Bea", "avatar_url": "/media/avatars/bea.png"},
        ],
    )

    assert references == [
        {"role": "current avatar for Ada", "url": "/media/avatars/ada.png"},
        {"role": "previous accepted panel for style only", "url": "/media/story-images/previous.png"},
    ]


def test_generation_drops_previous_panel_before_any_required_avatar():
    """Catches the eight-reference limit silently removing a current cast member."""
    generation = importlib.import_module("services.generation")
    students = [
        {"name": f"Student {index}", "avatar_url": f"/media/avatars/{index}.png"}
        for index in range(1, 9)
    ]

    references = generation.ordered_panel_references(
        "/media/story-images/previous.png",
        {"featured_students": [student["name"] for student in students]},
        students,
    )

    assert [reference["url"] for reference in references] == [
        f"/media/avatars/{index}.png" for index in range(1, 9)
    ]


def test_every_panel_retry_prompt_keeps_reference_roles():
    """Catches paid retries retaining images but dropping their semantic roles."""
    generation = importlib.import_module("services.generation")
    references = [
        {"role": "current avatar for Ada", "url": "/media/avatars/ada.png"},
        {"role": "previous accepted panel for style only", "url": "/media/story-images/previous.png"},
    ]

    retry = generation.build_panel_attempt_prompt(
        "Base panel prompt.", references, "Correct the misspelling."
    )

    assert retry == (
        "Base panel prompt. Reference image order: 1: current avatar for Ada; "
        "2: previous accepted panel for style only. The previous accepted panel is only a style reference; "
        "do not copy its cast, character proportions, poses, composition, speech bubbles, or text. "
        "Correction: Correct the misspelling."
    )


def test_successful_swap_does_not_retire_historical_media(monkeypatch, tmp_path):
    """Catches ordinary regeneration deleting history required for selective erasure."""
    database, storage, chapter_id, old_path = _ready_chapter(monkeypatch, tmp_path)
    generation = importlib.import_module("services.generation")
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
    assert database.get_generation_run(run["id"])["artifact_paths"] == []
    assert storage.absolute_path(old_path).is_file()
    monkeypatch.setattr(type(storage), "delete", original_delete)


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
            _script(),
            [
                {
                    "index": index,
                    "description": "Unsafe",
                    "image_object_path": f"story-images/{chapter_id}/../outside.png",
                }
                for index in range(1, 13)
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


def test_interrupted_poll_resumes_the_same_bfl_job_and_keeps_completed_panels(monkeypatch, tmp_path):
    """Catches a transient poll failure deleting paid panels or buying the current panel twice."""
    database, _storage, chapter_id, _old_path = _ready_chapter(monkeypatch, tmp_path)
    generation = importlib.import_module("services.generation")
    comic = importlib.import_module("services.comic_creation")
    script_calls = []
    submits = []
    interrupted = True

    monkeypatch.setattr(
        comic,
        "generate_full_script_and_panels",
        lambda **_kwargs: script_calls.append(1) or _script(),
    )

    def submit(*_args, **_kwargs):
        panel_number = len(submits) + 1
        job = generation.BFLJob(f"job-{panel_number}", f"poll://{panel_number}", 1.5)
        submits.append(job)
        return job

    def poll(polling_url, **_kwargs):
        nonlocal interrupted
        if polling_url == "poll://3" and interrupted:
            interrupted = False
            raise RuntimeError("fictional connection loss")
        return f"delivery://{polling_url.rsplit('/', 1)[-1]}"

    monkeypatch.setattr(generation, "submit_bfl_generation", submit)
    monkeypatch.setattr(generation, "poll_bfl_generation", poll)
    monkeypatch.setattr(generation, "download_bfl_image", lambda *_args, **_kwargs: PNG)
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "resume-same-job")

    generation.run_generation(run["id"])

    failed = database.get_generation_run(run["id"])
    assert failed["error_code"] == "bfl_poll_failed"
    assert [panel["index"] for panel in failed["checkpoint_panels"]] == [1, 2]
    assert failed["provider_job"]["polling_url"] == "poll://3"
    assert failed["reported_bfl_cost"] == 4.5

    database.resume_generation_run(run["id"])
    generation.run_generation(run["id"])

    completed = database.get_generation_run(run["id"])
    assert completed["job_state"] == "succeeded"
    assert len(submits) == 12
    assert len(script_calls) == 1
    assert database.get_chapter_with_panels(chapter_id)["revision"] == 2


def test_moderation_resume_requires_explicit_requeue_and_resubmits_only_the_blocked_panel(
    monkeypatch, tmp_path
):
    """Catches moderation auto-retrying or restarting panels that already completed."""
    database, _storage, chapter_id, _old_path = _ready_chapter(monkeypatch, tmp_path)
    generation = importlib.import_module("services.generation")
    comic = importlib.import_module("services.comic_creation")
    monkeypatch.setattr(comic, "generate_full_script_and_panels", lambda **_kwargs: _script())
    submits = []
    moderated = True

    def submit(*_args, **_kwargs):
        job = generation.BFLJob(f"job-{len(submits) + 1}", f"poll://{len(submits) + 1}", 1.0)
        submits.append(job)
        return job

    def poll(polling_url, **_kwargs):
        nonlocal moderated
        if polling_url == "poll://3" and moderated:
            moderated = False
            raise generation.BFLModerationError("Request Moderated")
        return f"delivery://{polling_url.rsplit('/', 1)[-1]}"

    monkeypatch.setattr(generation, "submit_bfl_generation", submit)
    monkeypatch.setattr(generation, "poll_bfl_generation", poll)
    monkeypatch.setattr(generation, "download_bfl_image", lambda *_args, **_kwargs: PNG)
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "resume-moderation")

    generation.run_generation(run["id"])
    assert len(submits) == 3
    assert database.get_generation_run(run["id"])["job_state"] == "failed"

    database.resume_generation_run(run["id"])
    generation.run_generation(run["id"])

    assert database.get_generation_run(run["id"])["job_state"] == "succeeded"
    assert len(submits) == 13


def test_generation_resume_and_discard_api_are_explicit_idempotent_actions(monkeypatch, tmp_path):
    """Catches duplicate resume workers or discard leaving checkpoint media behind."""
    database, storage, chapter_id, _old_path = _ready_chapter(monkeypatch, tmp_path)
    main = importlib.import_module("main")
    background_runs = []
    monkeypatch.setattr(main, "_run_story_generation", background_runs.append)
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "resume-api")
    database.start_generation_run(run["id"])
    database.record_generation_script(run["id"], _script())
    staged = storage.stage_bytes(PNG, ".png", max_bytes=len(PNG))
    checkpoint = storage.new_object_path("story-images", chapter_id, ".png")
    database.record_generation_artifact(run["id"], checkpoint)
    storage.finalize(staged, checkpoint)
    database.record_generation_checkpoint(run["id"], 1, checkpoint)
    database.fail_generation_run(run["id"], "bfl_request_moderated", "safe-reference")

    with TestClient(main.app) as client:
        first = client.post(f"/generation-runs/{run['id']}/resume")
        retry = client.post(f"/generation-runs/{run['id']}/resume")

    assert first.status_code == 202
    assert retry.status_code == 202
    assert first.json()["run_id"] == retry.json()["run_id"] == run["id"]
    assert background_runs == [run["id"]]

    database.fail_generation_run(run["id"], "bfl_request_moderated", "second-reference")
    with TestClient(main.app) as client:
        missing_confirmation = client.post(f"/generation-runs/{run['id']}/discard")
        discarded = client.post(f"/generation-runs/{run['id']}/discard?confirm=true")

    assert missing_confirmation.status_code == 400
    assert discarded.status_code == 200
    assert not storage.absolute_path(checkpoint).exists()
    assert database.get_generation_run(run["id"])["checkpoint_panels"] == []


def test_chapter_deletion_removes_failed_generation_checkpoints(monkeypatch, tmp_path):
    database, storage, chapter_id, _old_path = _ready_chapter(monkeypatch, tmp_path)
    run, _created = database.begin_generation_run(chapter_id, "idea_1", "checkpoint-delete")
    database.start_generation_run(run["id"])
    database.record_generation_script(run["id"], _script())
    checkpoint = storage.new_object_path("story-images", chapter_id, ".png")
    storage.finalize(storage.stage_bytes(PNG, ".png", max_bytes=len(PNG)), checkpoint)
    database.record_generation_checkpoint(run["id"], 1, checkpoint)
    database.fail_generation_run(run["id"], "bfl_request_moderated", "safe-reference")

    assert database.execute_deletion("chapter", chapter_id) is True
    assert not storage.absolute_path(checkpoint).exists()

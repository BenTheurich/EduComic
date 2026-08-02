"""Durable story-preview and canonical metadata behavior."""

import importlib
import base64

import pytest
from fastapi.testclient import TestClient


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_selected_idea_exposes_canonical_metadata_and_only_local_preview_urls(monkeypatch, tmp_path):
    """Catches raw object paths leaking or lesson prompts replacing selected-idea copy."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    storage_module = importlib.import_module("local_storage")
    runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Class", "Science", "6", "Space", "comic")
    storage = storage_module.LocalStorage(tmp_path)
    preview_path = storage.new_object_path("story-images", classroom["id"], ".png")
    storage.finalize(storage.stage_bytes(b"preview", ".png", max_bytes=100), preview_path)

    chapter = database.create_chapter(
        {
            "classroom_id": classroom["id"],
            "index": 1,
            "original_prompt": "Teacher-only lesson provenance",
            "story_ideas": [
                {
                    "id": "idea_1",
                    "title": "The Orbit Workshop",
                    "summary": "Students repair a satellite while learning how orbits work.",
                    "theme": "Space",
                    "preview_status": "ready",
                    "preview_object_path": preview_path,
                }
            ],
            "chosen_idea_id": "idea_1",
            "status": "idea_chosen",
        }
    )

    assert chapter["story_title"] == "The Orbit Workshop"
    assert chapter["story_description"] == "Students repair a satellite while learning how orbits work."
    assert chapter["thumbnail_url"].startswith("/media/story-images/")
    assert chapter["story_ideas"][0]["preview_url"] == chapter["thumbnail_url"]
    assert "preview_object_path" not in chapter["story_ideas"][0]


def test_three_server_owned_preview_jobs_publish_durable_local_images(monkeypatch, tmp_path):
    """Catches browser URLs, expiring provider URLs, or fewer than three durable previews."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    generation = importlib.import_module("services.generation")
    storage_module = importlib.import_module("local_storage")
    runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Class", "Science", "6", "Space", "comic")
    chapter = database.begin_story_options(classroom["id"], 1, "Teach orbits")
    chapter = database.complete_story_options(
        chapter["id"],
        [
            {
                "id": f"idea_{index}",
                "title": f"Orbit idea {index}",
                "summary": f"Students investigate orbit {index}.",
                "theme": "Space",
                "preview_status": "pending",
            }
            for index in range(1, 4)
        ],
    )
    jobs = database.begin_story_previews(chapter["id"])
    submitted = []
    monkeypatch.setattr(
        generation,
        "submit_bfl_generation",
        lambda prompt, *_args, **_kwargs: submitted.append(prompt) or "https://provider.test/poll",
    )
    monkeypatch.setattr(
        generation,
        "poll_bfl_generation",
        lambda *_args, **_kwargs: "https://provider.test/delivery.png",
    )
    monkeypatch.setattr(generation, "download_bfl_image", lambda *_args, **_kwargs: PNG)

    generation.run_story_previews(jobs)

    current = database.get_chapter(chapter["id"])
    assert len(jobs) == len(submitted) == 3
    assert all(idea["preview_status"] == "ready" for idea in current["story_ideas"])
    assert all(idea["preview_url"].startswith("/media/story-images/") for idea in current["story_ideas"])
    storage = storage_module.LocalStorage(tmp_path)
    assert all(
        storage.absolute_path(storage.object_path_from_url(idea["preview_url"])).is_file()
        for idea in current["story_ideas"]
    )
    assert all("provider.test" not in idea["preview_url"] for idea in current["story_ideas"])


def test_story_option_route_queues_three_preview_states_without_accepting_urls(monkeypatch, tmp_path):
    """Catches the browser becoming responsible for provider or thumbnail URLs."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    main = importlib.import_module("main")
    story_idea = importlib.import_module("services.story_idea")
    runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Class", "Science", "6", "Space", "comic")
    queued = []
    monkeypatch.setattr(
        story_idea,
        "generate_story_ideas",
        lambda *_args, **_kwargs: [
            {"title": f"Idea {index}", "summary": f"Summary {index}"}
            for index in range(1, 4)
        ],
    )
    monkeypatch.setattr(
        main,
        "run_story_previews_for_chapter",
        lambda chapter_id: queued.append(chapter_id),
        raising=False,
    )

    with TestClient(main.app) as client:
        response = client.post(
            f"/classrooms/{classroom['id']}/chapters/start",
            json={"lesson_prompt": "Teach orbits"},
        )

    assert response.status_code == 200
    chapter = response.json()["chapter"]
    assert [idea["preview_status"] for idea in chapter["story_ideas"]] == ["pending"] * 3
    assert [idea["preview_url"] for idea in chapter["story_ideas"]] == [None] * 3
    assert queued == [chapter["id"]]


def test_preview_retry_rejects_caller_urls_and_queues_only_the_failed_idea(monkeypatch, tmp_path):
    """Catches retry accepting a delivery URL or spending again on ready previews."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    main = importlib.import_module("main")
    runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Class", "Science", "6", "Space", "comic")
    chapter = database.begin_story_options(classroom["id"], 1, "Teach orbits")
    chapter = database.complete_story_options(
        chapter["id"],
        [
            {
                "id": f"idea_{index}",
                "title": f"Idea {index}",
                "summary": f"Summary {index}",
                "theme": "Space",
                "preview_status": "failed" if index == 2 else "ready",
            }
            for index in range(1, 4)
        ],
    )
    queued = []
    monkeypatch.setattr(main, "run_story_previews", lambda jobs: queued.extend(jobs))

    with TestClient(main.app) as client:
        rejected = client.post(
            f"/chapters/{chapter['id']}/story-ideas/idea_2/preview/retry",
            json={"thumbnail_url": "http://127.0.0.1/private"},
        )
        accepted = client.post(
            f"/chapters/{chapter['id']}/story-ideas/idea_2/preview/retry",
            json={},
        )

    assert rejected.status_code == 422
    assert accepted.status_code == 202
    assert [job["idea_id"] for job in queued] == ["idea_2"]
    assert accepted.json()["chapter"]["story_ideas"][1]["preview_status"] == "generating"


def test_generating_chapter_exposes_only_durable_temporary_panel_previews(monkeypatch, tmp_path):
    """Catches atomic final publication hiding already durable in-progress panel images."""
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
    run, _created = database.begin_generation_run(chapter["id"], "idea_1", "preview-panels")
    database.start_generation_run(run["id"])
    storage = storage_module.LocalStorage(tmp_path)
    first_path = storage.new_object_path("story-images", chapter["id"], ".png")
    storage.finalize(storage.stage_bytes(PNG, ".png", max_bytes=len(PNG)), first_path)
    database.record_generation_artifact(run["id"], first_path)

    current = database.get_chapter_with_panels(chapter["id"])

    assert current["panels"] == []
    assert current["temporary_panel_previews"] == [
        {"index": 1, "image": storage_module.media_url(first_path)}
    ]


def test_chapter_deletion_removes_all_story_idea_preview_files(monkeypatch, tmp_path):
    """Catches preview media becoming an untracked orphan after chapter deletion."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    storage_module = importlib.import_module("local_storage")
    runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Class", "Science", "6", "Space", "comic")
    storage = storage_module.LocalStorage(tmp_path)
    preview_paths = []
    for _index in range(3):
        object_path = storage.new_object_path("story-images", classroom["id"], ".png")
        storage.finalize(storage.stage_bytes(PNG, ".png", max_bytes=len(PNG)), object_path)
        preview_paths.append(object_path)
    chapter = database.create_chapter(
        {
            "classroom_id": classroom["id"],
            "index": 1,
            "original_prompt": "Teach orbits",
            "story_ideas": [
                {
                    "id": f"idea_{index}",
                    "title": f"Idea {index}",
                    "summary": f"Summary {index}",
                    "preview_status": "ready",
                    "preview_object_path": preview_paths[index - 1],
                }
                for index in range(1, 4)
            ],
            "status": "options_generated",
        }
    )

    assert database.execute_deletion("chapter", chapter["id"]) is True
    assert database.get_chapter(chapter["id"]) is None
    assert all(not storage.absolute_path(path).exists() for path in preview_paths)


@pytest.mark.parametrize("target_kind", ["chapter", "classroom"])
def test_active_preview_work_blocks_parent_deletion(monkeypatch, tmp_path, target_kind):
    """Catches deletion racing a paid preview into an orphaned local file."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Class", "Science", "6", "Space", "comic")
    chapter = database.begin_story_options(classroom["id"], 1, "Teach orbits")
    chapter = database.complete_story_options(
        chapter["id"],
        [
            {
                "id": f"idea_{index}",
                "title": f"Idea {index}",
                "summary": f"Summary {index}",
                "preview_status": "failed",
            }
            for index in range(1, 4)
        ],
    )
    jobs = database.begin_story_previews(chapter["id"])
    target_id = chapter["id"] if target_kind == "chapter" else classroom["id"]

    assert database.execute_deletion(target_kind, target_id) is False
    for job in jobs:
        database.fail_story_preview(chapter["id"], job["idea_id"], "test-reference")
    assert database.execute_deletion(target_kind, target_id) is True


def test_restart_marks_unfinished_preview_states_failed_and_retryable(monkeypatch, tmp_path):
    """Catches a local restart leaving previews in a permanent fake-loading state."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Class", "Science", "6", "Space", "comic")
    chapter = database.begin_story_options(classroom["id"], 1, "Teach orbits")
    chapter = database.complete_story_options(
        chapter["id"],
        [
            {
                "id": f"idea_{index}",
                "title": f"Idea {index}",
                "summary": f"Summary {index}",
                "preview_status": "pending",
            }
            for index in range(1, 4)
        ],
    )
    database.begin_story_previews(chapter["id"], ["idea_1", "idea_2"])

    database.clear_interrupted_active_work()

    restarted = database.get_chapter(chapter["id"])
    assert [idea["preview_status"] for idea in restarted["story_ideas"]] == ["failed"] * 3
    assert all(idea["preview_error_reference"] for idea in restarted["story_ideas"])
    assert len(database.begin_story_previews(chapter["id"])) == 3

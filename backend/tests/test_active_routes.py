"""Public story workflow route regressions."""

import importlib
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest


@pytest.mark.asyncio
async def test_active_story_workflow_starts_chooses_commits_and_reads(monkeypatch):
    """Catches any active story step being removed or routed through a stale endpoint."""
    database = importlib.import_module("database.database")
    main = importlib.import_module("main")
    story_idea = importlib.import_module("services.story_idea")
    classroom_id = uuid4()
    chapter_id = uuid4()
    chapters = {}
    committed = []

    def create_chapter(data):
        chapter = {"id": str(chapter_id), **data}
        chapters[str(chapter_id)] = chapter
        return chapter

    def update_chapter(chapter, data):
        chapters[chapter].update(data)
        return chapters[chapter]

    monkeypatch.setattr(database, "get_classroom", lambda _id: {"id": str(classroom_id), "story_theme": "space"})
    monkeypatch.setattr(database, "get_students_by_classroom", lambda _id: [])
    monkeypatch.setattr(database, "get_chapters_by_classroom", lambda _id: [])
    monkeypatch.setattr(database, "get_chapter", lambda chapter: chapters.get(chapter))
    monkeypatch.setattr(
        database,
        "get_chapter_with_panels",
        lambda chapter: {**chapters[chapter], "panels": []},
    )
    monkeypatch.setattr(database, "create_chapter", create_chapter)
    monkeypatch.setattr(database, "update_chapter", update_chapter)
    monkeypatch.setattr(
        database,
        "choose_chapter_idea",
        lambda chapter, idea: update_chapter(
            chapter, {"chosen_idea_id": idea, "status": "idea_chosen"}
        ),
        raising=False,
    )
    monkeypatch.setattr(
        database,
        "claim_chapter_generation",
        lambda chapter, idea: {**chapters[chapter], "status": "generating", "target_revision": 1},
        raising=False,
    )
    monkeypatch.setattr(
        story_idea,
        "generate_story_ideas",
        lambda *_args: [{"title": f"Idea {index}", "summary": "Summary"} for index in range(1, 4)],
    )
    monkeypatch.setattr(main, "commit_story_choice", lambda chapter, idea: committed.append((chapter, idea)))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        started = await client.post(
            f"/classrooms/{classroom_id}/chapters/start",
            json={"lesson_prompt": "Newton's laws"},
        )
        chosen = await client.post(
            f"/chapters/{chapter_id}/choose-idea", json={"idea_id": "idea_1"}
        )
        committed_response = await client.post(
            "/chapters/commit",
            json={"chapter_id": str(chapter_id), "chosen_idea_id": "idea_1"},
        )
        read = await client.get(f"/chapters/{chapter_id}")

    assert started.status_code == 200
    assert [idea["id"] for idea in started.json()["chapter"]["story_ideas"]] == [
        "idea_1",
        "idea_2",
        "idea_3",
    ]
    assert chosen.json()["chapter"]["status"] == "idea_chosen"
    assert committed_response.json()["status"] == "generating"
    assert read.json()["chapter"] == {**chapters[str(chapter_id)], "panels": []}
    assert committed == [(str(chapter_id), "idea_1")]


@pytest.mark.asyncio
async def test_repeated_commit_is_atomically_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    database = importlib.import_module("database.database")
    main = importlib.import_module("main")
    importlib.import_module("local_runtime").initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Class", "Math", "6", "Space", "cartoon")
    chapter = database.create_chapter(
        {
            "classroom_id": classroom["id"],
            "index": 1,
            "original_prompt": "Teach forces",
            "story_ideas": [{"id": "idea_1", "title": "Rocket", "summary": "Learn"}],
            "chosen_idea_id": "idea_1",
            "status": "idea_chosen",
        }
    )
    monkeypatch.setattr(main, "commit_story_choice", lambda *_args: None)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
        first = await client.post(
            "/chapters/commit", json={"chapter_id": chapter["id"], "chosen_idea_id": "idea_1"}
        )
        second = await client.post(
            "/chapters/commit", json={"chapter_id": chapter["id"], "chosen_idea_id": "idea_1"}
        )

    assert first.status_code == 200
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_choose_idea_cannot_reset_a_generating_chapter(monkeypatch, tmp_path):
    """Catches idea selection reopening a chapter for a second concurrent job."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    database = importlib.import_module("database.database")
    main = importlib.import_module("main")
    importlib.import_module("local_runtime").initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Class", "Math", "6", "Space", "cartoon")
    chapter = database.create_chapter(
        {
            "classroom_id": classroom["id"],
            "index": 1,
            "original_prompt": "Teach forces",
            "story_ideas": [{"id": "idea_1", "title": "Rocket", "summary": "Learn"}],
            "chosen_idea_id": "idea_1",
            "status": "generating",
        }
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
        response = await client.post(
            f"/chapters/{chapter['id']}/choose-idea", json={"idea_id": "idea_1"}
        )

    assert response.status_code == 409
    unchanged = database.get_chapter(chapter["id"])
    assert unchanged["status"] == "generating"
    assert unchanged["chosen_idea_id"] == "idea_1"


@pytest.mark.asyncio
async def test_choose_idea_loses_truthfully_when_commit_claim_wins_after_read(monkeypatch, tmp_path):
    """Catches a stale route read bypassing the database transition guard."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    database = importlib.import_module("database.database")
    main = importlib.import_module("main")
    importlib.import_module("local_runtime").initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Class", "Math", "6", "Space", "cartoon")
    chapter = database.create_chapter(
        {
            "classroom_id": classroom["id"],
            "index": 1,
            "original_prompt": "Teach forces",
            "story_ideas": [{"id": "idea_1", "title": "Rocket", "summary": "Learn"}],
            "chosen_idea_id": "idea_1",
            "status": "idea_chosen",
        }
    )
    original_get_chapter = database.get_chapter
    claimed = False

    def stale_read_then_claim(chapter_id):
        nonlocal claimed
        stale = original_get_chapter(chapter_id)
        if not claimed:
            claimed = True
            assert database.claim_chapter_generation(chapter_id, "idea_1") is not None
        return stale

    monkeypatch.setattr(database, "get_chapter", stale_read_then_claim)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
        response = await client.post(
            f"/chapters/{chapter['id']}/choose-idea", json={"idea_id": "idea_1"}
        )

    assert response.status_code == 409
    current = original_get_chapter(chapter["id"])
    assert current["status"] == "generating"


@pytest.mark.asyncio
async def test_invalid_story_ideas_do_not_insert_a_chapter(monkeypatch):
    """Catches the chapter route persisting an invalid provider result."""
    database = importlib.import_module("database.database")
    main = importlib.import_module("main")
    story_idea = importlib.import_module("services.story_idea")
    classroom_id = uuid4()
    inserts = []

    class ChapterQuery:
        def insert(self, data):
            inserts.append(data)
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    monkeypatch.setattr(database, "get_classroom", lambda _id: {"id": str(classroom_id), "story_theme": "space"})
    monkeypatch.setattr(database, "get_students_by_classroom", lambda _id: [])
    monkeypatch.setattr(database, "get_chapters_by_classroom", lambda _id: [])
    monkeypatch.setattr(database, "create_chapter", lambda data: inserts.append(data))
    monkeypatch.setattr(
        story_idea,
        "generate_story_ideas",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("OpenAI returned no validated story ideas")),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/classrooms/{classroom_id}/chapters/start",
            json={"lesson_prompt": "Newton's laws"},
        )

    assert response.status_code == 500
    assert inserts == []


def test_stale_story_paths_are_not_registered_for_any_method():
    """Catches deleted story paths returning under any HTTP method."""
    app = importlib.import_module("main").app

    registered_paths = {route.path for route in app.routes}
    stale_paths = {
        "/story/create/{classroom_id}",
        "/story/generate-options",
        "/chapters/ideas",
    }

    assert registered_paths.isdisjoint(stale_paths)


def test_material_paths_are_not_registered_for_any_method():
    """Catches the removed material-storage feature returning under any HTTP method."""
    app = importlib.import_module("main").app

    registered_paths = {route.path for route in app.routes}
    material_paths = {
        "/classrooms/{classroom_id}/materials",
        "/classrooms/{classroom_id}/materials/upload",
        "/materials/{material_id}",
    }

    assert registered_paths.isdisjoint(material_paths)


def test_student_photo_upload_is_not_registered_for_any_method():
    """Catches the unauthenticated child-photo endpoint returning under any method."""
    app = importlib.import_module("main").app

    registered_paths = {route.path for route in app.routes}

    assert "/students/upload-photo" not in registered_paths

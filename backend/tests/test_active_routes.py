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

    class ChapterQuery:
        def __init__(self):
            self.data = None
            self.chapter_id = None

        def insert(self, data):
            self.data = {"id": str(chapter_id), **data}
            chapters[str(chapter_id)] = self.data
            return self

        def update(self, data):
            self.data = data
            return self

        def eq(self, _field, value):
            self.chapter_id = value
            return self

        def execute(self):
            if self.chapter_id and self.data:
                chapters[self.chapter_id].update(self.data)
            return SimpleNamespace(data=[chapters[self.chapter_id]] if self.chapter_id else [self.data])

    monkeypatch.setattr(database, "get_classroom", lambda _id: {"id": str(classroom_id), "story_theme": "space"})
    monkeypatch.setattr(database, "get_students_by_classroom", lambda _id: [])
    monkeypatch.setattr(database, "get_chapters_by_classroom", lambda _id: [])
    monkeypatch.setattr(database, "get_chapter", lambda chapter: chapters.get(chapter))
    monkeypatch.setattr(
        database,
        "get_chapter_with_panels",
        lambda chapter: {**chapters[chapter], "panels": []},
    )
    monkeypatch.setattr(database, "supabase", SimpleNamespace(table=lambda _name: ChapterQuery()))
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

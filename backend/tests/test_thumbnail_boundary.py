"""Thumbnail removal and story-choice URL boundary regressions."""

import importlib
from uuid import uuid4

import httpx
import pytest


@pytest.mark.asyncio
async def test_thumbnail_generation_route_is_not_public():
    """Catches the deleted provider endpoint being registered again."""
    app = importlib.import_module("main").app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/story/generate-thumbnail",
            json={"title": "Orbit", "summary": "A lesson in motion"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "caller_url",
    [
        "http://127.0.0.1/admin",
        "http://10.0.0.1/private",
        "https://images.example/not-provider-owned.jpg",
    ],
)
async def test_choose_idea_rejects_caller_urls_before_handler_execution(
    monkeypatch, caller_url
):
    """Catches caller-controlled URLs reaching database or network code."""
    database = importlib.import_module("database.database")
    app = importlib.import_module("main").app
    chapter_id = uuid4()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        monkeypatch.setattr(
            database,
            "get_chapter",
            lambda _id: pytest.fail("choose-idea reached the database"),
        )
        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            lambda *_args, **_kwargs: pytest.fail(
                "choose-idea attempted network access"
            ),
        )
        response = await client.post(
            f"/chapters/{chapter_id}/choose-idea",
            json={"idea_id": "idea_1", "thumbnail_url": caller_url},
        )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "thumbnail_url"]
    assert response.json()["detail"][0]["type"] == "extra_forbidden"


@pytest.mark.asyncio
async def test_choose_idea_accepts_only_a_valid_idea_id(monkeypatch):
    """Catches strict extra-field validation rejecting the supported request."""
    database = importlib.import_module("database.database")
    app = importlib.import_module("main").app
    chapter_id = uuid4()
    updates = []

    monkeypatch.setattr(database, "get_chapter", lambda _id: {"id": str(chapter_id)})
    monkeypatch.setattr(
        database,
        "update_chapter",
        lambda _chapter_id, data: (updates.append(data) or {"id": str(chapter_id), **data}),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/chapters/{chapter_id}/choose-idea", json={"idea_id": "idea_1"}
        )

    assert response.status_code == 200
    assert updates == [{"chosen_idea_id": "idea_1", "status": "idea_chosen"}]


def test_comic_generation_uses_canonical_submit_and_provider_polling_urls(
    monkeypatch,
):
    """Catches environment configuration redirecting BFL credentials off-provider."""
    legacy_base_name = "BFL_API_" + "BASE"
    monkeypatch.setenv(legacy_base_name, "https://caller.example")
    comic_creation = importlib.reload(
        importlib.import_module("services.comic_creation")
    )
    requested_urls = []
    polling_url = "https://provider.example/poll/task-1"
    sample_url = "https://provider.example/images/task-1.png"

    class Response:
        def __init__(self, payload=None, content=b""):
            self.payload = payload
            self.content = content

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def post(url, **_kwargs):
        requested_urls.append(url)
        return Response({"polling_url": polling_url})

    def get(url, **_kwargs):
        requested_urls.append(url)
        if url == polling_url:
            return Response({"status": "Ready", "result": {"sample": sample_url}})
        return Response(content=b"image-bytes")

    monkeypatch.setattr(comic_creation, "BFL_API_KEY", "test-key")
    monkeypatch.setattr(comic_creation.requests, "post", post)
    monkeypatch.setattr(comic_creation.requests, "get", get)
    monkeypatch.setattr(comic_creation.time, "sleep", lambda _seconds: None)

    result = comic_creation.call_flux_and_download("safe prompt")

    assert result == (b"image-bytes", sample_url)
    assert requested_urls == [
        "https://api.bfl.ai/v1/flux-2-pro",
        polling_url,
        sample_url,
    ]

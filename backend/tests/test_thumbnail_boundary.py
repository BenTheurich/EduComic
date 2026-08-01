"""Thumbnail removal and story-choice URL boundary regressions."""

import base64
import importlib
from uuid import uuid4

import httpx
import pytest

from local_storage import LocalStorage, media_url


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

    monkeypatch.setattr(
        database,
        "get_chapter",
        lambda _id: {"id": str(chapter_id), "story_ideas": [{"id": "idea_1"}]},
    )
    monkeypatch.setattr(
        database,
        "choose_chapter_idea",
        lambda _chapter_id, idea: (
            updates.append({"chosen_idea_id": idea, "status": "idea_chosen"})
            or {"id": str(chapter_id), "chosen_idea_id": idea, "status": "idea_chosen"}
        ),
        raising=False,
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

    submitted = {}

    def post(url, **kwargs):
        requested_urls.append(url)
        submitted.update(kwargs["json"])
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
    assert submitted["safety_tolerance"] == 2


def test_flux_inlines_validated_local_reference_bytes(monkeypatch, tmp_path):
    """Catches application-only /media URLs being sent to BFL or localhost."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    comic_creation = importlib.reload(importlib.import_module("services.comic_creation"))
    storage = LocalStorage(tmp_path)
    owner = str(uuid4())
    object_path = storage.new_object_path("avatars", owner, ".png")
    storage.finalize(storage.stage_bytes(b"avatar-bytes", ".png", max_bytes=100), object_path)
    submitted = {}

    class Response:
        content = b"generated"

        def __init__(self, payload=None):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def post(_url, **kwargs):
        submitted.update(kwargs["json"])
        return Response({"polling_url": "https://provider.test/poll"})

    def get(url, **_kwargs):
        if url.endswith("/poll"):
            return Response({"status": "Ready", "result": {"sample": "https://provider.test/image.png"}})
        return Response()

    monkeypatch.setattr(comic_creation, "BFL_API_KEY", "test-key")
    monkeypatch.setattr(comic_creation.requests, "post", post)
    monkeypatch.setattr(comic_creation.requests, "get", get)
    monkeypatch.setattr(comic_creation.time, "sleep", lambda _seconds: None)

    comic_creation.call_flux_and_download("safe", reference_images=[media_url(object_path)])

    assert submitted["input_image"] == base64.b64encode(b"avatar-bytes").decode("ascii")
    assert "/media/" not in submitted["input_image"]
    assert "localhost" not in submitted["input_image"]


@pytest.mark.parametrize("reference", ["http://localhost:8000/media/avatar.png", "/media/../secret.png"])
def test_flux_rejects_unvalidated_reference_paths(monkeypatch, tmp_path, reference):
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    comic_creation = importlib.reload(importlib.import_module("services.comic_creation"))
    monkeypatch.setattr(comic_creation, "BFL_API_KEY", "test-key")
    monkeypatch.setattr(
        comic_creation.requests,
        "post",
        lambda *_args, **_kwargs: pytest.fail("invalid reference reached provider"),
    )

    with pytest.raises(ValueError, match="local|reference"):
        comic_creation.call_flux_and_download("safe", reference_images=[reference])


def test_flux_rejects_non_image_and_oversized_local_references(monkeypatch, tmp_path):
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    comic_creation = importlib.reload(importlib.import_module("services.comic_creation"))
    storage = LocalStorage(tmp_path)
    owner = str(uuid4())
    pdf_path = storage.new_object_path("avatars", owner, ".pdf")
    storage.finalize(storage.stage_bytes(b"pdf", ".pdf", max_bytes=10), pdf_path)
    large_path = storage.new_object_path("avatars", owner, ".png")
    large_bytes = b"x" * (20 * 1024 * 1024 + 1)
    storage.finalize(
        storage.stage_bytes(large_bytes, ".png", max_bytes=len(large_bytes)),
        large_path,
    )
    monkeypatch.setattr(comic_creation, "BFL_API_KEY", "test-key")
    monkeypatch.setattr(
        comic_creation.requests,
        "post",
        lambda *_args, **_kwargs: pytest.fail("invalid reference reached provider"),
    )

    for reference in (media_url(pdf_path), media_url(large_path)):
        with pytest.raises(ValueError, match="local|reference"):
            comic_creation.call_flux_and_download("safe", reference_images=[reference])

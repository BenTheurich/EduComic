"""HTTP trust-boundary validation and safe failure coverage."""

import importlib
import logging
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest


@pytest.fixture
def app():
    return importlib.import_module("main").app


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_student_creation_requires_bounded_json_body(client, monkeypatch):
    """Catches student fields remaining unbounded query parameters."""
    database = importlib.import_module("database.database")
    inserted = {}

    class Query:
        def insert(self, data):
            inserted.update(data)
            return self

        def execute(self):
            return SimpleNamespace(data=[{"id": str(uuid4()), **inserted}])

    monkeypatch.setattr(database, "supabase", SimpleNamespace(table=lambda _name: Query()))

    accepted = await client.post(
        "/students/create",
        json={"name": "  Ada Lovelace  ", "interests": "  robots  ", "photo_url": None},
    )
    rejected = await client.post(
        "/students/create",
        json={"name": "x" * 101, "interests": "robots", "photo_url": None},
    )

    assert accepted.status_code == 200
    assert inserted == {"name": "Ada Lovelace", "interests": "robots", "photo_url": None}
    assert rejected.status_code == 422


@pytest.mark.asyncio
async def test_oversized_photo_url_is_rejected(client):
    """Catches oversized provider/storage references reaching active handlers."""
    response = await client.post(
        "/students/create",
        json={
            "name": "Ada",
            "interests": "robots",
            "photo_url": "https://example.test/" + "a" * 5000,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "photo_url"]


@pytest.mark.asyncio
async def test_classroom_rejects_unknown_design_style(client):
    """Catches arbitrary classroom styles crossing the API boundary."""
    response = await client.post(
        "/classrooms",
        json={
            "name": "Science",
            "subject": "physics",
            "grade_level": "8",
            "story_theme": "space",
            "design_style": "photorealistic",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "design_style"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/avatar/create/not-a-uuid"),
        ("GET", "/classrooms/not-a-uuid"),
        ("DELETE", "/chapters/not-a-uuid"),
    ],
)
async def test_invalid_uuid_paths_are_rejected_before_handlers(client, method, path):
    """Catches malformed identifiers reaching database and provider code."""
    response = await client.request(method, path)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_commit_rejects_invalid_uuid_body(client):
    """Catches malformed chapter identifiers reaching a commit lookup."""
    response = await client.post(
        "/chapters/commit",
        json={"chapter_id": "not-a-uuid", "chosen_idea_id": "idea_1"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "chapter_id"]


@pytest.mark.asyncio
async def test_oversized_lesson_is_rejected(client):
    """Catches unbounded lesson text being sent to a provider."""
    response = await client.post(
        f"/classrooms/{uuid4()}/chapters/start",
        json={"lesson_prompt": "x" * 2001},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "lesson_prompt"]


@pytest.mark.asyncio
async def test_provider_exception_is_safe_and_correlated(client, monkeypatch, caplog):
    """Catches provider exception text leaking through an HTTP 500 response."""
    database = importlib.import_module("database.database")
    story_idea = importlib.import_module("services.story_idea")
    secret_text = "provider said token=super-secret"
    classroom_id = uuid4()

    monkeypatch.setattr(database, "get_classroom", lambda _id: {"id": str(classroom_id), "story_theme": "space"})
    monkeypatch.setattr(database, "get_students_by_classroom", lambda _id: [])
    monkeypatch.setattr(database, "get_chapters_by_classroom", lambda _id: [])
    monkeypatch.setattr(story_idea, "generate_story_ideas", lambda *_args: (_ for _ in ()).throw(RuntimeError(secret_text)))

    with caplog.at_level(logging.ERROR):
        response = await client.post(
            f"/classrooms/{classroom_id}/chapters/start",
            json={"lesson_prompt": "Newton's laws"},
        )

    body = response.json()
    assert response.status_code == 500
    assert body["detail"] == "Internal server error"
    assert body["error_reference"]
    assert secret_text not in response.text
    assert body["error_reference"] in caplog.text
    assert secret_text not in caplog.text


@pytest.mark.asyncio
async def test_unlisted_origin_gets_no_credentialed_cors_permission(client):
    """Catches credentialed CORS reverting to a wildcard origin."""
    response = await client.options(
        "/classrooms",
        headers={
            "Origin": "https://unlisted.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,data,files,field",
    [
        (
            "/students/upload-photo",
            {"filename": "   "},
            {"file": ("student.png", b"image", "image/png")},
            "filename",
        ),
        (
            "/students/upload-photo",
            {"filename": "a" * 256},
            {"file": ("student.png", b"image", "image/png")},
            "filename",
        ),
    ],
)
async def test_multipart_text_fields_are_nonblank_and_bounded(
    client, path, data, files, field
):
    """Catches whitespace-only or oversized upload metadata reaching handlers."""
    response = await client.post(path, data=data, files=files)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]


def test_wildcard_origin_is_rejected_when_credentials_are_enabled(monkeypatch):
    """Catches a wildcard being accepted by credentialed CORS configuration."""
    main = importlib.import_module("main")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173, *")

    with pytest.raises(RuntimeError, match="explicit origins"):
        main._allowed_origins()

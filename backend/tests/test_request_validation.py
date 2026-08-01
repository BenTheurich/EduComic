"""HTTP trust-boundary validation and safe failure coverage."""

import importlib
import logging
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

    def create_student(name, interests, **_kwargs):
        inserted.update({"name": name, "interests": interests})
        return {"id": str(uuid4()), **inserted}

    monkeypatch.setattr(database, "create_student", create_student)

    accepted = await client.post(
        "/students/create",
        json={"name": "  Ada Lovelace  ", "interests": "  robots  "},
    )
    rejected = await client.post(
        "/students/create",
        json={"name": "x" * 101, "interests": "robots"},
    )

    assert accepted.status_code == 200
    assert inserted == {"name": "Ada Lovelace", "interests": "robots"}
    assert rejected.status_code == 422


@pytest.mark.asyncio
async def test_student_creation_rejects_removed_photo_field(client):
    """Catches the unauthenticated child-photo contract returning."""
    response = await client.post(
        "/students/create",
        json={
            "name": "Ada",
            "interests": "robots",
            "photo_url": "https://example.test/ada.jpg",
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


def test_wildcard_origin_is_rejected_when_credentials_are_enabled(monkeypatch):
    """Catches a wildcard being accepted by credentialed CORS configuration."""
    main = importlib.import_module("main")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173, *")

    with pytest.raises(RuntimeError, match="explicit origins"):
        main._allowed_origins()


def test_default_origins_match_the_vite_development_server(monkeypatch):
    """Catches the backend rejecting requests from Vite's default local server."""
    main = importlib.import_module("main")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    assert main._allowed_origins() == [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

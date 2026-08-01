"""Regression coverage for local student profiles and avatar generation."""

import importlib
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from local_storage import LocalStorage, media_url


@pytest.mark.asyncio
async def test_student_creation_does_not_generate_an_avatar(monkeypatch):
    database = importlib.import_module("database.database")
    avatar = importlib.import_module("services.avatar")
    main = importlib.import_module("main")
    api_models = importlib.import_module("api_models")
    student_id = str(uuid4())
    provider = AsyncMock()
    monkeypatch.setattr(avatar, "generate_avatar", provider)
    monkeypatch.setattr(
        database,
        "create_student",
        lambda name, interests, **_kwargs: {
            "id": student_id,
            "name": name,
            "interests": interests,
            "avatar_url": None,
        },
    )

    result = await main.create_student(
        api_models.StudentCreateRequest(name="Ada Lovelace", interests="robots")
    )

    provider.assert_not_awaited()
    assert result["student"]["id"] == student_id


@pytest.mark.asyncio
async def test_avatar_lookup_failure_propagates_before_provider_call(monkeypatch):
    avatar = importlib.import_module("services.avatar")
    provider = AsyncMock(return_value="provider-image")
    storage = AsyncMock(return_value="stored-avatar")
    monkeypatch.setattr(
        avatar,
        "begin_avatar_work",
        lambda _student_id: ({"id": "student-1", "interests": "robots"}, "flux-2-pro"),
    )
    monkeypatch.setattr(
        avatar,
        "get_classrooms_by_student",
        lambda _student_id: (_ for _ in ()).throw(RuntimeError("classroom lookup failed")),
    )
    monkeypatch.setattr(avatar, "_call_black_forest_api", provider)
    monkeypatch.setattr(avatar, "_upload_avatar_to_storage", storage)
    monkeypatch.setattr(avatar, "finish_avatar_work", lambda _student_id: None)
    monkeypatch.setenv("BFL_API_KEY", "test-key")

    with pytest.raises(RuntimeError, match="classroom lookup failed"):
        await avatar.generate_avatar("student-1")

    provider.assert_not_awaited()
    storage.assert_not_awaited()


@pytest.mark.asyncio
async def test_explicit_avatar_generation_uses_the_enrolled_classroom_style(monkeypatch):
    avatar = importlib.import_module("services.avatar")
    student = {"id": "student-1", "name": "Ada Lovelace", "interests": "robots"}
    classroom = {"id": "classroom-1", "name": "Science", "design_style": "cartoon"}
    prompts = []
    monkeypatch.setattr(avatar, "begin_avatar_work", lambda _student_id: (student, "flux-2-pro"))
    monkeypatch.setattr(avatar, "get_classrooms_by_student", lambda _student_id: [classroom])
    monkeypatch.setattr(
        avatar,
        "replace_student_avatar",
        lambda _student_id, avatar_url: ({**student, "avatar_url": avatar_url}, None),
    )
    monkeypatch.setattr(avatar, "finish_avatar_work", lambda _student_id: None)
    monkeypatch.setenv("BFL_API_KEY", "test-key")

    async def capture_prompt(prompt, _api_key, **_kwargs):
        prompts.append(prompt)
        return "provider-image"

    monkeypatch.setattr(avatar, "_call_black_forest_api", capture_prompt)
    monkeypatch.setattr(avatar, "_upload_avatar_to_storage", AsyncMock(return_value="/media/avatars/avatar.png"))

    result = await avatar.generate_avatar("student-1")

    assert result["avatar_url"] == "/media/avatars/avatar.png"
    assert "style of a cartoon classroom comic strip" in prompts[0]
    assert "robots" in prompts[0]
    assert "reference photo" not in prompts[0].lower()


@pytest.mark.asyncio
async def test_avatar_update_failure_deletes_new_file_and_preserves_old(monkeypatch, tmp_path):
    avatar = importlib.import_module("services.avatar")
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BFL_API_KEY", "test-key")
    storage = LocalStorage(tmp_path)
    student_id = str(uuid4())
    old_path = storage.new_object_path("avatars", student_id, ".png")
    new_path = storage.new_object_path("avatars", student_id, ".png")
    for path, value in ((old_path, b"old"), (new_path, b"new")):
        storage.finalize(storage.stage_bytes(value, ".png", max_bytes=10), path)
    monkeypatch.setattr(
        avatar,
        "begin_avatar_work",
        lambda _student_id: (
            {"id": student_id, "interests": "robots", "avatar_url": media_url(old_path)},
            "flux-2-pro",
        ),
    )
    monkeypatch.setattr(avatar, "get_classrooms_by_student", lambda _student_id: [])
    monkeypatch.setattr(avatar, "_call_black_forest_api", AsyncMock(return_value="provider"))
    monkeypatch.setattr(avatar, "_upload_avatar_to_storage", AsyncMock(return_value=media_url(new_path)))
    monkeypatch.setattr(
        avatar,
        "replace_student_avatar",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("db failed")),
    )
    monkeypatch.setattr(avatar, "finish_avatar_work", lambda _student_id: None)

    with pytest.raises(RuntimeError, match="db failed"):
        await avatar.generate_avatar(student_id)

    assert storage.read_bytes(old_path, max_bytes=10) == b"old"
    assert not storage.absolute_path(new_path).exists()


@pytest.mark.asyncio
async def test_successful_avatar_replacement_deletes_superseded_file(monkeypatch, tmp_path):
    avatar = importlib.import_module("services.avatar")
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BFL_API_KEY", "test-key")
    storage = LocalStorage(tmp_path)
    student_id = str(uuid4())
    old_path = storage.new_object_path("avatars", student_id, ".png")
    new_path = storage.new_object_path("avatars", student_id, ".png")
    for path, value in ((old_path, b"old"), (new_path, b"new")):
        storage.finalize(storage.stage_bytes(value, ".png", max_bytes=10), path)
    student = {"id": student_id, "interests": "robots", "avatar_url": media_url(old_path)}
    monkeypatch.setattr(avatar, "begin_avatar_work", lambda _student_id: (student, "flux-2-pro"))
    monkeypatch.setattr(avatar, "get_classrooms_by_student", lambda _student_id: [])
    monkeypatch.setattr(avatar, "_call_black_forest_api", AsyncMock(return_value="provider"))
    monkeypatch.setattr(avatar, "_upload_avatar_to_storage", AsyncMock(return_value=media_url(new_path)))
    monkeypatch.setattr(
        avatar,
        "replace_student_avatar",
        lambda _student_id, avatar_url: ({**student, "avatar_url": avatar_url}, old_path),
    )
    monkeypatch.setattr(avatar, "finish_superseded_avatar_cleanup", lambda *_args: None)
    monkeypatch.setattr(avatar, "finish_avatar_work", lambda _student_id: None)

    result = await avatar.generate_avatar(student_id)

    assert result["avatar_url"] == media_url(new_path)
    assert not storage.absolute_path(old_path).exists()
    assert storage.read_bytes(new_path, max_bytes=10) == b"new"


@pytest.mark.asyncio
async def test_missing_bfl_key_is_service_unavailable_not_student_missing(monkeypatch):
    avatar = importlib.import_module("services.avatar")
    main = importlib.import_module("main")
    monkeypatch.delenv("BFL_API_KEY", raising=False)
    monkeypatch.setattr(main, "generate_avatar", avatar.generate_avatar)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
        response = await client.post(f"/avatar/create/{uuid4()}")

    assert response.status_code == 503
    assert response.json()["detail"] == "Internal server error"

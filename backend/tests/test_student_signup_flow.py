"""Regression coverage for local student profiles and avatar generation."""

import importlib
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest


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
    monkeypatch.setattr(avatar, "get_student", lambda _student_id: {"id": "student-1", "interests": "robots"})
    monkeypatch.setattr(
        avatar,
        "get_classrooms_by_student",
        lambda _student_id: (_ for _ in ()).throw(RuntimeError("classroom lookup failed")),
    )
    monkeypatch.setattr(avatar, "_call_black_forest_api", provider)
    monkeypatch.setattr(avatar, "_upload_avatar_to_storage", storage)
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
    monkeypatch.setattr(avatar, "get_student", lambda _student_id: student)
    monkeypatch.setattr(avatar, "get_classrooms_by_student", lambda _student_id: [classroom])
    monkeypatch.setattr(avatar, "update_student", lambda _student_id, updates: {**student, **updates})
    monkeypatch.setenv("BFL_API_KEY", "test-key")

    async def capture_prompt(prompt, _api_key):
        prompts.append(prompt)
        return "provider-image"

    monkeypatch.setattr(avatar, "_call_black_forest_api", capture_prompt)
    monkeypatch.setattr(avatar, "_upload_avatar_to_storage", AsyncMock(return_value="/media/avatars/avatar.png"))

    result = await avatar.generate_avatar("student-1")

    assert result["avatar_url"] == "/media/avatars/avatar.png"
    assert "style of a cartoon classroom comic strip" in prompts[0]
    assert "robots" in prompts[0]
    assert "reference photo" not in prompts[0].lower()

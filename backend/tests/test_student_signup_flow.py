"""Regression coverage for student enrollment before avatar generation."""

import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


class _Query:
    def __init__(self, state, table):
        self.state = state
        self.table = table
        self.data = None

    def insert(self, data):
        self.data = data
        return self

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def execute(self):
        if self.table == "students":
            return SimpleNamespace(data=[{**self.data, "id": "student-1", "avatar_url": None}])
        classrooms = [{"classrooms": self.state["classroom"]}] if self.state["enrolled"] else []
        return SimpleNamespace(data=classrooms)


class _Supabase:
    def __init__(self, state):
        self.state = state

    def table(self, name):
        return _Query(self.state, name)


class _FailingQuery(_Query):
    def execute(self):
        raise RuntimeError("classroom lookup failed")


class _FailingLookupSupabase:
    def table(self, name):
        return _FailingQuery({}, name)


@pytest.mark.asyncio
async def test_student_creation_does_not_generate_an_avatar(monkeypatch):
    database = importlib.import_module("database.database")
    avatar = importlib.import_module("services.avatar")
    main = importlib.import_module("main")
    api_models = importlib.import_module("api_models")
    state = {"enrolled": False, "classroom": {"design_style": "cartoon"}}
    monkeypatch.setattr(database, "supabase", _Supabase(state))
    provider = AsyncMock()
    monkeypatch.setattr(avatar, "generate_avatar", provider)

    result = await main.create_student(
        api_models.StudentCreateRequest(name="Ada Lovelace", interests="robots")
    )

    provider.assert_not_awaited()
    assert result["student"]["id"] == "student-1"


@pytest.mark.asyncio
async def test_avatar_lookup_failure_propagates_before_provider_call(monkeypatch):
    avatar = importlib.import_module("services.avatar")
    provider = AsyncMock(return_value="provider-image")
    storage = AsyncMock(return_value="stored-avatar")

    monkeypatch.setattr(avatar, "supabase", _FailingLookupSupabase())
    monkeypatch.setattr(avatar, "get_student", lambda _student_id: {"id": "student-1", "interests": "robots"})
    monkeypatch.setattr(avatar, "_call_black_forest_api", provider)
    monkeypatch.setattr(avatar, "_upload_avatar_to_storage", storage)
    monkeypatch.setenv("BFL_API_KEY", "test-key")

    with pytest.raises(RuntimeError, match="classroom lookup failed"):
        await avatar.generate_avatar("student-1")

    provider.assert_not_awaited()
    storage.assert_not_awaited()


@pytest.mark.asyncio
async def test_explicit_avatar_generation_uses_the_enrolled_classroom_style(monkeypatch):
    database = importlib.import_module("database.database")
    avatar = importlib.import_module("services.avatar")
    main = importlib.import_module("main")
    api_models = importlib.import_module("api_models")
    student = {"id": "student-1", "name": "Ada Lovelace", "interests": "robots"}
    classroom = {"id": "classroom-1", "name": "Science", "design_style": "cartoon"}
    state = {"enrolled": False, "classroom": classroom}
    fake_supabase = _Supabase(state)
    prompts = []

    monkeypatch.setattr(database, "supabase", fake_supabase)
    monkeypatch.setattr(avatar, "supabase", fake_supabase)
    monkeypatch.setattr(avatar, "get_student", lambda _student_id: student)
    monkeypatch.setattr(avatar, "update_student", lambda _student_id, updates: {**student, **updates})
    monkeypatch.setenv("BFL_API_KEY", "test-key")

    async def capture_prompt(prompt, _api_key):
        prompts.append(prompt)
        return "provider-image"

    async def store_avatar(_image_url, _student_id):
        return "stored-avatar"

    monkeypatch.setattr(avatar, "_call_black_forest_api", capture_prompt)
    monkeypatch.setattr(avatar, "_upload_avatar_to_storage", store_avatar)
    monkeypatch.setattr(database, "get_classroom", lambda _classroom_id: classroom)
    monkeypatch.setattr(database, "get_student", lambda _student_id: student)
    monkeypatch.setattr(database, "is_student_in_classroom", lambda *_args: state["enrolled"])
    monkeypatch.setattr(database, "add_student_to_classroom", lambda *_args: state.update(enrolled=True))

    await main.create_student(
        api_models.StudentCreateRequest(
            name=student["name"], interests=student["interests"]
        )
    )
    await main.join_classroom(student["id"], classroom["id"])
    result = await main.create_avatar_endpoint(student["id"])

    assert result["student"]["avatar_url"] == "stored-avatar"
    assert len(prompts) == 1
    assert "style of a cartoon classroom comic strip" in prompts[0]
    assert "robots" in prompts[0]
    assert "reference photo" not in prompts[0].lower()

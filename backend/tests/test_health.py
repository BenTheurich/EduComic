"""Offline smoke coverage for the application's operational endpoints."""

import importlib
import socket
import sys
import httpx
import pytest
import requests


def _load_application():
    for name in tuple(sys.modules):
        if name == "main" or name == "panel_review" or name.startswith(("database.", "services.")):
            sys.modules.pop(name)
    return importlib.import_module("main")


@pytest.mark.asyncio
async def test_liveness_loads_offline_without_credentials(monkeypatch):
    """Catches eager initialization making liveness unavailable without credentials."""
    monkeypatch.setattr(socket.socket, "connect", lambda *_args, **_kwargs: pytest.fail("network access"))

    app = _load_application().app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health")).json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_readiness_does_not_construct_provider_clients(monkeypatch, tmp_path):
    """Catches provider constructors or transports running during app import/readiness."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        sys.modules["openai"],
        "OpenAI",
        lambda *_args, **_kwargs: pytest.fail("OpenAI client constructed"),
    )
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *_args, **_kwargs: pytest.fail("HTTPX transport constructed"),
    )
    monkeypatch.setattr(
        requests.sessions.Session,
        "request",
        lambda *_args, **_kwargs: pytest.fail("requests transport called"),
    )

    main = _load_application()
    main.initialize_local_backend(tmp_path)
    response = await main.readiness_check()

    assert response.status_code == 200
    assert response.body
    assert b'"generation_capability":false' in response.body


@pytest.mark.asyncio
async def test_readiness_reports_all_blockers(monkeypatch, tmp_path):
    """Catches readiness hiding missing keys or unmigrated local persistence."""
    monkeypatch.setattr(socket.socket, "connect", lambda *_args, **_kwargs: pytest.fail("network access"))
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))

    app = _load_application().app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        readiness = await client.get("/ready")

    assert readiness.status_code == 503
    assert readiness.json() == {
        "status": "not_ready",
        "local_data": {
            "persistence": False,
            "migrations": False,
            "data_directory_writable": True,
            "storage": True,
            "cleanup": True,
        },
        "provider_capabilities": {"openai": False, "bfl": False},
        "generation_capability": False,
        "missing_configuration": ["OPENAI_API_KEY", "BFL_API_KEY"],
        "blocking_reasons": ["local_persistence_unavailable", "database_migration_required"],
    }


@pytest.mark.asyncio
async def test_provider_keys_do_not_hide_unmigrated_persistence(monkeypatch, tmp_path):
    """Catches provider keys making the incomplete private runtime report ready."""
    for name, value in {
        "OPENAI_API_KEY": "test-key",
        "BFL_API_KEY": "test-key",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(socket.socket, "connect", lambda *_args, **_kwargs: pytest.fail("network access"))
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))

    app = _load_application().app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        readiness = await client.get("/ready")

    assert readiness.status_code == 503
    assert readiness.json() == {
        "status": "not_ready",
        "local_data": {
            "persistence": False,
            "migrations": False,
            "data_directory_writable": True,
            "storage": True,
            "cleanup": True,
        },
        "provider_capabilities": {"openai": True, "bfl": True},
        "generation_capability": False,
        "blocking_reasons": ["local_persistence_unavailable", "database_migration_required"],
    }


@pytest.mark.asyncio
async def test_bfl_api_key_is_accepted_by_avatar_generation(monkeypatch):
    """Catches avatar generation rejecting the documented BFL key name."""
    monkeypatch.setenv("BFL_API_KEY", "test-key")

    avatar = importlib.import_module("services.avatar")
    monkeypatch.setattr(avatar, "get_classrooms_by_student", lambda _student_id: [])
    monkeypatch.setattr(avatar, "get_student", lambda _student_id: {"id": "student-1", "interests": "space"})
    monkeypatch.setattr(avatar, "_call_black_forest_api", lambda *_args: _async_value("bfl-image"))
    monkeypatch.setattr(avatar, "_upload_avatar_to_storage", lambda *_args: _async_value("stored-image"))
    monkeypatch.setattr(avatar, "update_student", lambda _student_id, updates: updates)

    assert await avatar.generate_avatar("student-1") == {"avatar_url": "stored-image"}


async def _async_value(value):
    return value

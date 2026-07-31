"""Offline smoke coverage for the application's operational endpoints."""

import importlib
import socket
import sys

import httpx
import pytest

from conftest import created_supabase_clients


def _load_application():
    for name in tuple(sys.modules):
        if name == "main" or name == "panel_review" or name.startswith(("database.", "services.")):
            sys.modules.pop(name)
    return importlib.import_module("main")


@pytest.mark.asyncio
async def test_liveness_loads_offline_and_readiness_reports_missing_configuration(monkeypatch):
    """Catches eager database initialization making liveness unavailable without credentials."""
    monkeypatch.setattr(socket.socket, "connect", lambda *_args, **_kwargs: pytest.fail("network access"))

    app = _load_application().app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health")).json() == {"status": "healthy"}
        readiness = await client.get("/ready")

    assert readiness.status_code == 503
    assert readiness.json() == {
        "status": "not_ready",
        "missing_configuration": ["SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY", "BFL_API_KEY"],
    }
    assert created_supabase_clients == []


def test_database_operations_fail_closed_when_supabase_is_unconfigured():
    """Catches unconfigured database calls reaching a client with absent credentials."""
    database = importlib.import_module("database.database")

    with pytest.raises(RuntimeError, match="Supabase is not configured"):
        database.get_all_classrooms()

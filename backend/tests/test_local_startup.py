"""Local startup and media delivery behavior."""

import importlib
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy import select

from database.models import LocalProfile
from database.session import create_session_factory
import local_runtime
from local_runtime import initialize_local_backend
from local_storage import LocalStorage, media_url


def test_local_startup_creates_data_directories(tmp_path):
    """Catches first-run startup requiring pre-created asset directories."""
    paths = initialize_local_backend(tmp_path)

    assert {path.name for path in paths.root.iterdir() if path.is_dir()} == {
        "avatars",
        "materials",
        "staging",
        "story-images",
        "student-photos",
    }


def test_local_startup_applies_migrations(tmp_path):
    """Catches first-run startup leaving a blank SQLite database."""
    paths = initialize_local_backend(tmp_path)

    assert "classrooms" in inspect(create_engine(f"sqlite:///{paths.database.as_posix()}")).get_table_names()


def test_local_startup_creates_exactly_one_non_authenticated_teacher_profile(tmp_path):
    """Catches startup missing or duplicating the concrete local teacher selection."""
    paths = initialize_local_backend(tmp_path)
    factory = create_session_factory(f"sqlite:///{paths.database.as_posix()}")

    with factory() as session:
        profiles = session.scalars(select(LocalProfile)).all()

    assert [(profile.display_name, profile.role) for profile in profiles] == [("Local Teacher", "teacher")]


def test_local_runtime_rejects_non_sqlite_database_url_before_engine_or_storage(monkeypatch, tmp_path):
    """Catches local mode contacting a configured hosted database."""
    data_dir = tmp_path / "local-data"
    monkeypatch.setenv("DATABASE_URL", "postgresql://hosted.example/educomic")
    monkeypatch.setattr(
        local_runtime,
        "upgrade_database",
        lambda *_args: pytest.fail("migration engine contacted"),
    )
    monkeypatch.setattr(
        local_runtime,
        "create_local_engine",
        lambda *_args: pytest.fail("readiness engine contacted"),
    )

    with pytest.raises(ValueError, match="SQLite"):
        initialize_local_backend(data_dir)
    assert not data_dir.exists()
    assert local_runtime.local_readiness(data_dir) == (False, True)


def test_backend_imports_without_supabase_package_or_variables(monkeypatch, tmp_path):
    """Catches the private startup path importing or configuring Supabase."""
    for name in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_IMAGES_BUCKET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    monkeypatch.delitem(sys.modules, "supabase", raising=False)
    for name in tuple(sys.modules):
        if name == "main" or name.startswith(("database.", "services.")):
            sys.modules.pop(name)

    assert importlib.import_module("main").app.title == "EduComic API"


def test_media_route_returns_application_url_without_filesystem_path(monkeypatch, tmp_path):
    """Catches local absolute paths leaking through media responses."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    storage = LocalStorage(tmp_path)
    object_path = storage.new_object_path("avatars", "00000000-0000-0000-0000-000000000001", ".png")
    storage.finalize(storage.stage_bytes(b"fictional-image", ".png", max_bytes=20), object_path)
    main = importlib.import_module("main")

    with TestClient(main.app) as client:
        response = client.get(media_url(object_path))

    assert response.status_code == 200
    assert response.content == b"fictional-image"
    assert response.headers["content-type"] == "image/png"
    assert str(tmp_path) not in str(response.headers)
    assert str(tmp_path).encode() not in response.content


def test_media_route_rejects_traversal(monkeypatch, tmp_path):
    """Catches encoded parent traversal reaching files outside local storage."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    main = importlib.import_module("main")

    with TestClient(main.app) as client:
        response = client.get("/media/%2E%2E/secret.txt")

    assert response.status_code == 404

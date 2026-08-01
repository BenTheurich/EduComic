"""First-run local data initialization."""

import json
import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from database.migrations import MIGRATION_HEAD, upgrade_database
from database.session import create_local_engine
from local_storage import LocalStorage


@dataclass(frozen=True)
class LocalPaths:
    root: Path
    database: Path


def resolve_local_paths(data_dir: Path | str | None = None) -> LocalPaths:
    configured = data_dir or os.getenv("EDUCOMIC_DATA_DIR")
    root = Path(configured).expanduser() if configured else Path(__file__).resolve().parents[1] / "data"
    root = root.resolve()
    return LocalPaths(root=root, database=root / "educomic.db")


def local_database_url(paths: LocalPaths) -> str:
    database_url = os.getenv("DATABASE_URL") or f"sqlite:///{paths.database.as_posix()}"
    if make_url(database_url).get_backend_name() != "sqlite":
        raise ValueError("Local mode requires a SQLite DATABASE_URL")
    return database_url


def initialize_local_backend(data_dir: Path | str | None = None) -> LocalPaths:
    paths = resolve_local_paths(data_dir)
    database_url = local_database_url(paths)
    storage = LocalStorage(paths.root)
    upgrade_database(database_url)
    from database.database import (
        clear_interrupted_active_work,
        ensure_local_teacher,
        fail_interrupted_generation_runs,
        get_pending_generation_artifacts,
        replace_generation_artifacts,
    )

    ensure_local_teacher(database_url)
    fail_interrupted_generation_runs(database_url)
    clear_interrupted_active_work(database_url)
    unresolved = []
    for run_id, artifact_paths in get_pending_generation_artifacts(database_url):
        remaining = []
        for object_path in artifact_paths:
            try:
                storage.delete(object_path)
            except Exception:
                remaining.append(object_path)
        replace_generation_artifacts(run_id, remaining, database_url)
        unresolved.extend(remaining)
    storage.cleanup_staging(older_than=timedelta(0))
    if unresolved:
        raise RuntimeError("Generation cleanup remains unresolved")
    return paths


def local_readiness(data_dir: Path | str | None = None) -> tuple[bool, bool]:
    """Inspect local persistence and storage without contacting providers."""
    details = local_readiness_details(data_dir)
    return details["persistence"] and details["migrations"], details["storage"]


def local_readiness_details(data_dir: Path | str | None = None) -> dict[str, bool]:
    """Report each local generation prerequisite without contacting providers."""
    paths = resolve_local_paths(data_dir)
    persistence_ready = False
    migrations_ready = False
    cleanup_ready = True
    storage_ready = False
    try:
        engine = create_local_engine(local_database_url(paths))
        with engine.connect() as connection:
            connection.execute(text("SELECT 1 FROM local_profiles LIMIT 1")).scalar_one()
            migrations_ready = (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == MIGRATION_HEAD
            )
            if migrations_ready:
                manifests = connection.execute(
                    text("SELECT artifact_paths FROM generation_runs")
                ).scalars()
                cleanup_ready = all(not json.loads(value or "[]") for value in manifests)
                deletion_manifests = connection.execute(
                    text("SELECT object_paths FROM deletion_manifests")
                ).scalars()
                cleanup_ready = cleanup_ready and all(
                    not json.loads(value or "[]") for value in deletion_manifests
                )
        engine.dispose()
        persistence_ready = True
    except Exception:
        persistence_ready = False

    try:
        storage = LocalStorage(paths.root)
        staged = storage.stage_bytes(b"ok", ".png", max_bytes=2)
        storage.absolute_path(staged, allow_staging=True).unlink()
        storage_ready = True
    except Exception:
        storage_ready = False
    return {
        "persistence": persistence_ready,
        "migrations": migrations_ready,
        "data_directory_writable": storage_ready,
        "storage": storage_ready,
        "cleanup": cleanup_ready,
    }

"""First-run local data initialization."""

import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

from database.migrations import upgrade_database
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
    LocalStorage(paths.root)
    upgrade_database(database_url)
    from database.database import ensure_local_teacher

    ensure_local_teacher(database_url)
    return paths


def local_readiness(data_dir: Path | str | None = None) -> tuple[bool, bool]:
    """Inspect local persistence and storage without contacting providers."""
    paths = resolve_local_paths(data_dir)
    persistence_ready = False
    storage_ready = False
    try:
        engine = create_local_engine(local_database_url(paths))
        with engine.connect() as connection:
            connection.execute(text("SELECT 1 FROM local_profiles LIMIT 1")).scalar_one()
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
    return persistence_ready, storage_ready

"""First-run local data initialization."""

import os
from dataclasses import dataclass
from pathlib import Path

from database.migrations import upgrade_database
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
    return os.getenv("DATABASE_URL") or f"sqlite:///{paths.database.as_posix()}"


def initialize_local_backend(data_dir: Path | str | None = None) -> LocalPaths:
    paths = resolve_local_paths(data_dir)
    LocalStorage(paths.root)
    upgrade_database(local_database_url(paths))
    return paths

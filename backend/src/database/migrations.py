"""Checked-in Alembic migration runner for local startup."""

from pathlib import Path

from alembic import command
from alembic.config import Config


MIGRATION_HEAD = "0009_avatar_thumbnails"


def upgrade_database(database_url: str) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")

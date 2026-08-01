"""Validated local file staging and durable object operations."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from uuid import UUID, uuid4


OBJECT_CLASSES = frozenset({"materials", "student-photos", "avatars", "story-images"})
KNOWN_TYPES = {".jpeg": "image/jpeg", ".jpg": "image/jpeg", ".pdf": "application/pdf", ".png": "image/png", ".webp": "image/webp"}


class StorageValidationError(ValueError):
    pass


class LocalStorage:
    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        for directory in (*OBJECT_CLASSES, "staging"):
            (self.root / directory).mkdir(exist_ok=True)

    def new_object_path(self, object_class: str, owner_id: str, suffix: str) -> str:
        if object_class not in OBJECT_CLASSES:
            raise StorageValidationError("unknown object class")
        try:
            owner = str(UUID(owner_id))
        except ValueError as exc:
            raise StorageValidationError("invalid owner identifier") from exc
        suffix = self._validated_suffix(suffix)
        return f"{object_class}/{owner}/{uuid4().hex}{suffix}"

    def stage_bytes(self, data: bytes, suffix: str, *, max_bytes: int) -> str:
        if not data:
            raise StorageValidationError("empty files are not accepted")
        if max_bytes <= 0 or len(data) > max_bytes:
            raise StorageValidationError("file exceeds staging limit")
        path = f"staging/{uuid4().hex}{self._validated_suffix(suffix)}"
        self.absolute_path(path, allow_staging=True).write_bytes(data)
        return path

    def finalize(self, staged_path: str, object_path: str) -> str:
        staged = self.absolute_path(staged_path, allow_staging=True)
        if PurePosixPath(staged_path).parts[0] != "staging" or not staged.is_file():
            raise StorageValidationError("staged file does not exist")
        destination = self.absolute_path(object_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, destination)
        return object_path

    def read_bytes(self, object_path: str, *, max_bytes: int) -> bytes:
        path = self.absolute_path(object_path)
        if max_bytes <= 0 or not path.is_file() or path.stat().st_size > max_bytes:
            raise StorageValidationError("file is missing or exceeds read limit")
        with path.open("rb") as file:
            data = file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise StorageValidationError("file exceeds read limit")
        return data

    def delete(self, object_path: str) -> bool:
        path = self.absolute_path(object_path)
        try:
            path.unlink()
        except FileNotFoundError:
            return False
        return True

    def cleanup_staging(self, *, older_than: timedelta, now: datetime | None = None) -> int:
        if older_than.total_seconds() < 0:
            raise StorageValidationError("cleanup age cannot be negative")
        cutoff = (now or datetime.now(timezone.utc)).timestamp() - older_than.total_seconds()
        removed = 0
        for path in (self.root / "staging").iterdir():
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        return removed

    def absolute_path(self, object_path: str, *, allow_staging: bool = False) -> Path:
        if not isinstance(object_path, str) or not object_path or "\\" in object_path or ":" in object_path:
            raise StorageValidationError("invalid object path")
        relative = PurePosixPath(object_path)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise StorageValidationError("invalid object path")
        allowed = OBJECT_CLASSES | ({"staging"} if allow_staging else set())
        if relative.parts[0] not in allowed:
            raise StorageValidationError("unknown object class")
        resolved = (self.root / Path(*relative.parts)).resolve()
        if resolved == self.root or self.root not in resolved.parents:
            raise StorageValidationError("object path escapes storage root")
        return resolved

    def content_type(self, object_path: str) -> str:
        suffix = PurePosixPath(object_path).suffix.lower()
        try:
            return KNOWN_TYPES[suffix]
        except KeyError as exc:
            raise StorageValidationError("unsupported media type") from exc

    @staticmethod
    def _validated_suffix(suffix: str) -> str:
        normalized = suffix.lower()
        if normalized not in KNOWN_TYPES:
            raise StorageValidationError("unsupported file type")
        return normalized


def media_url(object_path: str) -> str:
    return f"/media/{quote(object_path, safe='/')}"

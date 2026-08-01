"""Concrete local file lifecycle behavior."""

import os
from datetime import datetime, timedelta, timezone

import pytest

from local_storage import LocalStorage, StorageValidationError


def test_object_paths_reject_unsafe_inputs(tmp_path):
    """Catches caller-controlled paths escaping the local data directory."""
    storage = LocalStorage(tmp_path)

    for path in ("../secret.txt", "/etc/passwd", "C:/secret.txt", "unknown/owner/file.png"):
        with pytest.raises(StorageValidationError):
            storage.read_bytes(path, max_bytes=10)


def test_atomic_finalization_replaces_complete_file(tmp_path):
    """Catches replacement writing partial bytes or retaining the prior file."""
    storage = LocalStorage(tmp_path)
    object_path = storage.new_object_path("avatars", "00000000-0000-0000-0000-000000000001", ".png")
    first = storage.stage_bytes(b"old-image", ".png", max_bytes=20)
    storage.finalize(first, object_path)
    second = storage.stage_bytes(b"new-image", ".png", max_bytes=20)

    storage.finalize(second, object_path)

    assert storage.read_bytes(object_path, max_bytes=20) == b"new-image"
    assert not storage.absolute_path(second, allow_staging=True).exists()


def test_staging_cleanup_removes_only_abandoned_files(tmp_path):
    """Catches cleanup deleting fresh work or retaining abandoned staging files."""
    storage = LocalStorage(tmp_path)
    old_path = storage.stage_bytes(b"old", ".pdf", max_bytes=10)
    fresh_path = storage.stage_bytes(b"fresh", ".pdf", max_bytes=10)
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    os.utime(storage.absolute_path(old_path, allow_staging=True), (old_time.timestamp(), old_time.timestamp()))

    removed = storage.cleanup_staging(older_than=timedelta(hours=1))

    assert removed == 1
    assert not storage.absolute_path(old_path, allow_staging=True).exists()
    assert storage.absolute_path(fresh_path, allow_staging=True).exists()


def test_bounded_read_rejects_oversized_object(tmp_path):
    """Catches oversized objects bypassing the read limit."""
    storage = LocalStorage(tmp_path)
    object_path = storage.new_object_path("materials", "00000000-0000-0000-0000-000000000001", ".pdf")
    storage.finalize(storage.stage_bytes(b"fictional-pdf", ".pdf", max_bytes=20), object_path)

    with pytest.raises(StorageValidationError, match="read limit"):
        storage.read_bytes(object_path, max_bytes=5)


def test_delete_is_idempotent(tmp_path):
    """Catches interrupted cleanup retries raising on an already absent object."""
    storage = LocalStorage(tmp_path)
    object_path = storage.new_object_path("materials", "00000000-0000-0000-0000-000000000001", ".pdf")
    storage.finalize(storage.stage_bytes(b"fictional-pdf", ".pdf", max_bytes=20), object_path)

    assert storage.delete(object_path) is True
    assert storage.delete(object_path) is False


def test_staging_files_cannot_be_read_as_ready_objects(tmp_path):
    """Catches incomplete staging files being exposed through the media boundary."""
    storage = LocalStorage(tmp_path)
    staged_path = storage.stage_bytes(b"incomplete", ".png", max_bytes=20)

    with pytest.raises(StorageValidationError):
        storage.read_bytes(staged_path, max_bytes=20)

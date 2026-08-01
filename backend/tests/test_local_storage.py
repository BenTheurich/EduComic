"""Concrete local file lifecycle behavior."""

import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from local_storage import LocalStorage, StorageValidationError


def _create_directory_redirect(link: Path, target: Path) -> None:
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
        )
    else:
        link.symlink_to(target, target_is_directory=True)


def _remove_directory_redirect(link: Path) -> None:
    if os.name == "nt":
        link.rmdir()
    else:
        link.unlink()


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


def test_redirected_storage_root_is_rejected(tmp_path):
    """Catches a redirected managed root being accepted as the storage boundary."""
    target = tmp_path / "external"
    target.mkdir()
    redirect = tmp_path / "redirect"
    _create_directory_redirect(redirect, target)
    try:
        with pytest.raises(StorageValidationError, match="redirected"):
            LocalStorage(redirect)
    finally:
        _remove_directory_redirect(redirect)


def test_redirected_staging_cleanup_preserves_external_files(tmp_path):
    """Catches cleanup following a replaced staging directory outside storage."""
    storage = LocalStorage(tmp_path / "storage")
    staging = storage.root / "staging"
    shutil.rmtree(staging)
    external = tmp_path / "external"
    external.mkdir()
    external_file = external / "keep.png"
    external_file.write_bytes(b"keep")
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    os.utime(external_file, (old_time.timestamp(), old_time.timestamp()))
    _create_directory_redirect(staging, external)
    try:
        with pytest.raises(StorageValidationError, match="redirected"):
            storage.cleanup_staging(older_than=timedelta(hours=1))
        assert external_file.read_bytes() == b"keep"
    finally:
        _remove_directory_redirect(staging)


def test_redirected_media_read_is_rejected(tmp_path):
    """Catches reads following a redirected object owner directory."""
    storage = LocalStorage(tmp_path)
    owner = "00000000-0000-0000-0000-000000000001"
    target = storage.root / "materials" / "redirected"
    target.mkdir()
    (target / "image.png").write_bytes(b"redirected")
    redirect = storage.root / "avatars" / owner
    _create_directory_redirect(redirect, target)
    try:
        with pytest.raises(StorageValidationError, match="redirected"):
            storage.read_bytes(f"avatars/{owner}/image.png", max_bytes=20)
    finally:
        _remove_directory_redirect(redirect)


def test_redirected_media_replacement_is_rejected(tmp_path):
    """Catches atomic replacement following a redirected object owner directory."""
    storage = LocalStorage(tmp_path)
    owner = "00000000-0000-0000-0000-000000000001"
    target = storage.root / "materials" / "redirected"
    target.mkdir()
    redirect = storage.root / "avatars" / owner
    _create_directory_redirect(redirect, target)
    staged = storage.stage_bytes(b"new-image", ".png", max_bytes=20)
    try:
        with pytest.raises(StorageValidationError, match="redirected"):
            storage.finalize(staged, f"avatars/{owner}/image.png")
        assert not (target / "image.png").exists()
    finally:
        _remove_directory_redirect(redirect)

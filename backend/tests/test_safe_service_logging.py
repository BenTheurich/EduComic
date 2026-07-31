"""Provider and storage failures must not print sensitive values."""

import importlib
from types import SimpleNamespace

import pytest


class _DownloadResponse:
    content = b"image-bytes"

    def raise_for_status(self):
        return None


class _AsyncClient:
    def __init__(self, *, response=None, error=None, **_kwargs):
        self.response = response
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, _url):
        if self.error:
            raise self.error
        return self.response

    async def post(self, *_args, **_kwargs):
        if self.error:
            raise self.error
        return self.response


class _FailingBucket:
    def upload(self, *_args, **_kwargs):
        raise RuntimeError("secret storage response")


class _Storage:
    def from_(self, _bucket):
        return _FailingBucket()


@pytest.mark.asyncio
async def test_avatar_storage_failure_prints_no_url_identifier_or_exception(
    monkeypatch, capsys
):
    """Catches avatar URLs, student IDs, or storage errors leaking to stdout."""
    avatar = importlib.import_module("services.avatar")
    image_url = "https://provider.test/private-avatar-token"
    student_id = "student-private-id"
    monkeypatch.setattr(
        avatar.httpx,
        "AsyncClient",
        lambda **kwargs: _AsyncClient(response=_DownloadResponse(), **kwargs),
    )
    monkeypatch.setattr(avatar, "supabase", SimpleNamespace(storage=_Storage()))
    capsys.readouterr()

    with pytest.raises(RuntimeError, match="^Avatar upload failed$") as raised:
        await avatar._upload_avatar_to_storage(image_url, student_id)

    output = capsys.readouterr().out
    assert image_url not in output
    assert student_id not in output
    assert "secret storage response" not in output
    assert "secret storage response" not in str(raised.value)


@pytest.mark.asyncio
async def test_thumbnail_provider_failure_prints_no_exception_or_story_content(
    monkeypatch, capsys
):
    """Catches provider exceptions and teacher story content leaking to stdout."""
    thumbnail = importlib.import_module("services.thumbnail")
    title = "private lesson title"
    summary = "private lesson summary"
    monkeypatch.setattr(thumbnail, "BLACK_FOREST_API_KEY", "configured-test-key")
    monkeypatch.setattr(
        thumbnail.httpx,
        "AsyncClient",
        lambda **kwargs: _AsyncClient(error=RuntimeError("secret provider response"), **kwargs),
    )
    capsys.readouterr()

    assert await thumbnail.generate_story_thumbnail(title, summary) is None

    output = capsys.readouterr().out
    assert "secret provider response" not in output
    assert title not in output
    assert summary not in output
    assert "Traceback" not in output


def test_comic_storage_failure_prints_no_exception_or_generated_url(
    monkeypatch, capsys
):
    """Catches storage exceptions and generated URLs leaking to stdout."""
    comic_creation = importlib.import_module("services.comic_creation")
    fallback_url = "https://provider.test/private-panel-token"
    monkeypatch.setattr(comic_creation, "SUPABASE_IMAGES_BUCKET", "Images")
    monkeypatch.setattr(
        comic_creation, "supabase", SimpleNamespace(storage=_Storage())
    )
    capsys.readouterr()

    result = comic_creation.upload_image_and_get_url(
        b"image", "chapter-private-id", 1, fallback_url
    )

    output = capsys.readouterr().out
    assert result == fallback_url
    assert "secret storage response" not in output
    assert fallback_url not in output
    assert "chapter-private-id" not in output

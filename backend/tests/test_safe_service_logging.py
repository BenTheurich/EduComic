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

class _FailingBucket:
    def upload(self, *_args, **_kwargs):
        raise RuntimeError("secret storage response")


class _Storage:
    def from_(self, _bucket):
        return _FailingBucket()


class _ReviewCompletions:
    def __init__(self, *, parsed=None, error=None):
        self.parsed = parsed
        self.error = error

    def parse(self, **_kwargs):
        if self.error:
            raise self.error
        message = SimpleNamespace(parsed=self.parsed)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _review_client(*, parsed=None, error=None):
    completions = _ReviewCompletions(parsed=parsed, error=error)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def _private_panel_review_inputs():
    panel = {
        "index": 1,
        "featured_students": ["Private Student"],
        "setting": "private classroom setting",
        "description": "private panel description",
        "dialogue": [{"speaker": "Private Student", "text": "private dialogue"}],
    }
    classroom = {
        "subject": "private subject",
        "grade_level": "private grade",
        "story_theme": "private theme",
    }
    students = [
        {
            "name": "Private Student",
            "interests": "private interest",
            "avatar_url": "https://provider.test/private-avatar-token",
        }
    ]
    return panel, classroom, students


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


def test_panel_review_success_prints_no_provider_url_or_student_name(
    monkeypatch, capsys
):
    """Catches panel image URLs or featured student names leaking on success."""
    panel_review = importlib.import_module("panel_review")
    image_url = "https://provider.test/private-panel-token"
    panel, classroom, students = _private_panel_review_inputs()
    response = panel_review.PanelReview.model_validate(
        {
            "score": 9.0,
            "dimensions": {
                "text_accuracy": 9.0,
                "character_accuracy": 9.0,
                "layout_readability": 9.0,
            },
            "issues": [],
            "suggested_fix_prompt": "",
            "notes": "",
        }
    )
    monkeypatch.setattr(panel_review, "OPENAI_API_KEY", "configured-test-key")
    monkeypatch.setattr(panel_review, "openai_client", _review_client(parsed=response))
    capsys.readouterr()

    result = panel_review.review_panel_image(image_url, panel, classroom, students)

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert result["score"] == 9.0
    assert image_url not in output
    assert "Private Student" not in output


def test_panel_review_provider_failure_exposes_only_generic_error(monkeypatch, capsys):
    """Catches raw provider exceptions escaping or leaking to process output."""
    panel_review = importlib.import_module("panel_review")
    image_url = "https://provider.test/private-panel-token"
    panel, classroom, students = _private_panel_review_inputs()
    provider_error = "secret provider response https://provider.test/private-error"
    monkeypatch.setattr(panel_review, "OPENAI_API_KEY", "configured-test-key")
    monkeypatch.setattr(
        panel_review,
        "openai_client",
        _review_client(error=RuntimeError(provider_error)),
    )
    capsys.readouterr()

    with pytest.raises(RuntimeError, match="^Panel review request failed$") as raised:
        panel_review.review_panel_image(image_url, panel, classroom, students)

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert image_url not in output
    assert "Private Student" not in output
    assert provider_error not in output
    assert provider_error not in str(raised.value)


def test_panel_review_invalid_response_exposes_only_generic_error(monkeypatch, capsys):
    """Catches raw provider response content escaping JSON validation."""
    panel_review = importlib.import_module("panel_review")
    image_url = "https://provider.test/private-panel-token"
    panel, classroom, students = _private_panel_review_inputs()
    monkeypatch.setattr(panel_review, "OPENAI_API_KEY", "configured-test-key")
    monkeypatch.setattr(
        panel_review, "openai_client", _review_client(parsed=None)
    )
    capsys.readouterr()

    with pytest.raises(RuntimeError, match="^Panel review returned invalid response$") as raised:
        panel_review.review_panel_image(image_url, panel, classroom, students)

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert image_url not in output
    assert "Private Student" not in output

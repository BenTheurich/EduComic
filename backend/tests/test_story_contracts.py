"""Strict provider contracts reject unsafe output before it reaches side effects."""

from copy import deepcopy
import importlib
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from story_contracts import ComicScript, PanelReview, StoryIdeasResponse


def _ideas():
    return {
        "ideas": [
            {"title": "Forces at the Fair", "summary": "Ava tests balanced forces."},
            {"title": "Rocket Rescue", "summary": "Leo learns how thrust works."},
            {"title": "Bridge Builders", "summary": "The class compares strong shapes."},
        ]
    }


def _script():
    panels = []
    for index in range(1, 13):
        panels.append(
            {
                "index": index,
                "setting": "School science room",
                "description": "Ava and Leo test a small model rocket.",
                "narration": "The experiment begins.",
                "dialogue": [{"speaker": "Ava", "text": "Let us test the force."}],
                "featured_students": ["Ava", "Leo"],
            }
        )
    return {
        "episode_title": "The Rocket Test",
        "learning_objectives": ["Explain how a force changes motion."],
        "panels": panels,
    }


def _validate_script(payload):
    return ComicScript.model_validate(
        payload,
        context={"student_names": {"Ava", "Leo"}},
    )


def test_story_ideas_require_exactly_three_nonblank_bounded_items():
    assert len(StoryIdeasResponse.model_validate(_ideas()).ideas) == 3

    for invalid in (
        {"ideas": _ideas()["ideas"][:2]},
        {"ideas": [{"title": " ", "summary": "Valid"}, *_ideas()["ideas"][1:]]},
        {"ideas": [{"title": "T" * 121, "summary": "Valid"}, *_ideas()["ideas"][1:]]},
        {"ideas": [{"title": "Valid", "summary": "S" * 601}, *_ideas()["ideas"][1:]]},
    ):
        with pytest.raises(ValidationError):
            StoryIdeasResponse.model_validate(invalid)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda script: script["panels"].pop(),
        lambda script: script["panels"][1].update(index=1),
        lambda script: script["panels"][0]["dialogue"][0].update(speaker="Unknown"),
        lambda script: script["panels"][0].update(featured_students=["Leo"]),
        lambda script: script["panels"][0].update(featured_students=["Unknown"]),
        lambda script: script["panels"][0].update(setting=" "),
        lambda script: script["panels"][0].update(description="D" * 1201),
        lambda script: script["panels"][0].update(
            dialogue=[{"speaker": "Ava", "text": "one two three four five six seven eight nine ten eleven"}]
        ),
        lambda script: script["panels"][0].update(
            dialogue=[
                {"speaker": "Ava", "text": "First."},
                {"speaker": "Leo", "text": "Second."},
                {"speaker": "Teacher", "text": "Third."},
            ]
        ),
    ],
    ids=[
        "short-script",
        "duplicate-index",
        "unknown-speaker",
        "unfeatured-student-speaker",
        "unknown-featured-student",
        "blank-setting",
        "oversize-description",
        "long-dialogue",
        "too-many-dialogue-lines",
    ],
)
def test_comic_script_rejects_invalid_provider_output(mutate):
    script = deepcopy(_script())
    mutate(script)

    with pytest.raises(ValidationError):
        _validate_script(script)


def test_comic_script_accepts_only_expected_fields_and_known_cast():
    script = _script()
    script["panels"][0]["dialogue"] = [
        {"speaker": "Teacher", "text": "Watch what happens next."},
        {"speaker": "Narrator", "text": "The rocket starts moving."},
    ]
    assert len(_validate_script(script).panels) == 12

    script["unexpected"] = True
    with pytest.raises(ValidationError):
        _validate_script(script)


def test_comic_script_with_no_students_allows_only_teacher_or_narrator():
    script = _script()
    for panel in script["panels"]:
        panel["featured_students"] = []
        panel["dialogue"] = [{"speaker": "Teacher", "text": "Watch this force."}]
    script["panels"][0]["dialogue"][0]["speaker"] = "Ava"

    with pytest.raises(ValidationError):
        ComicScript.model_validate(script, context={"student_names": set()})


def test_panel_review_requires_complete_bounded_scores_and_text():
    valid = {
        "score": 9.0,
        "dimensions": {
            "exact_visible_text": True,
            "unexpected_visible_text": False,
            "bubble_ownership": True,
            "reference_identity_continuity": True,
            "requested_action": True,
            "layout_readability": True,
        },
        "issues": ["A speech bubble is slightly cropped."],
        "suggested_fix_prompt": "Move the bubble away from the edge.",
        "notes": "Otherwise clear.",
    }
    assert PanelReview.model_validate(valid).score == 9.0

    for invalid in (
        {key: value for key, value in valid.items() if key != "notes"},
        {**valid, "score": 11.0},
        {**valid, "score": 9.0, "dimensions": {**valid["dimensions"], "exact_visible_text": False}},
        {**valid, "issues": ["I" * 401]},
        {**valid, "suggested_fix_prompt": "F" * 1001},
    ):
        with pytest.raises(ValidationError):
            PanelReview.model_validate(invalid)


class _ParsedCompletions:
    def __init__(self, parsed):
        self.parsed = parsed
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        message = SimpleNamespace(parsed=self.parsed)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _client_for(parsed):
    completions = _ParsedCompletions(parsed)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def _classroom():
    return {
        "id": "private-classroom-id",
        "name": "Physics Club",
        "subject": "Physics",
        "grade_level": "7",
        "story_theme": "Space",
        "design_style": "comic",
        "duration": "6 months",
    }


def _students():
    return [
        {
            "name": "Ava",
            "interests": "rockets",
            "avatar_url": "https://provider.test/private-avatar-token",
        },
        {"name": "Leo", "interests": "bridges", "avatar_url": None},
    ]


def _all_message_text(call):
    return str(call["messages"])


def test_story_idea_service_uses_structured_parse_and_redacts_non_narrative_data(monkeypatch):
    story_idea = importlib.import_module("services.story_idea")
    parsed = StoryIdeasResponse.model_validate(_ideas())
    client, completions = _client_for(parsed)
    monkeypatch.setattr(story_idea, "openai_client", client)

    result = story_idea.generate_story_ideas(_classroom(), _students(), "Teach forces")

    assert [idea["id"] for idea in result] == ["idea_1", "idea_2", "idea_3"]
    call = completions.calls[0]
    assert call["model"] == "gpt-5.6-terra"
    assert call["response_format"] is StoryIdeasResponse
    assert call["max_completion_tokens"] == 2048
    prompt = _all_message_text(call)
    assert "private-classroom-id" not in prompt
    assert "private-avatar-token" not in prompt
    assert "grade_level" in prompt
    assert "Return ONLY a JSON object with this structure" not in prompt


def test_comic_service_uses_structured_parse_and_contextual_cast_validation(monkeypatch):
    comic_creation = importlib.import_module("services.comic_creation")
    parsed = ComicScript.model_validate(_script())
    client, completions = _client_for(parsed)
    monkeypatch.setattr(comic_creation, "openai_client", client)

    result = comic_creation.generate_full_script_and_panels(
        _classroom(), _students(), "Teach forces", {"id": "idea_1", "title": "Rocket lesson", "summary": "Learn."}
    )

    assert len(result["panels"]) == 12
    call = completions.calls[0]
    assert call["model"] == "gpt-5.6-terra"
    assert call["response_format"] is ComicScript
    assert call["max_completion_tokens"] == 8192
    prompt = _all_message_text(call)
    assert "private-classroom-id" not in prompt
    assert "private-avatar-token" not in prompt
    assert "grade_level" in prompt
    assert "Return ONLY a JSON object with this structure" not in prompt


def test_panel_review_uses_strict_parse_and_omits_classroom_and_student_profiles(monkeypatch):
    panel_review = importlib.import_module("panel_review")
    parsed = PanelReview.model_validate(
        {
            "score": 9.0,
            "dimensions": {
                "exact_visible_text": True,
                "unexpected_visible_text": False,
                "bubble_ownership": True,
                "reference_identity_continuity": True,
                "requested_action": True,
                "layout_readability": True,
            },
            "issues": [],
            "suggested_fix_prompt": "",
            "notes": "",
        }
    )
    client, completions = _client_for(parsed)
    monkeypatch.setattr(panel_review, "OPENAI_API_KEY", "configured-test-key")
    monkeypatch.setattr(panel_review, "openai_client", client)

    result = panel_review.review_panel_image(
        "https://provider.test/rendered-panel",
        _script()["panels"][0],
        {**_classroom(), "subject": "private subject", "story_theme": "private theme"},
        [{**_students()[0], "interests": "private interest"}],
        reference_images=[{"role": "previous successful panel", "url": "/media/story-images/fake.png"}],
    )

    assert result["score"] == 9.0
    call = completions.calls[0]
    assert call["model"] == "gpt-5.6-terra"
    assert call["response_format"] is PanelReview
    assert call["max_completion_tokens"] == 2048
    prompt = _all_message_text(call)
    assert "private interest" not in prompt
    assert "private-avatar-token" not in prompt
    assert "private subject" not in prompt
    assert "private theme" not in prompt
    assert "previous successful panel" in prompt
    assert "Return ONLY with a single JSON object" not in prompt


def test_panel_review_retry_ignores_a_false_high_overall_score_for_visible_text():
    """Catches a misspelling being accepted because an unconstrained score is high."""
    panel_review = importlib.import_module("panel_review")
    review = PanelReview.model_validate(
        {
            "score": 5.0,
            "dimensions": {
                "exact_visible_text": False,
                "unexpected_visible_text": False,
                "bubble_ownership": True,
                "reference_identity_continuity": True,
                "requested_action": True,
                "layout_readability": True,
            },
            "issues": ["The narration is misspelled."],
            "suggested_fix_prompt": "Use the exact narration.",
            "notes": "",
        }
    )

    assert panel_review.review_requires_retry(review.model_dump()) is True


def test_invalid_script_is_rejected_before_panel_deletion_or_image_provider(monkeypatch):
    comic_creation = importlib.import_module("services.comic_creation")
    invalid = _script()
    invalid["panels"][0]["dialogue"][0]["speaker"] = "Unknown"
    client, _completions = _client_for(ComicScript.model_validate(invalid))
    monkeypatch.setattr(comic_creation, "openai_client", client)
    monkeypatch.setattr(
        comic_creation,
        "get_chapter",
        lambda _chapter_id: {
            "id": "chapter-1",
            "index": 1,
            "classroom_id": "classroom-1",
            "original_prompt": "Teach forces",
            "story_ideas": [{"id": "idea_1", "title": "Rocket lesson", "summary": "Learn."}],
        },
    )
    monkeypatch.setattr(comic_creation, "get_classroom", lambda _classroom_id: _classroom())
    monkeypatch.setattr(comic_creation, "get_students_by_classroom", lambda _classroom_id: _students())
    deleted = []

    class _DeleteQuery:
        def delete(self):
            deleted.append("delete")
            return self

        def eq(self, *_args):
            return self

        def execute(self):
            return None

    monkeypatch.setattr(
        comic_creation,
        "delete_panels_by_chapter",
        lambda *_args, **_kwargs: deleted.append("delete"),
    )
    monkeypatch.setattr(
        comic_creation,
        "call_flux_and_download",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("FLUX called")),
    )

    with pytest.raises(ValidationError):
        comic_creation.commit_story_choice("chapter-1", "idea_1")
    assert deleted == []


def test_invalid_panel_review_stops_generation_before_later_side_effects(monkeypatch):
    """Catches review failures being converted into retries and persisted panels."""
    comic_creation = importlib.import_module("services.comic_creation")
    monkeypatch.setattr(comic_creation, "PANEL_REVIEW_ENABLED", True)
    monkeypatch.setattr(comic_creation, "PANEL_REVIEW_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(
        comic_creation,
        "get_chapter",
        lambda _chapter_id: {
            "id": "chapter-1",
            "index": 1,
            "classroom_id": "classroom-1",
            "original_prompt": "Teach forces",
            "story_ideas": [{"id": "idea_1", "title": "Rocket lesson", "summary": "Learn."}],
        },
    )
    monkeypatch.setattr(comic_creation, "get_classroom", lambda _classroom_id: _classroom())
    monkeypatch.setattr(comic_creation, "get_students_by_classroom", lambda _classroom_id: _students())
    monkeypatch.setattr(comic_creation, "generate_full_script_and_panels", lambda *_args, **_kwargs: _script())

    class _DeleteQuery:
        def delete(self):
            return self

        def eq(self, *_args):
            return self

        def execute(self):
            return None

    monkeypatch.setattr(comic_creation, "delete_panels_by_chapter", lambda *_args, **_kwargs: None)
    flux_calls = []
    uploads = []
    panel_writes = []
    monkeypatch.setattr(
        comic_creation,
        "call_flux_and_download",
        lambda *_args, **_kwargs: (flux_calls.append("flux") or (b"image", "https://provider.test/panel")),
    )
    monkeypatch.setattr(
        comic_creation,
        "review_panel_image",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("Panel review returned invalid response")),
    )
    monkeypatch.setattr(
        comic_creation,
        "upload_image_and_get_url",
        lambda *_args, **_kwargs: uploads.append("upload"),
    )
    monkeypatch.setattr(
        comic_creation,
        "create_panel",
        lambda *_args, **_kwargs: panel_writes.append("panel"),
    )

    with pytest.raises(RuntimeError, match="Panel review returned invalid response"):
        comic_creation.commit_story_choice("chapter-1", "idea_1")

    assert flux_calls == ["flux"]
    assert uploads == []
    assert panel_writes == []


def test_panel_review_defaults_off_and_attempts_are_hard_clamped(monkeypatch):
    comic_creation = importlib.import_module("services.comic_creation")
    monkeypatch.delenv("PANEL_REVIEW_ENABLED", raising=False)
    monkeypatch.setenv("PANEL_REVIEW_MAX_ATTEMPTS", "0")
    comic_creation = importlib.reload(comic_creation)
    assert comic_creation.PANEL_REVIEW_ENABLED is False
    assert comic_creation.PANEL_REVIEW_MAX_ATTEMPTS == 1

    monkeypatch.setenv("PANEL_REVIEW_MAX_ATTEMPTS", "99")
    comic_creation = importlib.reload(comic_creation)
    assert comic_creation.PANEL_REVIEW_MAX_ATTEMPTS == 3


def test_services_reject_missing_parsed_output(monkeypatch):
    story_idea = importlib.import_module("services.story_idea")
    comic_creation = importlib.import_module("services.comic_creation")
    panel_review = importlib.import_module("panel_review")
    client, _completions = _client_for(None)

    monkeypatch.setattr(story_idea, "openai_client", client)
    with pytest.raises(RuntimeError, match="story ideas"):
        story_idea.generate_story_ideas(_classroom(), _students(), "Teach forces")

    monkeypatch.setattr(comic_creation, "openai_client", client)
    with pytest.raises(RuntimeError, match="comic script"):
        comic_creation.generate_full_script_and_panels(
            _classroom(),
            _students(),
            "Teach forces",
            {"id": "idea_1", "title": "Rocket lesson", "summary": "Learn."},
        )

    monkeypatch.setattr(panel_review, "OPENAI_API_KEY", "configured-test-key")
    monkeypatch.setattr(panel_review, "openai_client", client)
    with pytest.raises(RuntimeError, match="Panel review returned invalid response"):
        panel_review.review_panel_image(
            "https://provider.test/rendered-panel",
            _script()["panels"][0],
            _classroom(),
            _students(),
        )

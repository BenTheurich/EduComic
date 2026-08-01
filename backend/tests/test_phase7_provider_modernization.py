"""Current provider defaults and mock-only request contracts."""

import base64
import importlib
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text

from local_storage import LocalStorage, media_url


def test_new_settings_accept_current_models_but_not_historical_model():
    from api_models import SettingsUpdateRequest
    from provider_config import SUPPORTED_BFL_MODELS, SUPPORTED_OPENAI_MODELS, require_supported_model

    for model in ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"):
        assert SettingsUpdateRequest(openai_model=model).openai_model == model
    with pytest.raises(ValidationError):
        SettingsUpdateRequest(openai_model="gpt-5.1")

    assert require_supported_model("gpt-5.1", SUPPORTED_OPENAI_MODELS, "OpenAI") == "gpt-5.1"
    assert SettingsUpdateRequest(bfl_model="flux-2-flex").bfl_model == "flux-2-flex"
    assert require_supported_model("flux-2-flex", SUPPORTED_BFL_MODELS, "BFL") == "flux-2-flex"


def test_migration_updates_local_setting_without_rewriting_historical_snapshot(tmp_path):
    from database.migrations import upgrade_database
    from test_local_database import _database_url, _upgrade_to

    url = _database_url(tmp_path / "provider-defaults.db")
    _upgrade_to(url, "0006_material_grounding")
    engine = create_engine(url)
    ids = {name: f"00000000-0000-4000-8000-00000000000{index}" for index, name in enumerate(
        ("profile", "classroom", "chapter", "setting", "run"), start=1
    )}
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO local_profiles (id, display_name, role, display_settings) "
            "VALUES (:profile, 'Fictional Teacher', 'teacher', '{}')"
        ), ids)
        connection.execute(text(
            "INSERT INTO classrooms (id, owner_id, name, subject, grade_level, story_theme, design_style) "
            "VALUES (:classroom, :profile, 'Fictional Class', 'Science', '6', 'Space', 'comic')"
        ), ids)
        connection.execute(text(
            "INSERT INTO chapters (id, classroom_id, \"index\", original_prompt, status, revision, "
            "option_student_ids, option_provenance_complete, option_settings_snapshot) "
            "VALUES (:chapter, :classroom, 1, 'Orbits', 'draft', 0, '[]', 1, '{}')"
        ), ids)
        connection.execute(text(
            "INSERT INTO settings (id, profile_id, openai_model, bfl_endpoint, generation_defaults) "
            "VALUES (:setting, :profile, 'gpt-5.1', 'flux-2-pro', '{}')"
        ), ids)
        connection.execute(text(
            "INSERT INTO generation_runs (id, idempotency_key, chapter_id, target_revision, job_state, "
            "artifact_paths, settings_snapshot) VALUES "
            "(:run, 'fictional-history', :chapter, 1, 'failed', '[]', :snapshot)"
        ), {**ids, "snapshot": json.dumps({"openai_model": "gpt-5.1", "bfl_model": "flux-2-pro"})})

    upgrade_database(url)

    with engine.connect() as connection:
        setting = connection.execute(text("SELECT openai_model FROM settings")).scalar_one()
        snapshot = json.loads(connection.execute(text("SELECT settings_snapshot FROM generation_runs")).scalar_one())
        head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert head == "0008_panel_regeneration"
    assert setting == "gpt-5.6-terra"
    assert snapshot["openai_model"] == "gpt-5.1"


@pytest.mark.asyncio
async def test_avatar_bfl_contract_uses_pinned_endpoint_poll_url_reference_and_safety(monkeypatch):
    avatar = importlib.import_module("services.avatar")
    calls = []
    polling_url = "https://provider.invalid/poll/fictional-avatar"

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **kwargs):
            calls.append(("post", url, kwargs["json"]))
            return Response({"id": "fictional-job", "polling_url": polling_url})

        async def get(self, url, **_kwargs):
            calls.append(("get", url, None))
            return Response({"status": "Ready", "result": {"sample": "https://provider.invalid/image.png"}})

    encoded_reference = base64.b64encode(b"fictional portrait").decode("ascii")
    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(avatar.httpx, "AsyncClient", Client)
    monkeypatch.setattr(avatar.asyncio, "sleep", no_sleep)

    result = await avatar._call_black_forest_api("fictional child-safe avatar", "fictional-key", input_image=encoded_reference)

    assert result == "https://provider.invalid/image.png"
    assert calls == [
        ("post", "https://api.bfl.ai/v1/flux-2-pro", {
            "prompt": "fictional child-safe avatar",
            "input_image": encoded_reference,
            "safety_tolerance": 2,
        }),
        ("get", polling_url, None),
    ]


def test_panel_bfl_contract_encodes_local_reference_and_returns_provider_poll_url(monkeypatch, tmp_path):
    generation = importlib.import_module("services.generation")
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BFL_API_KEY", "fictional-key")
    storage = LocalStorage(tmp_path)
    object_path = storage.new_object_path(
        "story-images", "00000000-0000-4000-8000-000000000001", ".png"
    )
    storage.finalize(storage.stage_bytes(b"fictional panel", ".png", max_bytes=100), object_path)
    observed = {}
    polling_url = "https://provider.invalid/poll/fictional-panel"

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"polling_url": polling_url}

    def post(url, **kwargs):
        observed.update(url=url, body=kwargs["json"])
        return Response()

    monkeypatch.setattr(generation.requests, "post", post)

    result = generation.submit_bfl_generation(
        "fictional child-safe panel",
        reference_images=[media_url(object_path)],
    )

    assert result == polling_url
    assert observed == {
        "url": "https://api.bfl.ai/v1/flux-2-pro",
        "body": {
            "prompt": "fictional child-safe panel",
            "width": 960,
            "height": 640,
            "output_format": "png",
            "safety_tolerance": 2,
            "input_image": base64.b64encode(b"fictional panel").decode("ascii"),
        },
    }

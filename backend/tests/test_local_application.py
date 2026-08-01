"""Phase 2 local/private application behavior."""

import importlib
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from database.models import Student
from local_storage import LocalStorage, media_url


def test_local_workflows_persist_across_backend_restarts(monkeypatch, tmp_path):
    """Catches an active classroom/student/chapter path bypassing durable local data."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    main = importlib.import_module("main")
    database = importlib.import_module("database.database")
    story_idea = importlib.import_module("services.story_idea")
    monkeypatch.setattr(
        story_idea,
        "generate_story_ideas",
        lambda *_args: [
            {"title": "Orbit One", "summary": "A fictional force lesson."},
            {"title": "Orbit Two", "summary": "A fictional motion lesson."},
            {"title": "Orbit Three", "summary": "A fictional gravity lesson."},
        ],
    )

    student_id = str(uuid4())
    with TestClient(main.app) as client:
        classroom_response = client.post(
            "/classrooms",
            json={
                "name": "Fictional Science",
                "subject": "Physics",
                "grade_level": "7",
                "story_theme": "Space",
                "design_style": "comic",
            },
        )
        assert classroom_response.status_code == 200
        classroom = classroom_response.json()["classroom"]

        created = client.post(
            "/students/create",
            json={
                "student_id": student_id,
                "name": "Ada Fiction",
                "interests": "robots",
                "classroom_id": classroom["id"],
            },
        )
        assert created.status_code == 200

        started = client.post(
            f"/classrooms/{classroom['id']}/chapters/start",
            json={"lesson_prompt": "Explain gravity with a toy rocket."},
        )
        assert started.status_code == 200
        chapter = started.json()["chapter"]

        storage = LocalStorage(tmp_path)
        object_path = storage.new_object_path("story-images", chapter["id"], ".png")
        storage.finalize(storage.stage_bytes(b"fictional-image", ".png", max_bytes=100), object_path)
        database.create_panel(chapter["id"], 1, f"/media/{object_path}")
        database.update_chapter(chapter["id"], {"status": "ready", "chosen_idea_id": "idea_1"})

        first_read = client.get(f"/chapters/{chapter['id']}")
        assert first_read.status_code == 200
        assert first_read.json()["chapter"]["panels"][0]["image"] == f"/media/{object_path}"
        assert client.get(f"/media/{object_path}").content == b"fictional-image"

    with TestClient(main.app) as restarted:
        assert restarted.get(f"/classrooms/{classroom['id']}").status_code == 200
        profile = restarted.get(f"/students/{student_id}").json()
        assert [item["id"] for item in profile["classrooms"]] == [classroom["id"]]
        chapter_after_restart = restarted.get(f"/chapters/{chapter['id']}").json()["chapter"]
        assert chapter_after_restart["status"] == "ready"
        assert chapter_after_restart["panels"][0]["image"] == f"/media/{object_path}"


def test_student_create_and_enroll_is_atomic_and_idempotent(monkeypatch, tmp_path):
    """Catches failed or retried enrollment leaving orphan or duplicate students."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    main = importlib.import_module("main")
    student_id = str(uuid4())
    missing_classroom = str(uuid4())

    with TestClient(main.app) as client:
        failed = client.post(
            "/students/create",
            json={
                "student_id": student_id,
                "name": "Retry Student",
                "interests": "maps",
                "classroom_id": missing_classroom,
            },
        )
        assert failed.status_code == 404
        assert client.get(f"/students/{student_id}").status_code == 404

        classroom = client.post(
            "/classrooms",
            json={
                "name": "Retry Class",
                "subject": "Math",
                "grade_level": "6",
                "story_theme": "Puzzle",
                "design_style": "cartoon",
            },
        ).json()["classroom"]
        payload = {
            "student_id": student_id,
            "name": "Retry Student",
            "interests": "maps",
            "classroom_id": classroom["id"],
        }
        assert client.post("/students/create", json=payload).status_code == 200
        assert client.post("/students/create", json=payload).status_code == 200

        assert [student["id"] for student in client.get("/students").json()["students"]] == [student_id]
        enrolled = client.get(f"/classrooms/{classroom['id']}/students").json()["students"]
        assert [student["id"] for student in enrolled] == [student_id]


def test_simultaneous_identical_student_create_and_enroll_reloads_winner(monkeypatch, tmp_path):
    """Catches a client-UUID race becoming an IntegrityError/500."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    local_runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    local_runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Race Class", "Math", "6", "Puzzle", "cartoon")
    student_id = str(uuid4())
    flush_barrier = Barrier(2)

    def pause_competing_inserts(session, *_args):
        if any(isinstance(value, Student) and value.id == student_id for value in session.new):
            flush_barrier.wait(timeout=5)

    def create_once():
        return database.create_student(
            "Concurrent Student",
            "maps",
            classroom_id=classroom["id"],
            student_id=student_id,
        )

    event.listen(Session, "before_flush", pause_competing_inserts)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: create_once(), range(2)))
    finally:
        event.remove(Session, "before_flush", pause_competing_inserts)

    assert [result["id"] for result in results] == [student_id, student_id]
    assert [row["id"] for row in database.get_all_students()] == [student_id]
    assert [row["id"] for row in database.get_students_by_classroom(classroom["id"])] == [student_id]


def test_readiness_inspects_local_data_and_provider_configuration_without_network(monkeypatch, tmp_path):
    """Catches readiness making a paid call or hiding usable local persistence."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("BFL_API_KEY", raising=False)
    main = importlib.import_module("main")
    monkeypatch.setattr(
        main,
        "httpx",
        SimpleNamespace(AsyncClient=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network called"))),
        raising=False,
    )

    with TestClient(main.app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "local_data": {
            "persistence": True,
            "migrations": True,
            "data_directory_writable": True,
            "storage": True,
            "cleanup": True,
        },
        "provider_capabilities": {"openai": False, "bfl": False},
        "generation_capability": False,
        "missing_configuration": ["OPENAI_API_KEY", "BFL_API_KEY"],
    }

    monkeypatch.setenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
    monkeypatch.setenv("BFL_API_KEY", "<your-key>")
    with TestClient(main.app) as client:
        placeholders = client.get("/ready")
    assert placeholders.json()["provider_capabilities"] == {"openai": False, "bfl": False}


def test_avatar_and_panel_outputs_are_durable_local_media(monkeypatch, tmp_path):
    """Catches generated media falling back to provider URLs or hosted storage."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    avatar = importlib.import_module("services.avatar")
    comic_creation = importlib.import_module("services.comic_creation")
    student_id = str(uuid4())
    chapter_id = str(uuid4())

    class Response:
        content = b"avatar-bytes"
        headers = {"content-type": "image/png"}

        def raise_for_status(self):
            return None

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, _url):
            return Response()

    monkeypatch.setattr(avatar.httpx, "AsyncClient", lambda **_kwargs: Client())

    avatar_url = importlib.import_module("asyncio").run(
        avatar._upload_avatar_to_storage("https://provider.test/avatar", student_id)
    )
    panel_url = comic_creation.upload_image_and_get_url(
        b"panel-bytes", chapter_id, 1, "https://provider.test/panel"
    )

    storage = LocalStorage(tmp_path)
    assert avatar_url.startswith("/media/avatars/")
    assert panel_url.startswith("/media/story-images/")
    assert storage.read_bytes(avatar_url.removeprefix("/media/"), max_bytes=100) == b"avatar-bytes"
    assert storage.read_bytes(panel_url.removeprefix("/media/"), max_bytes=100) == b"panel-bytes"


def test_panel_insert_failure_compensates_new_local_file(monkeypatch, tmp_path):
    """Catches a failed panel row insert orphaning generated image bytes."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    comic_creation = importlib.import_module("services.comic_creation")
    chapter_id = str(uuid4())
    monkeypatch.setattr(
        comic_creation,
        "create_panel",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("insert failed")),
    )

    with pytest.raises(RuntimeError, match="insert failed"):
        comic_creation._persist_panel(
            chapter_id=chapter_id,
            img_bytes=b"panel-bytes",
            fallback_url="https://provider.test/panel.png",
            index=1,
            revision=1,
            dialogue=[],
            scene_description="Scene",
            speakers=[],
        )

    assert list((tmp_path / "story-images" / chapter_id).glob("*")) == []


def test_chapter_deletion_removes_committed_panel_media(monkeypatch, tmp_path):
    """Catches database cascade deletion leaving chapter image files behind."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    local_runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    main = importlib.import_module("main")
    local_runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Delete", "Math", "6", "Space", "cartoon")
    chapter = database.create_chapter(
        {
            "classroom_id": classroom["id"],
            "index": 1,
            "original_prompt": "Teach",
            "story_ideas": [],
            "status": "draft",
        }
    )
    storage = LocalStorage(tmp_path)
    object_path = storage.new_object_path("story-images", chapter["id"], ".png")
    storage.finalize(storage.stage_bytes(b"panel", ".png", max_bytes=10), object_path)
    database.create_panel(chapter["id"], 1, f"/media/{object_path}")

    with TestClient(main.app) as client:
        response = client.delete(f"/chapters/{chapter['id']}")

    assert response.status_code == 200
    assert database.get_chapter(chapter["id"]) is None
    assert not storage.absolute_path(object_path).exists()


def test_chapter_deletion_logs_file_cleanup_failure_after_database_commit(monkeypatch, tmp_path, caplog):
    """Catches post-commit cleanup failure becoming a false database failure."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    local_runtime = importlib.import_module("local_runtime")
    database = importlib.import_module("database.database")
    main = importlib.import_module("main")
    local_runtime.initialize_local_backend(tmp_path)
    classroom = database.create_classroom("Delete", "Math", "6", "Space", "cartoon")
    chapter = database.create_chapter(
        {
            "classroom_id": classroom["id"],
            "index": 1,
            "original_prompt": "Teach",
            "story_ideas": [],
            "status": "draft",
        }
    )
    storage = LocalStorage(tmp_path)
    object_path = storage.new_object_path("story-images", chapter["id"], ".png")
    storage.finalize(storage.stage_bytes(b"panel", ".png", max_bytes=10), object_path)
    database.create_panel(chapter["id"], 1, media_url(object_path))

    with TestClient(main.app) as client:
        monkeypatch.setattr(
            main,
            "LocalStorage",
            lambda *_args: (_ for _ in ()).throw(RuntimeError("disk unavailable")),
        )
        response = client.delete(f"/chapters/{chapter['id']}")

    assert response.status_code == 200
    assert database.get_chapter(chapter["id"]) is None
    assert storage.absolute_path(object_path).exists()
    assert "Local media deletion failed context=chapter deletion" in caplog.text


def test_student_media_update_rejects_raw_object_paths(monkeypatch, tmp_path):
    """Catches callers bypassing the validated local-media URL boundary."""
    monkeypatch.setenv("EDUCOMIC_DATA_DIR", str(tmp_path))
    initialize_local_backend = importlib.import_module("local_runtime").initialize_local_backend
    database = importlib.import_module("database.database")
    initialize_local_backend(tmp_path)
    student = database.create_student("Boundary Student", "drawing")

    with pytest.raises(ValueError, match="Unsupported student update"):
        database.update_student(student["id"], {"avatar_object_path": "avatars/raw.png"})


def test_local_runner_refuses_wider_bind_without_unsupported_override():
    """Catches the supported start command silently exposing unauthenticated data."""
    run_local = importlib.import_module("run_local")

    assert run_local.validate_bind("127.0.0.1", allow_unsupported_exposure=False) == "127.0.0.1"
    try:
        run_local.validate_bind("0.0.0.0", allow_unsupported_exposure=False)
    except ValueError as exc:
        assert "unsupported" in str(exc).lower()
    else:
        raise AssertionError("wider bind was accepted without an explicit override")


def test_background_generation_delegates_to_the_durable_run_coordinator(monkeypatch):
    """Catches the API background task bypassing persisted run failure handling."""
    main = importlib.import_module("main")
    runs = []
    monkeypatch.setattr(main, "run_generation", runs.append)

    main._run_story_generation("run-1")

    assert runs == ["run-1"]

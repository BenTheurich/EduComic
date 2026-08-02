"""Founder-authorized residual provenance regressions for Phase 4."""

import json

from sqlalchemy import create_engine, text

from test_phase4_review_fixes import _classroom, _client, _script


def _personalized_options(_classroom, students, _outline, *, model):
    names = " and ".join(student["name"] for student in students)
    return [
        {"title": f"{names} explore", "summary": f"{names} solve the lesson"},
        {"title": "Second", "summary": "Second summary"},
        {"title": "Third", "summary": "Third summary"},
    ]


def test_selected_option_participants_are_provider_provenance_not_generation_cast(monkeypatch, tmp_path):
    """Active work excludes a removed student while completed comics remain readable."""
    client, database = _client(monkeypatch, tmp_path)
    import services.comic_creation as comic
    import services.generation as generation
    import services.story_idea as story_idea

    monkeypatch.setattr(story_idea, "generate_story_ideas", _personalized_options)
    monkeypatch.setattr(generation, "database", database)
    monkeypatch.setattr(generation, "comic_creation", comic)
    observed = {}

    def script_provider(**kwargs):
        observed["cast"] = [student["id"] for student in kwargs["students"]]
        return _script()

    monkeypatch.setattr(comic, "generate_full_script_and_panels", script_provider)
    monkeypatch.setattr(generation, "submit_bfl_generation", lambda *_args, **_kwargs: "poll://job")
    monkeypatch.setattr(generation, "poll_bfl_generation", lambda *_args, **_kwargs: "delivery://image")
    monkeypatch.setattr(generation, "download_bfl_image", lambda *_args, **_kwargs: b"fictional")
    monkeypatch.setattr(generation, "validate_image_bytes", lambda _content: None)

    with client:
        classroom = _classroom(client)
        ari = client.post(
            "/students/create",
            json={"name": "Ari", "interests": "orbits", "classroom_id": classroom["id"]},
        ).json()["student"]
        bea = client.post(
            "/students/create",
            json={"name": "Bea", "interests": "rockets", "classroom_id": classroom["id"]},
        ).json()["student"]
        chapter = client.post(
            f"/classrooms/{classroom['id']}/chapters/start",
            json={"lesson_prompt": "Teach orbits"},
        ).json()["chapter"]
        client.post(f"/chapters/{chapter['id']}/choose-idea", json={"idea_id": "idea_1"})
        assert database.remove_student_from_classroom(ari["id"], classroom["id"])
        run, _ = database.begin_generation_run(chapter["id"], "idea_1", "provider-provenance")

    assert run["settings_snapshot"]["student_ids"] == [bea["id"]]
    assert set(run["settings_snapshot"]["provider_input_student_ids"]) == {ari["id"], bea["id"]}
    assert database.execute_deletion("student", ari["id"]) is False

    generation.run_generation(run["id"])

    assert observed["cast"] == [bea["id"]]
    assert database.get_generation_run(run["id"])["job_state"] == "succeeded"
    assert database.execute_deletion("student", ari["id"]) is True
    assert database.get_generation_run(run["id"])["job_state"] == "succeeded"
    preserved = database.get_chapter(chapter["id"])
    assert preserved["status"] == "ready"
    assert preserved["revision"] == 1


def test_failed_option_provenance_is_cleared_even_without_output(monkeypatch, tmp_path):
    """Catches empty failed output hiding participant/settings provenance from erasure."""
    client, database = _client(monkeypatch, tmp_path)
    import services.story_idea as story_idea

    monkeypatch.setattr(
        story_idea,
        "generate_story_ideas",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fictional failure")),
    )
    with client:
        classroom = _classroom(client)
        ari = client.post(
            "/students/create",
            json={"name": "Ari", "interests": "orbits", "classroom_id": classroom["id"]},
        ).json()["student"]
        response = client.post(
            f"/classrooms/{classroom['id']}/chapters/start",
            json={"lesson_prompt": "Teach orbits"},
        )

    assert response.status_code == 500
    failed = database.get_chapters_by_classroom(classroom["id"])[0]
    assert failed["story_ideas"] == []
    assert failed["option_student_ids"] == [ari["id"]]

    assert database.execute_deletion("student", ari["id"]) is True

    scrubbed = database.get_chapter(failed["id"])
    assert scrubbed["option_student_ids"] == []
    assert scrubbed["option_settings_snapshot"] == {}
    assert ari["id"] not in json.dumps(scrubbed)


def test_erasure_preserves_neutral_selected_idea_for_existing_commit_flow(monkeypatch, tmp_path):
    """Catches erasure leaving a personalized choice or an uncommittable empty shell."""
    client, database = _client(monkeypatch, tmp_path)
    import main
    import services.story_idea as story_idea

    monkeypatch.setattr(story_idea, "generate_story_ideas", _personalized_options)
    scheduled = []
    monkeypatch.setattr(main, "run_generation", lambda run_id: scheduled.append(run_id))

    with client:
        classroom = _classroom(client)
        ari = client.post(
            "/students/create",
            json={"name": "Ari", "interests": "orbits", "classroom_id": classroom["id"]},
        ).json()["student"]
        bea = client.post(
            "/students/create",
            json={"name": "Bea", "interests": "rockets", "classroom_id": classroom["id"]},
        ).json()["student"]
        chapter = client.post(
            f"/classrooms/{classroom['id']}/chapters/start",
            json={"lesson_prompt": "Teach orbits"},
        ).json()["chapter"]
        client.post(f"/chapters/{chapter['id']}/choose-idea", json={"idea_id": "idea_1"})
        database.remove_student_from_classroom(ari["id"], classroom["id"])
        assert database.execute_deletion("student", ari["id"]) is True
        shell = database.get_chapter(chapter["id"])
        committed = client.post(
            "/chapters/commit",
            json={
                "chapter_id": chapter["id"],
                "chosen_idea_id": "idea_1",
                "idempotency_key": "neutral-shell",
            },
        )

    assert len(shell["story_ideas"]) == 1
    assert {key: shell["story_ideas"][0][key] for key in ("id", "title", "summary")} == {
        "id": "idea_1",
        "title": "Classroom story",
        "summary": "Create a new story with the current classroom.",
    }
    assert "Ari" not in json.dumps(shell)
    assert committed.status_code == 200
    run = database.get_generation_run(committed.json()["run_id"])
    assert scheduled == [run["id"]]
    assert run["settings_snapshot"]["student_ids"] == [bea["id"]]
    assert run["settings_snapshot"]["provider_input_student_ids"] == [bea["id"]]


def test_forward_migration_marks_openai_snapshots_incomplete_and_preserves_completed_story(
    monkeypatch, tmp_path
):
    """Old provenance stays conservative without breaking a completed comic."""
    from database.migrations import upgrade_database
    from test_local_database import _database_url, _upgrade_to
    import database.database as database

    database_path = tmp_path / "educomic.db"
    url = _database_url(database_path)
    _upgrade_to(url, "0004_review_fixes")
    engine = create_engine(url)
    ids = {
        "profile": "00000000000040008000000000000011",
        "classroom": "00000000000040008000000000000012",
        "student": "00000000000040008000000000000013",
        "chapter": "00000000000040008000000000000014",
        "run": "00000000000040008000000000000015",
    }
    script = _script()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO local_profiles (id, display_name, role, display_settings) "
                "VALUES (:id, 'Teacher', 'teacher', '{}')"
            ),
            {"id": ids["profile"]},
        )
        connection.execute(
            text(
                "INSERT INTO classrooms (id, owner_id, name, subject, grade_level, story_theme, design_style) "
                "VALUES (:id, :owner, 'Class', 'Science', '6', 'Space', 'comic')"
            ),
            {"id": ids["classroom"], "owner": ids["profile"]},
        )
        connection.execute(
            text("INSERT INTO students (id, name, interests) VALUES (:id, 'Ari', 'orbits')"),
            {"id": ids["student"]},
        )
        connection.execute(
            text(
                "INSERT INTO chapters (id, classroom_id, \"index\", original_prompt, story_ideas, "
                "option_student_ids, option_provenance_complete, option_settings_snapshot, "
                "chosen_idea_id, status, revision, story_script) VALUES "
                "(:id, :classroom, 1, 'Orbits', :ideas, '[]', 1, '{}', "
                "'idea_1', 'ready', 1, :script)"
            ),
            {
                "id": ids["chapter"],
                "classroom": ids["classroom"],
                "ideas": json.dumps([{"id": "idea_1", "title": "Orbit", "summary": "Learn"}]),
                "script": json.dumps(script),
            },
        )
        connection.execute(
            text(
                "INSERT INTO generation_runs (id, idempotency_key, chapter_id, selected_idea_id, "
                "target_revision, job_state, stage, artifact_paths, settings_snapshot, script_snapshot) "
                "VALUES (:id, 'pre-fix-openai', :chapter, 'idea_1', 1, 'succeeded', 'ready', '[]', "
                ":snapshot, :script)"
            ),
            {
                "id": ids["run"],
                "chapter": ids["chapter"],
                "snapshot": json.dumps(
                    {
                        "story_length": 12,
                        "openai_model": "gpt-5.1",
                        "bfl_model": "flux-2-pro",
                        "student_ids": [],
                        "provenance_complete": True,
                    }
                ),
                "script": json.dumps(script),
            },
        )

    upgrade_database(url)

    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0008_panel_regeneration"
        snapshot = json.loads(
            connection.execute(
                text("SELECT settings_snapshot FROM generation_runs WHERE id = :id"),
                {"id": ids["run"]},
            ).scalar_one()
        )
    assert snapshot["openai_model"] == "gpt-5.1"
    assert snapshot["provenance_complete"] is False

    with database._session(url) as session:
        database._apply_deletion(session, "student", ids["student"])
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM generation_runs WHERE id = :id"), {"id": ids["run"]}
        ).scalar_one() == 1
        assert connection.execute(
            text("SELECT revision FROM chapters WHERE id = :id"), {"id": ids["chapter"]}
        ).scalar_one() == 1

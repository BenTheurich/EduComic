"""
FastAPI main application entry point.
"""

import logging
import os
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from api_models import (
    ClassroomCreateRequest,
    ClassroomUpdateRequest,
    CommitStoryRequest,
    LessonPromptRequest,
    PanelRegenerationRequest,
    StoryChoiceRequest,
    StoryPreviewRetryRequest,
    StudentCreateRequest,
    StudentUpdateRequest,
    SettingsUpdateRequest,
)
from local_runtime import initialize_local_backend, local_readiness_details, resolve_local_paths
from local_storage import LocalStorage, StorageValidationError, media_url
from materials import MAX_PDF_BYTES, MaterialRejected, extract_pdf
from provider_config import configured_secret
from services.avatar import PortraitRejected, ProviderConfigurationError, generate_avatar, normalize_portrait
from services.generation import run_generation, run_story_previews, run_story_previews_for_chapter
from services.panel_regeneration import run_panel_regeneration

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_local_backend()
    yield


# Create FastAPI app
app = FastAPI(
    title="EduComic API",
    description="API for educational comic generation",
    version="1.0.0",
    lifespan=lifespan,
)

logger = logging.getLogger("educomic.api")


def _allowed_origins() -> list[str]:
    configured = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
    )
    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    if not origins or "*" in origins:
        raise RuntimeError(
            "ALLOWED_ORIGINS must contain explicit origins when credentials are enabled"
        )
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _internal_error(request: Request, status_code: int = 500) -> JSONResponse:
    reference = uuid4().hex
    logger.error(
        "Request failed reference=%s method=%s path=%s status=%s",
        reference,
        request.method,
        request.url.path,
        status_code,
    )
    return JSONResponse(
        status_code=status_code,
        content={"detail": "Internal server error", "error_reference": reference},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        return _internal_error(request, exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, _exc: Exception):
    return _internal_error(request)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "EduComic API is running", "status": "healthy"}


@app.get("/health")
async def health_check():
    """Liveness check that never depends on external services."""
    return {"status": "healthy"}


@app.get("/ready")
async def readiness_check():
    """Inspect local data and provider configuration without paid calls."""
    local_data = local_readiness_details()
    persistence_ready = local_data["persistence"]
    migrations_ready = local_data["migrations"]
    storage_ready = local_data["storage"]
    cleanup_ready = local_data["cleanup"]

    providers = {
        "openai": configured_secret("OPENAI_API_KEY"),
        "bfl": configured_secret("BFL_API_KEY"),
    }
    missing = [name for name, configured in (("OPENAI_API_KEY", providers["openai"]), ("BFL_API_KEY", providers["bfl"])) if not configured]
    content = {
        "status": "ready" if persistence_ready and migrations_ready and storage_ready and cleanup_ready else "not_ready",
        "local_data": local_data,
        "provider_capabilities": providers,
        "generation_capability": persistence_ready and migrations_ready and storage_ready and cleanup_ready and all(providers.values()),
    }
    if missing:
        content["missing_configuration"] = missing
    if not persistence_ready or not migrations_ready or not storage_ready or not cleanup_ready:
        content["blocking_reasons"] = [
            reason
            for ready, reason in (
                (persistence_ready, "local_persistence_unavailable"),
                (migrations_ready, "database_migration_required"),
                (storage_ready, "local_storage_unavailable"),
                (cleanup_ready, "generation_cleanup_required"),
            )
            if not ready
        ]
    return JSONResponse(
        status_code=200 if persistence_ready and migrations_ready and storage_ready and cleanup_ready else 503,
        content=content,
    )


@app.get("/media/{object_path:path}")
async def local_media(object_path: str):
    """Serve a validated local object without returning its filesystem path."""
    storage = LocalStorage(resolve_local_paths().root)
    try:
        content = storage.read_bytes(object_path, max_bytes=50 * 1024 * 1024)
        content_type = storage.content_type(object_path)
    except StorageValidationError:
        raise HTTPException(status_code=404, detail="Media not found")
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )


@app.post("/classrooms")
async def create_classroom_endpoint(request: ClassroomCreateRequest):
    """
    Create a new classroom.

    Args:
        name: Classroom name
        subject: Subject being taught
        grade_level: Grade level
        story_theme: Theme for stories
        design_style: Visual design style

    Returns:
        Created classroom record
    """
    from database.database import create_classroom

    try:
        classroom = create_classroom(
            name=request.name,
            subject=request.subject,
            grade_level=request.grade_level,
            story_theme=request.story_theme,
            design_style=request.design_style,
            duration="6 months",
        )
        return {"success": True, "classroom": classroom}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.patch("/classrooms/{classroom_id}")
async def update_classroom_endpoint(classroom_id: UUID, request: ClassroomUpdateRequest):
    from database.database import update_classroom

    classroom = update_classroom(str(classroom_id), request.model_dump())
    if classroom is None:
        raise HTTPException(status_code=404, detail="Classroom not found")
    return {"success": True, "classroom": classroom}


@app.delete("/classrooms/{classroom_id}")
async def delete_classroom_endpoint(classroom_id: UUID, confirm: bool = False):
    from database.database import execute_deletion

    if not confirm:
        raise HTTPException(status_code=400, detail="Deletion requires explicit confirmation")
    if not execute_deletion("classroom", str(classroom_id)):
        raise HTTPException(status_code=409, detail="Local file cleanup is incomplete; retry deletion")
    return {"success": True, "message": "Classroom deleted"}


async def _bounded_pdf_body(request: Request) -> bytes:
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk[: MAX_PDF_BYTES + 1 - len(content)])
        if len(content) > MAX_PDF_BYTES:
            raise MaterialRejected("oversized")
    return bytes(content)


@app.post("/classrooms/{classroom_id}/materials", status_code=201)
async def upload_material_endpoint(classroom_id: UUID, request: Request, filename: str):
    """Accept one bounded raw PDF body and atomically retain only validated sources."""
    from database.database import create_material, get_classroom

    classroom_id = str(classroom_id)
    if get_classroom(classroom_id) is None:
        raise HTTPException(status_code=404, detail="Classroom not found")
    filename = filename.strip()
    if (
        not filename
        or len(filename) > 255
        or "/" in filename
        or "\\" in filename
        or any(ord(character) < 32 for character in filename)
    ):
        raise HTTPException(status_code=400, detail="A safe source filename is required")
    try:
        content = await _bounded_pdf_body(request)
        extracted = extract_pdf(content)
    except MaterialRejected as exc:
        raise HTTPException(
            status_code=422,
            detail={"state": exc.state, "message": str(exc)},
        )

    storage = LocalStorage(resolve_local_paths().root)
    staged = material = None
    try:
        staged = storage.stage_bytes(content, ".pdf", max_bytes=MAX_PDF_BYTES)
        object_path = storage.new_object_path("materials", classroom_id, ".pdf")
        material = create_material(
            classroom_id,
            filename,
            object_path,
            extracted.content_hash,
            extracted.pages,
        )
        storage.finalize(staged, object_path)
        staged = None
    except Exception:
        if staged:
            storage.discard_staged(staged)
        if material:
            from database.database import execute_deletion

            execute_deletion("material", material["id"])
        raise
    return {"success": True, "material": material}


@app.get("/classrooms/{classroom_id}/materials")
async def list_materials_endpoint(classroom_id: UUID):
    from database.database import get_classroom, get_materials_by_classroom

    classroom_id = str(classroom_id)
    if get_classroom(classroom_id) is None:
        raise HTTPException(status_code=404, detail="Classroom not found")
    return {"success": True, "materials": get_materials_by_classroom(classroom_id)}


@app.delete("/materials/{material_id}")
async def delete_material_endpoint(material_id: UUID, confirm: bool = False):
    from database.database import execute_deletion

    if not confirm:
        raise HTTPException(status_code=400, detail="Deletion requires explicit confirmation")
    if not execute_deletion("material", str(material_id)):
        raise HTTPException(status_code=409, detail="Local file cleanup is incomplete; retry deletion")
    return {"success": True, "message": "Material deleted"}


@app.get("/classrooms")
async def get_classrooms():
    """
    Get all classrooms.

    Returns:
        List of all classroom records with student counts
    """
    from database.database import (
        get_all_classrooms,
        get_chapters_by_classroom,
        get_students_by_classroom,
    )

    try:
        classrooms = get_all_classrooms()

        # Add student count and story count to each classroom
        for classroom in classrooms:
            students = get_students_by_classroom(classroom["id"])
            chapters = get_chapters_by_classroom(classroom["id"])
            classroom["student_count"] = len(students)
            classroom["story_count"] = len(chapters)

        return {"success": True, "classrooms": classrooms}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/classrooms/{classroom_id}")
async def get_classroom(classroom_id: UUID):
    """
    Get a specific classroom with students.

    Args:
        classroom_id: UUID of the classroom

    Returns:
        Classroom record with students array
    """
    from database.database import get_classroom_with_students

    try:
        classroom = get_classroom_with_students(str(classroom_id))
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")
        return {"success": True, "classroom": classroom}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/classrooms/{classroom_id}/students")
async def get_classroom_students(classroom_id: UUID):
    """
    Get all students in a classroom.

    Args:
        classroom_id: UUID of the classroom

    Returns:
        List of student records
    """
    from database.database import get_students_by_classroom

    try:
        students = get_students_by_classroom(str(classroom_id))
        return {"success": True, "students": students}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/classrooms/{classroom_id}/chapters")
async def get_classroom_chapters(classroom_id: UUID):
    """
    Get all chapters (stories) for a classroom.

    Args:
        classroom_id: UUID of the classroom

    Returns:
        List of chapter records
    """
    from database.database import get_chapters_by_classroom

    try:
        chapters = get_chapters_by_classroom(str(classroom_id))
        return {"success": True, "chapters": chapters}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/students/create")
async def create_student(request: StudentCreateRequest):
    """
    Create a local student profile and optional classroom enrollment.

    Args:
        name: Student's full name
        interests: Student's interests/hobbies

    Returns:
        Created student record
    """
    from database.database import create_student as create_local_student

    try:
        student = create_local_student(
            request.name,
            request.interests,
            classroom_id=str(request.classroom_id) if request.classroom_id else None,
            student_id=str(request.student_id) if request.student_id else None,
        )
        return {"success": True, "student": student}
    except ValueError as exc:
        if str(exc) == "Classroom not found":
            raise HTTPException(status_code=404, detail="Classroom not found")
        raise HTTPException(status_code=409, detail="Student profile conflicts with an existing local profile")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/students/{student_id}/join-classroom/{classroom_id}")
async def join_classroom(student_id: UUID, classroom_id: UUID):
    """
    Add a student to a classroom (many-to-many).
    Student can be in multiple classrooms.

    Args:
        student_id: UUID of the student
        classroom_id: UUID of the classroom to join

    Returns:
        Student and classroom info
    """
    from database.database import (
        add_student_to_classroom,
        get_classroom,
        get_student,
        is_student_in_classroom,
    )

    try:
        # Verify classroom exists
        student_id = str(student_id)
        classroom_id = str(classroom_id)
        classroom = get_classroom(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")

        # Verify student exists
        student = get_student(student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Check if already enrolled
        if is_student_in_classroom(student_id, classroom_id):
            return {
                "success": True,
                "message": "Student already enrolled in this classroom",
                "student": student,
                "classroom": classroom,
            }

        # Add student to classroom (many-to-many)
        add_student_to_classroom(student_id, classroom_id)

        return {
            "success": True,
            "message": "Student joined classroom successfully",
            "student": student,
            "classroom": classroom,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/students")
async def get_all_students():
    """
    Get all students.

    Returns:
        List of all student records
    """
    from database.database import get_all_students

    try:
        return {"success": True, "students": get_all_students()}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/students/{student_id}")
async def get_student(student_id: UUID):
    """
    Get a student by ID with all their classrooms.

    Args:
        student_id: UUID of the student

    Returns:
        Student record with list of classrooms
    """
    from database.database import get_classrooms_by_student, get_student

    try:
        student_id = str(student_id)
        student = get_student(student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Get all classrooms the student is enrolled in
        classrooms = get_classrooms_by_student(student_id)

        return {"success": True, "student": student, "classrooms": classrooms}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.patch("/students/{student_id}")
async def update_student_endpoint(student_id: UUID, request: StudentUpdateRequest):
    from database.database import update_student

    student = update_student(str(student_id), request.model_dump())
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"success": True, "student": student}


@app.delete("/students/{student_id}")
async def erase_student_endpoint(student_id: UUID, confirm: bool = False):
    from database.database import execute_deletion

    if not confirm:
        raise HTTPException(status_code=400, detail="Erasure requires explicit confirmation")
    if not execute_deletion("student", str(student_id)):
        raise HTTPException(status_code=409, detail="Local file cleanup is incomplete; retry deletion")
    return {
        "success": True,
        "message": "Student profile and personal files erased; completed stories preserved",
    }


@app.get("/students/{student_id}/classrooms")
async def get_student_classrooms(student_id: UUID):
    """
    Get all classrooms a student is enrolled in.

    Args:
        student_id: UUID of the student

    Returns:
        List of classroom records
    """
    from database.database import get_classrooms_by_student

    try:
        classrooms = get_classrooms_by_student(str(student_id))
        return {"success": True, "classrooms": classrooms}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/students/{student_id}/leave-classroom/{classroom_id}")
async def leave_classroom(student_id: UUID, classroom_id: UUID, confirm: bool = False):
    """
    Remove a student from a classroom.

    Args:
        student_id: UUID of the student
        classroom_id: UUID of the classroom to leave

    Returns:
        Success message
    """
    from database.database import remove_student_from_classroom

    try:
        if not confirm:
            raise HTTPException(status_code=400, detail="Classroom removal requires explicit confirmation")
        success = remove_student_from_classroom(str(student_id), str(classroom_id))
        return {"success": True, "removed": success, "message": "Student removed from classroom"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/avatar/create/{student_id}")
async def create_avatar_endpoint(student_id: UUID, request: Request):
    """
    Generate an avatar for a student.

    Args:
        student_id: UUID of the student

    Returns:
        Updated student record with avatar_url
    """
    from database.database import GenerationConflict

    try:
        body = await request.body()
        content_type = request.headers.get("content-type", "").split(";", 1)[0]
        portrait = normalize_portrait(body, content_type) if body or content_type.startswith("image/") else None
        student = await generate_avatar(str(student_id), portrait)
        return {"success": True, "student": student}
    except PortraitRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ProviderConfigurationError:
        raise HTTPException(status_code=503, detail="Avatar generation is unavailable")
    except ValueError:
        raise HTTPException(status_code=404, detail="Student not found")
    except GenerationConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# COMIC CREATION ENDPOINTS
# ============================================


def _run_story_generation(run_id: str) -> None:
    run_generation(run_id)


def _run_panel_regeneration(run_id: str) -> None:
    run_panel_regeneration(run_id)


def _cleanup_generation_paths(run_id: str, paths: list[str]) -> list[str]:
    from database.database import replace_generation_artifacts

    storage = LocalStorage(resolve_local_paths().root)
    remaining = []
    for path in paths:
        try:
            storage.delete(path)
        except Exception:
            remaining.append(path)
    replace_generation_artifacts(run_id, remaining)
    return remaining


@app.post("/generation-runs/{run_id}/resume", status_code=202)
async def resume_story_generation(run_id: UUID, background_tasks: BackgroundTasks):
    from database.database import GenerationConflict, resume_generation_run

    try:
        run, created = resume_generation_run(str(run_id))
        if created:
            background_tasks.add_task(_run_story_generation, run["id"])
        return {
            "run_id": run["id"],
            "chapter_id": run["chapter_id"],
            "status": "generating",
            "resumed": created,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Generation run not found")
    except GenerationConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/generation-runs/{run_id}/discard")
async def discard_story_generation(run_id: UUID, confirm: bool = False):
    from database.database import (
        GenerationConflict,
        discard_generation_run,
        replace_generation_artifacts,
    )

    if not confirm:
        raise HTTPException(status_code=400, detail="Discard requires explicit confirmation")
    try:
        paths = discard_generation_run(str(run_id))
        remaining = _cleanup_generation_paths(str(run_id), paths)
        if remaining:
            raise HTTPException(status_code=409, detail="Checkpoint cleanup is incomplete; retry discard")
        return {"success": True, "run_id": str(run_id)}
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=404, detail="Generation run not found")
    except GenerationConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/chapters/commit")
async def commit_chapter_endpoint(
    request: CommitStoryRequest, background_tasks: BackgroundTasks
):
    """
    Commit a chosen story idea and generate full chapter with comic panels.

    This endpoint starts the generation process in the background and returns immediately.
    The frontend should poll GET /chapters/{chapter_id} to track progress by checking
    the panels array length.

    This endpoint:
    1. Takes a chapter with story ideas (created earlier)
    2. Generates a full script based on the chosen idea (in background)
    3. Creates comic panel images using FLUX (in background)
    4. Stores everything in the database as panels are created

    Args:
        request: Contains chapter_id and chosen_idea_id (e.g., "idea_1")
        background_tasks: FastAPI background task manager

    Returns:
        Immediate success response - use polling to track progress
    """
    from database.database import GenerationConflict, begin_generation_run, get_chapter

    try:
        # Verify chapter exists
        chapter_id = str(request.chapter_id)
        chapter = get_chapter(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        ideas = {idea.get("id") for idea in chapter.get("story_ideas") or []}
        if request.chosen_idea_id not in ideas or chapter.get("chosen_idea_id") != request.chosen_idea_id:
            raise HTTPException(status_code=400, detail="Story choice is invalid")
        idempotency_key = request.idempotency_key or f"legacy-{chapter_id}-{chapter['revision'] + 1}"
        run, created = begin_generation_run(chapter_id, request.chosen_idea_id, idempotency_key)

        if created:
            background_tasks.add_task(_run_story_generation, run["id"])

        return {
            "success": True,
            "message": "Comic generation started" if created else "Comic generation request already exists",
            "chapter_id": chapter_id,
            "run_id": run["id"],
            "status": {"succeeded": "ready", "failed": "failed"}.get(run["job_state"], "generating"),
        }
    except HTTPException:
        raise
    except GenerationConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError:
        raise HTTPException(status_code=400, detail="Story choice is invalid")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/classrooms/{classroom_id}/chapters/start")
async def start_chapter_endpoint(
    classroom_id: UUID, request: LessonPromptRequest, background_tasks: BackgroundTasks
):
    """
    Start a new chapter by generating story options.

    Args:
        classroom_id: UUID of the classroom
        lesson_prompt: Teacher's lesson description

    Returns:
        Created chapter with story options
    """
    from database.database import (
        begin_story_options,
        complete_story_options,
        fail_story_options,
        get_chapters_by_classroom,
        get_classroom,
        get_students_by_ids,
    )
    from services.story_idea import generate_story_ideas

    try:
        classroom_id = str(classroom_id)
        lesson_prompt = request.lesson_prompt
        # Get classroom and students
        classroom = get_classroom(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")

        # Get next chapter index - use max index + 1 to handle gaps
        existing_chapters = get_chapters_by_classroom(classroom_id)
        if existing_chapters:
            next_index = max(ch.get("index", 0) for ch in existing_chapters) + 1
        else:
            next_index = 1

        selected_material_ids = [str(material_id) for material_id in request.material_ids]
        chapter = (
            begin_story_options(classroom_id, next_index, lesson_prompt, selected_material_ids)
            if selected_material_ids
            else begin_story_options(classroom_id, next_index, lesson_prompt)
        )
        try:
            students = get_students_by_ids(chapter["option_student_ids"])
            provider_args = {
                "model": chapter["option_settings_snapshot"]["openai_model"]
            }
            if chapter.get("grounded_sources"):
                provider_args["materials"] = chapter["grounded_sources"]
            story_ideas = generate_story_ideas(classroom, students, lesson_prompt, **provider_args)
        except Exception:
            fail_story_options(chapter["id"])
            raise

        # Format story ideas with IDs
        formatted_ideas = []
        for idx, idea in enumerate(story_ideas, 1):
            formatted_ideas.append(
                {
                    "id": f"idea_{idx}",
                    "title": idea.get("title", ""),
                    "summary": idea.get("summary", ""),
                    "theme": classroom.get("story_theme", ""),
                    "preview_status": "pending",
                }
            )

        chapter = complete_story_options(chapter["id"], formatted_ideas)
        background_tasks.add_task(run_story_previews_for_chapter, chapter["id"])

        return {"success": True, "chapter": chapter}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/chapters/{chapter_id}/choose-idea")
async def choose_story_idea(chapter_id: UUID, request: StoryChoiceRequest):
    """
    Teacher chooses a story idea for the chapter.

    Args:
        chapter_id: UUID of the chapter
        idea_id: ID of the chosen story idea

    Returns:
        Updated chapter
    """
    from database.database import choose_chapter_idea, get_chapter

    try:
        chapter_id = str(chapter_id)
        idea_id = request.idea_id
        # Verify chapter exists
        chapter = get_chapter(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        if idea_id not in {idea.get("id") for idea in chapter.get("story_ideas") or []}:
            raise HTTPException(status_code=400, detail="Story choice is invalid")

        updated = choose_chapter_idea(chapter_id, idea_id)
        if not updated:
            raise HTTPException(status_code=409, detail="Chapter cannot be changed in its current state")

        return {"success": True, "chapter": updated}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/chapters/{chapter_id}")
async def get_chapter_with_panels_endpoint(chapter_id: UUID):
    """
    Get a chapter with all its panels.

    Args:
        chapter_id: UUID of the chapter

    Returns:
        Chapter record with nested panels array
    """
    from database.database import get_chapter_with_panels

    try:
        chapter = get_chapter_with_panels(str(chapter_id))
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        return {"success": True, "chapter": chapter}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/chapters/{chapter_id}")
async def delete_chapter_endpoint(chapter_id: UUID, confirm: bool = False):
    """
    Delete a chapter and all its panels.

    Args:
        chapter_id: UUID of the chapter to delete

    Returns:
        Success message
    """
    from database.database import execute_deletion

    try:
        chapter_id = str(chapter_id)
        if not confirm:
            raise HTTPException(status_code=400, detail="Deletion requires explicit confirmation")
        if not execute_deletion("chapter", chapter_id):
            raise HTTPException(status_code=409, detail="Local file cleanup is incomplete; retry deletion")
        return {"success": True, "message": "Chapter deleted"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post(
    "/chapters/{chapter_id}/story-ideas/{idea_id}/preview/retry",
    status_code=202,
)
async def retry_story_preview(
    chapter_id: UUID,
    idea_id: str,
    _request: StoryPreviewRetryRequest,
    background_tasks: BackgroundTasks,
):
    from database.database import GenerationConflict, begin_story_previews, get_chapter

    if idea_id not in {"idea_1", "idea_2", "idea_3"}:
        raise HTTPException(status_code=422, detail="Story preview choice is invalid")
    try:
        jobs = begin_story_previews(str(chapter_id), [idea_id])
        if not jobs:
            raise HTTPException(status_code=409, detail="Story preview is already active or ready")
        background_tasks.add_task(run_story_previews, jobs)
        return {"success": True, "chapter": get_chapter(str(chapter_id))}
    except HTTPException:
        raise
    except GenerationConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        status_code = 404 if str(exc) == "Chapter not found" else 400
        raise HTTPException(status_code=status_code, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/chapters/{chapter_id}/panels/{panel_number}/regenerate", status_code=202)
async def regenerate_panel_endpoint(
    chapter_id: UUID,
    panel_number: int,
    request: PanelRegenerationRequest,
    background_tasks: BackgroundTasks,
):
    from database.database import GenerationConflict, begin_panel_regeneration

    try:
        run, created = begin_panel_regeneration(
            str(chapter_id),
            panel_number,
            request.expected_revision,
            request.correction,
            request.idempotency_key,
        )
        if created:
            background_tasks.add_task(_run_panel_regeneration, run["id"])
        return _panel_regeneration_status(run)
    except GenerationConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        status_code = 404 if str(exc) in {"Chapter not found", "Panel not found"} else 400
        raise HTTPException(status_code=status_code, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/panel-regenerations/{run_id}")
async def get_panel_regeneration_endpoint(run_id: UUID):
    from database.database import get_generation_run

    run = get_generation_run(str(run_id))
    if run is None or run["run_kind"] != "panel":
        raise HTTPException(status_code=404, detail="Panel regeneration not found")
    return _panel_regeneration_status(run)


def _panel_regeneration_status(run: dict) -> dict:
    status = "candidate_ready" if run["stage"] == "candidate_ready" else {
        "succeeded": "ready", "failed": "failed"
    }.get(run["job_state"], "regenerating")
    return {
        "run_id": run["id"],
        "chapter_id": run["chapter_id"],
        "panel_number": run["panel_number"],
        "status": status,
        "candidate_url": media_url(run["candidate_object_path"]) if run["candidate_object_path"] else None,
        "reported_bfl_cost": run["reported_bfl_cost"] or None,
        "error_code": run["error_code"],
        "error_reference": run["error_reference"],
        "cleanup_pending": run["cleanup_pending"],
    }


@app.post("/panel-regenerations/{run_id}/accept")
async def accept_panel_regeneration_endpoint(run_id: UUID):
    from database.database import GenerationConflict, accept_panel_regeneration, get_generation_run

    try:
        paths = accept_panel_regeneration(str(run_id))
        if _cleanup_generation_paths(str(run_id), paths):
            raise HTTPException(status_code=409, detail="Panel cleanup is incomplete; retry accept")
        return _panel_regeneration_status(get_generation_run(str(run_id)))
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=404, detail="Panel regeneration not found")
    except GenerationConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/panel-regenerations/{run_id}/reject")
async def reject_panel_regeneration_endpoint(run_id: UUID):
    from database.database import GenerationConflict, get_generation_run, reject_panel_regeneration

    try:
        paths = reject_panel_regeneration(str(run_id))
        if _cleanup_generation_paths(str(run_id), paths):
            raise HTTPException(status_code=409, detail="Panel cleanup is incomplete; retry reject")
        return _panel_regeneration_status(get_generation_run(str(run_id)))
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=404, detail="Panel regeneration not found")
    except GenerationConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/settings")
async def get_settings_endpoint():
    from database.database import get_settings

    settings = get_settings()
    return {
        "success": True,
        "settings": settings,
        "provider_readiness": {
            "openai": configured_secret("OPENAI_API_KEY"),
            "bfl": configured_secret("BFL_API_KEY"),
        },
        "local_data": "Stored only on this device",
    }


@app.patch("/settings")
async def update_settings_endpoint(request: SettingsUpdateRequest):
    from database.database import update_settings

    return {"success": True, "settings": update_settings(request.model_dump(exclude_none=True))}


@app.post("/settings/reset-local-data")
async def reset_local_data_endpoint(confirm: bool = False):
    from database.database import execute_deletion

    if not confirm:
        raise HTTPException(status_code=400, detail="Reset requires explicit confirmation")
    if not execute_deletion("reset"):
        raise HTTPException(status_code=409, detail="Local file cleanup is incomplete; retry reset")
    return {"success": True, "message": "Local application data reset"}


@app.get("/students/{student_id}/chapters")
async def get_student_chapters(student_id: UUID):
    """
    Get all chapters across all classrooms a student is enrolled in.

    Args:
        student_id: UUID of the student

    Returns:
        List of chapter records with classroom info
    """
    from database.database import (
        get_chapters_by_classroom,
        get_classrooms_by_student,
    )

    try:
        # Get all classrooms the student is enrolled in
        classrooms = get_classrooms_by_student(str(student_id))

        # Collect all chapters from all classrooms
        all_chapters = []
        for classroom in classrooms:
            chapters = get_chapters_by_classroom(classroom["id"])
            # Add classroom info to each chapter
            for chapter in chapters:
                chapter["classroom_name"] = classroom["name"]
                chapter["classroom_subject"] = classroom.get("subject", "")
                all_chapters.append(chapter)

        # Sort by created_at descending (newest first)
        all_chapters.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {"success": True, "chapters": all_chapters}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

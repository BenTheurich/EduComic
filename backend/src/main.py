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
    StoryChoiceRequest,
    StudentCreateRequest,
    StudentUpdateRequest,
    SettingsUpdateRequest,
)
from local_runtime import initialize_local_backend, local_readiness_details, resolve_local_paths
from local_storage import LocalStorage, StorageValidationError
from services.avatar import ProviderConfigurationError, generate_avatar
from services.generation import run_generation

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

    def configured_secret(name: str) -> bool:
        value = os.getenv(name, "").strip()
        return bool(value and not value.startswith("<") and not value.startswith("YOUR_"))

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
    return {"success": True, "message": "Student profile and personal data erased"}


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
async def leave_classroom(student_id: UUID, classroom_id: UUID):
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
        success = remove_student_from_classroom(str(student_id), str(classroom_id))
        return {"success": True, "removed": success, "message": "Student removed from classroom"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/avatar/create/{student_id}")
async def create_avatar_endpoint(student_id: UUID):
    """
    Generate an avatar for a student.

    Args:
        student_id: UUID of the student

    Returns:
        Updated student record with avatar_url
    """
    try:
        student = await generate_avatar(str(student_id))
        return {"success": True, "student": student}
    except ProviderConfigurationError:
        raise HTTPException(status_code=503, detail="Avatar generation is unavailable")
    except ValueError:
        raise HTTPException(status_code=404, detail="Student not found")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# COMIC CREATION ENDPOINTS
# ============================================


def _run_story_generation(run_id: str) -> None:
    run_generation(run_id)


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
    classroom_id: UUID, request: LessonPromptRequest
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
        get_chapters_by_classroom,
        get_classroom,
        get_students_by_classroom,
        create_chapter,
    )
    from services.story_idea import generate_story_ideas

    try:
        classroom_id = str(classroom_id)
        lesson_prompt = request.lesson_prompt
        # Get classroom and students
        classroom = get_classroom(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")

        students = get_students_by_classroom(classroom_id)

        # Get next chapter index - use max index + 1 to handle gaps
        existing_chapters = get_chapters_by_classroom(classroom_id)
        if existing_chapters:
            next_index = max(ch.get("index", 0) for ch in existing_chapters) + 1
        else:
            next_index = 1

        # Generate story ideas
        story_ideas = generate_story_ideas(classroom, students, lesson_prompt)

        # Format story ideas with IDs
        formatted_ideas = []
        for idx, idea in enumerate(story_ideas, 1):
            formatted_ideas.append(
                {
                    "id": f"idea_{idx}",
                    "title": idea.get("title", ""),
                    "summary": idea.get("summary", ""),
                    "theme": classroom.get("story_theme", ""),
                }
            )

        # Create chapter directly with correct schema
        data = {
            "classroom_id": classroom_id,
            "index": next_index,
            "original_prompt": lesson_prompt,
            "story_ideas": formatted_ideas,
            "status": "options_generated",
        }

        chapter = create_chapter(data)

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


@app.get("/settings")
async def get_settings_endpoint():
    from database.database import get_settings

    settings = get_settings()
    return {
        "success": True,
        "settings": settings,
        "provider_readiness": {
            "openai": bool(os.getenv("OPENAI_API_KEY", "").strip()),
            "bfl": bool(os.getenv("BFL_API_KEY", "").strip()),
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

"""
FastAPI main application entry point.
"""

import logging
import os
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api_models import (
    ClassroomCreateRequest,
    CommitStoryRequest,
    LessonPromptRequest,
    StoryChoiceRequest,
    StudentCreateRequest,
)
from services.avatar import generate_avatar
from services.comic_creation import commit_story_choice
from services.story_idea import start_chapter

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="EduComic API",
    description="API for educational comic generation",
    version="1.0.0",
)

logger = logging.getLogger("educomic.api")


def _allowed_origins() -> list[str]:
    configured = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
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
    """Report whether the configuration required for work is present."""
    required = ("SUPABASE_URL", "SUPABASE_KEY", "OPENAI_API_KEY")
    missing = [name for name in required if not os.getenv(name)]
    if not os.getenv("BFL_API_KEY"):
        missing.append("BFL_API_KEY")
    if missing:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "missing_configuration": missing},
        )
    return {"status": "ready"}


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
    Create a new student account (without classroom).
    Photo must be uploaded first, then this endpoint creates the student.

    Args:
        name: Student's full name
        interests: Student's interests/hobbies
        photo_url: URL to student's photo (should be uploaded first)

    Returns:
        Created student record
    """
    from database.database import supabase

    try:
        student_data = {
            "name": request.name,
            "interests": request.interests,
            "photo_url": str(request.photo_url) if request.photo_url else None,
        }

        response = supabase.table("students").insert(student_data).execute()

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create student")

        return {"success": True, "student": response.data[0]}
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


@app.post("/students/upload-photo")
async def upload_student_photo(
    file: UploadFile = File(...),
    filename: str = Form(
        ..., min_length=1, max_length=255, pattern=r"^.*\S.*$"
    ),
):
    """
    Upload a student photo to Supabase storage.

    Args:
        file: Photo file upload
        filename: Name of the file

    Returns:
        Public URL of the uploaded photo
    """
    import uuid

    from database.database import supabase

    try:
        # Validate file type
        allowed_types = [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/webp",
        ]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(allowed_types)}",
            )

        # Read file content
        file_content = await file.read()

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {len(file_content)} bytes. Max: {max_size} bytes (10MB)",
            )

        # Generate unique filename
        file_ext = filename.split(".")[-1] if "." in filename else "jpg"
        unique_filename = f"{uuid.uuid4()}.{file_ext}"

        # Upload to Supabase storage
        try:
            response = supabase.storage.from_("StudentPhotos").upload(
                unique_filename,
                file_content,
                {"content-type": file.content_type or f"image/{file_ext}"},
            )

            # Check for upload errors
            if hasattr(response, "error") and response.error:
                raise Exception(f"Supabase upload error: {response.error}")

        except Exception:
            raise HTTPException(status_code=500, detail="Internal server error")

        # Get public URL
        public_url = supabase.storage.from_("StudentPhotos").get_public_url(
            unique_filename
        )

        return {"success": True, "photo_url": public_url}
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
    from database.database import supabase

    try:
        response = (
            supabase.table("students")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return {"success": True, "students": response.data}
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
        if not success:
            raise HTTPException(status_code=404, detail="Enrollment not found")

        return {"success": True, "message": "Student left classroom successfully"}
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
    except ValueError:
        raise HTTPException(status_code=404, detail="Student not found")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/story/generate-options")
async def generate_story_options_endpoint(
    classroom_id: str = Query(...), lesson_prompt: str = Query(...)
):
    """
    Generate 3 story options based on teacher's prompt.

    Args:
        classroom_id: UUID of the classroom
        lesson_prompt: Teacher's description of the lesson

    Returns:
        List of 3 story options with id, title, summary, theme
    """
    from database.database import get_classroom, get_students_by_classroom
    from services.story_idea import generate_story_ideas

    try:
        # Get classroom and students
        classroom = get_classroom(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")

        students = get_students_by_classroom(classroom_id)

        # Generate story ideas
        story_ideas = generate_story_ideas(classroom, students, lesson_prompt)

        # Format story ideas with IDs
        formatted_options = []
        for idx, idea in enumerate(story_ideas, 1):
            formatted_options.append(
                {
                    "id": f"idea_{idx}",
                    "title": idea.get("title", ""),
                    "summary": idea.get("summary", ""),
                    "theme": classroom.get("story_theme", ""),
                }
            )

        return {"success": True, "options": formatted_options}
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Story options could not be generated")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/story/create/{classroom_id}")
async def create_story_endpoint(classroom_id: UUID):
    """
    Create a story for a classroom.

    Args:
        classroom_id: UUID of the classroom

    Returns:
        Created story record
    """
    try:
        # TODO: Implement story creation logic
        return {
            "success": True,
            "message": f"Story creation for classroom {classroom_id} not yet implemented",
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Classroom not found")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# COMIC CREATION ENDPOINTS
# ============================================


class GenerateIdeasRequest(BaseModel):
    classroom_id: str
    teacher_outline: str


@app.post("/chapters/ideas")
async def generate_ideas_endpoint(request: GenerateIdeasRequest):
    """
    Generate 3 story ideas for a new chapter.

    This endpoint:
    1. Fetches classroom and student data
    2. Calls OpenAI to generate 3 story ideas based on teacher's outline
    3. Creates a chapter record with ideas stored in JSON
    4. Returns the chapter ID and ideas for teacher to choose from

    Args:
        request: Contains classroom_id and teacher_outline

    Returns:
        Chapter ID and 3 story ideas
    """
    try:
        result = start_chapter(request.classroom_id, request.teacher_outline)
        return {"success": True, "data": result}
    except ValueError:
        raise HTTPException(status_code=400, detail="Story ideas could not be generated")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


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
    from database.database import get_chapter, supabase

    try:
        # Verify chapter exists
        chapter_id = str(request.chapter_id)
        chapter = get_chapter(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        # Update status to indicate generation has started
        supabase.table("chapters").update({"status": "generating"}).eq(
            "id", chapter_id
        ).execute()

        # Start the actual comic generation in the background
        background_tasks.add_task(
            commit_story_choice, chapter_id, request.chosen_idea_id
        )

        return {
            "success": True,
            "message": "Comic generation started",
            "chapter_id": chapter_id,
            "status": "generating",
        }
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Story choice is invalid")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/classrooms/{classroom_id}/materials")
async def get_classroom_materials(classroom_id: UUID):
    """
    Get all materials for a classroom.

    Args:
        classroom_id: UUID of the classroom

    Returns:
        List of material records
    """
    from database.database import get_materials_by_classroom

    try:
        materials = get_materials_by_classroom(str(classroom_id))
        return {"success": True, "materials": materials}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/classrooms/{classroom_id}/materials/upload")
async def upload_material(
    classroom_id: UUID,
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=200, pattern=r"^.*\S.*$"),
    description: str = Form(None, max_length=2000),
    week_number: int = Form(None, ge=1, le=52),
):
    """
    Upload a material file for a classroom.

    Args:
        classroom_id: UUID of the classroom
        file: PDF file upload
        title: Title of the material
        description: Optional description
        week_number: Optional week number

    Returns:
        Created material record
    """
    import uuid

    from database.database import create_material, get_classroom, supabase

    try:
        classroom_id = str(classroom_id)
        # Verify classroom exists
        classroom = get_classroom(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")

        # Validate file type (PDF only)
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Only PDF files are allowed.",
            )

        # Read file content
        file_content = await file.read()

        # Validate file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {len(file_content)} bytes. Max: {max_size} bytes (50MB)",
            )

        # Generate unique filename
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
        unique_filename = f"{classroom_id}/{uuid.uuid4()}.{file_ext}"

        # Upload to Supabase storage in Materials bucket
        try:
            storage_response = supabase.storage.from_("Materials").upload(
                unique_filename,
                file_content,
                {
                    "content-type": file.content_type or "application/pdf",
                    "cache-control": "3600",
                },
            )

            # Check for upload errors
            if hasattr(storage_response, "error") and storage_response.error:
                raise Exception(f"Supabase upload error: {storage_response.error}")

        except Exception:
            raise HTTPException(status_code=500, detail="Internal server error")

        # Get public URL
        public_url = supabase.storage.from_("Materials").get_public_url(unique_filename)

        # Create material record in database
        material = create_material(
            classroom_id=classroom_id,
            title=title,
            file_url=public_url,
            file_type=file.content_type,
            description=description,
            week_number=week_number,
        )

        return {"success": True, "material": material}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/materials/{material_id}")
async def delete_material_endpoint(material_id: UUID):
    """
    Delete a material.

    Args:
        material_id: UUID of the material

    Returns:
        Success message
    """
    from database.database import delete_material, get_material, supabase

    try:
        # Get material to find file URL
        material_id = str(material_id)
        material = get_material(material_id)
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")

        # Extract filename from URL and delete from storage
        try:
            file_url = material.get("file_url", "")
            # Extract path from URL (after /Materials/)
            if "/Materials/" in file_url:
                file_path = file_url.split("/Materials/")[-1]
                supabase.storage.from_("Materials").remove([file_path])
        except Exception:
            # Continue with database deletion even if storage deletion fails
            pass

        # Delete from database
        success = delete_material(material_id)
        if not success:
            raise HTTPException(status_code=404, detail="Material not found")

        return {"success": True, "message": "Material deleted successfully"}

    except HTTPException:
        raise
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
        supabase,
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

        response = supabase.table("chapters").insert(data).execute()
        chapter = response.data[0] if response.data else None

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
    from database.database import get_chapter, supabase

    try:
        chapter_id = str(chapter_id)
        idea_id = request.idea_id
        # Verify chapter exists
        chapter = get_chapter(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        update_data = {"chosen_idea_id": idea_id, "status": "idea_chosen"}

        response = (
            supabase.table("chapters")
            .update(update_data)
            .eq("id", chapter_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update chapter")

        return {"success": True, "chapter": response.data[0]}

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
async def delete_chapter_endpoint(chapter_id: UUID):
    """
    Delete a chapter and all its panels.

    Args:
        chapter_id: UUID of the chapter to delete

    Returns:
        Success message
    """
    from database.database import delete_chapter, get_chapter

    try:
        # Verify chapter exists
        chapter_id = str(chapter_id)
        chapter = get_chapter(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        # Delete the chapter (cascades to panels)
        success = delete_chapter(chapter_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete chapter")

        return {"success": True, "message": "Chapter deleted successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


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

"""Validated request bodies for active API workflows."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, StringConstraints, UrlConstraints

ShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
LongText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
IdeaId = Annotated[str, StringConstraints(pattern=r"^idea_[1-3]$")]
BoundedHttpUrl = Annotated[AnyHttpUrl, UrlConstraints(max_length=2048)]


class ClassroomCreateRequest(BaseModel):
    name: ShortText
    subject: ShortText
    grade_level: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)
    ]
    story_theme: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    design_style: Literal["manga", "comic", "cartoon"]


class StudentCreateRequest(BaseModel):
    name: ShortText
    interests: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    photo_url: BoundedHttpUrl | None = None


class LessonPromptRequest(BaseModel):
    lesson_prompt: LongText


class StoryChoiceRequest(BaseModel):
    idea_id: IdeaId


class CommitStoryRequest(BaseModel):
    chapter_id: UUID
    chosen_idea_id: IdeaId

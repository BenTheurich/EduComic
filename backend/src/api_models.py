"""Validated request bodies for active API workflows."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
LongText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
IdeaId = Annotated[str, StringConstraints(pattern=r"^idea_[1-3]$")]
IdempotencyKey = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]


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


class ClassroomUpdateRequest(ClassroomCreateRequest):
    pass


class StudentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: UUID | None = None
    name: ShortText
    interests: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    classroom_id: UUID | None = None


class StudentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ShortText
    interests: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]


class SettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    story_length: Literal[12, 20] | None = None
    default_design_style: Literal["manga", "comic", "cartoon"] | None = None
    openai_model: Literal["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"] | None = None
    bfl_model: Literal["flux-2-pro"] | None = None
    automatic_panel_review: bool | None = None
    panel_review_attempt_cap: Literal[1, 2, 3] | None = None
    reader_preferences: dict[str, bool] | None = None


class LessonPromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lesson_prompt: LongText
    material_ids: list[UUID] = Field(default_factory=list, max_length=10)


class StoryChoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idea_id: IdeaId


class CommitStoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_id: UUID
    chosen_idea_id: IdeaId
    idempotency_key: IdempotencyKey | None = None

"""Strict schemas for untrusted story-provider output."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationInfo, field_validator, model_validator


def _text(max_length: int) -> Any:
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class StoryIdea(_StrictModel):
    title: _text(120)
    summary: _text(600)


class StoryIdeasResponse(_StrictModel):
    ideas: list[StoryIdea] = Field(min_length=3, max_length=3)


class DialogueLine(_StrictModel):
    speaker: _text(120)
    text: _text(240)

    @field_validator("text")
    @classmethod
    def limit_words(cls, value: str) -> str:
        if len(value.split()) > 10:
            raise ValueError("dialogue must contain at most 10 words")
        return value


class ComicPanel(_StrictModel):
    index: int = Field(ge=1, le=12)
    setting: _text(300)
    description: _text(1200)
    narration: Annotated[str, StringConstraints(strip_whitespace=True, max_length=240)]
    dialogue: list[DialogueLine] = Field(max_length=2)
    featured_students: list[_text(120)] = Field(max_length=12)

    @field_validator("narration")
    @classmethod
    def limit_narration_words(cls, value: str) -> str:
        if len(value.split()) > 10:
            raise ValueError("narration must contain at most 10 words")
        return value


class ComicScript(_StrictModel):
    episode_title: _text(160)
    learning_objectives: list[_text(240)] = Field(min_length=1, max_length=5)
    panels: list[ComicPanel] = Field(min_length=8, max_length=12)

    @model_validator(mode="after")
    def validate_sequence_and_cast(self, info: ValidationInfo) -> "ComicScript":
        if [panel.index for panel in self.panels] != list(range(1, len(self.panels) + 1)):
            raise ValueError("panel indices must be the exact sequence 1..N")

        if info.context is None:
            return self
        known_students = set(info.context.get("student_names", ()))

        allowed_speakers = known_students | {"Teacher", "Narrator"}
        for panel in self.panels:
            if len(panel.featured_students) != len(set(panel.featured_students)):
                raise ValueError("featured students must not contain duplicates")
            unknown_students = set(panel.featured_students) - known_students
            if unknown_students:
                raise ValueError("featured students must be known classroom students")
            if any(line.speaker not in allowed_speakers for line in panel.dialogue):
                raise ValueError("dialogue speakers must be known students, Teacher, or Narrator")
            if any(
                line.speaker in known_students and line.speaker not in panel.featured_students
                for line in panel.dialogue
            ):
                raise ValueError("student speakers must be featured in their panel")
        return self


class ReviewDimensions(_StrictModel):
    text_accuracy: float = Field(ge=0, le=10)
    character_accuracy: float = Field(ge=0, le=10)
    layout_readability: float = Field(ge=0, le=10)


class PanelReview(_StrictModel):
    score: float = Field(ge=0, le=10)
    dimensions: ReviewDimensions
    issues: list[_text(400)] = Field(max_length=12)
    suggested_fix_prompt: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]

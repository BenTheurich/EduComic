"""Strict schemas for untrusted story-provider output."""

from typing import Annotated, Any, Literal

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
        if len(value.split()) > 8:
            raise ValueError("dialogue must contain at most 8 words")
        return value


class ComicPanel(_StrictModel):
    index: int = Field(ge=1, le=20)
    setting: _text(300)
    description: _text(700)
    narration: Annotated[str, StringConstraints(strip_whitespace=True, max_length=240)]
    dialogue: list[DialogueLine] = Field(max_length=2)
    featured_students: list[_text(120)] = Field(max_length=4)

    @field_validator("narration")
    @classmethod
    def limit_narration_words(cls, value: str) -> str:
        if len(value.split()) > 8:
            raise ValueError("narration must contain at most 8 words")
        return value

    @model_validator(mode="after")
    def limit_visible_text_regions(self) -> "ComicPanel":
        if bool(self.narration) + len(self.dialogue) > 2:
            raise ValueError("a panel may contain at most two visible text regions")
        return self


class ComicScript(_StrictModel):
    episode_title: _text(160)
    learning_objectives: list[_text(240)] = Field(min_length=1, max_length=5)
    panels: list[ComicPanel] = Field(min_length=12, max_length=20)

    @model_validator(mode="after")
    def validate_sequence_and_cast(self, info: ValidationInfo) -> "ComicScript":
        if [panel.index for panel in self.panels] != list(range(1, len(self.panels) + 1)):
            raise ValueError("panel indices must be the exact sequence 1..N")

        if info.context is None:
            return self
        panel_count = info.context.get("panel_count")
        if panel_count is not None and len(self.panels) != panel_count:
            raise ValueError(f"comic script must contain exactly {panel_count} panels")
        known_students = set(info.context.get("student_names", ()))

        allowed_speakers = known_students | {"Teacher"}
        featured_cast = {name for panel in self.panels for name in panel.featured_students}
        if len(featured_cast) > 4:
            raise ValueError("a comic may feature at most four students")
        for panel in self.panels:
            if len(panel.featured_students) != len(set(panel.featured_students)):
                raise ValueError("featured students must not contain duplicates")
            unknown_students = set(panel.featured_students) - known_students
            if unknown_students:
                raise ValueError("featured students must be known classroom students")
            if any(line.speaker not in allowed_speakers for line in panel.dialogue):
                raise ValueError("dialogue speakers must be known students or Teacher")
            if any(
                line.speaker in known_students and line.speaker not in panel.featured_students
                for line in panel.dialogue
            ):
                raise ValueError("student speakers must be featured in their panel")
        return self


class ReviewDimensions(_StrictModel):
    bubble_ownership: bool
    reference_identity_continuity: bool
    requested_action: bool
    layout_readability: bool


class VisibleTextObservation(_StrictModel):
    kind: Literal["narration", "dialogue", "other"]
    text: _text(240)


class PanelReview(_StrictModel):
    score: float = Field(ge=0, le=10)
    visible_text: list[VisibleTextObservation] = Field(max_length=12)
    dimensions: ReviewDimensions
    issues: list[_text(400)] = Field(max_length=12)
    suggested_fix_prompt: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]

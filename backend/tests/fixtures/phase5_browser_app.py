"""Fictional provider double used only by the Phase 5 browser acceptance pass."""

import sys
from pathlib import Path

import uvicorn


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from services import story_idea  # noqa: E402


def fictional_story_ideas(_classroom, _students, _outline, *, model, materials=None):
    grounded = bool(materials)
    return [
        {
            "title": f"Luma Lesson {index}" if grounded else f"Open Lesson {index}",
            "summary": "A fictional story grounded in the selected lesson PDF." if grounded else "A fictional story.",
        }
        for index in range(1, 4)
    ]


story_idea.generate_story_ideas = fictional_story_ideas

from main import app  # noqa: E402


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

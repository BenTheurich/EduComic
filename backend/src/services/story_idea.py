"""Generate three grounded story ideas for a chapter-start request."""

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from materials import UNTRUSTED_SOURCE_SYSTEM_RULE, grounding_prompt
from provider_clients import LazyClient
from provider_config import DEFAULT_OPENAI_MODEL, SUPPORTED_OPENAI_MODELS, require_supported_model
from story_contracts import StoryIdeasResponse


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
openai_client = LazyClient(lambda: OpenAI(api_key=OPENAI_API_KEY))


def _classroom_context_dict(
    classroom: Dict[str, Any], students: List[Dict[str, Any]], teacher_outline: str
) -> Dict[str, Any]:
    return {
        "classroom": {
            "name": classroom["name"],
            "subject": classroom["subject"],
            "grade_level": classroom["grade_level"],
            "story_theme": classroom["story_theme"],
            "design_style": classroom["design_style"],
            "duration": classroom["duration"],
        },
        "students": [{"name": student["name"], "interests": student.get("interests", "")} for student in students],
        "teacher_outline": teacher_outline,
    }


def generate_story_ideas(
    classroom: Dict[str, Any],
    students: List[Dict[str, Any],],
    teacher_outline: str,
    *,
    model: str = DEFAULT_OPENAI_MODEL,
    materials: list[dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Return exactly three age-appropriate, structured chapter ideas."""
    model = require_supported_model(model, SUPPORTED_OPENAI_MODELS, "OpenAI")
    payload = _classroom_context_dict(classroom, students, teacher_outline)
    response = openai_client.chat.completions.parse(
        model=model,
        response_format=StoryIdeasResponse,
        max_completion_tokens=2048,
        messages=[
            {
                "role": "system",
                "content": (
                    "Create three distinct, fun educational comic ideas using language suitable for the classroom grade level. "
                    "Make every idea teach the teacher's outline and selected materials, with varied student combinations. "
                    f"{UNTRUSTED_SOURCE_SYSTEM_RULE}"
                ),
            },
            {
                "role": "user",
                "content": (
                    "Create exactly three chapter ideas. Give each a short title and a 2-3 sentence summary; "
                    "keep the learning concrete, age-appropriate, and personal to the named students.\n\n"
                    f"CONTEXT:\n{json.dumps(payload, ensure_ascii=False)}"
                    f"\n\n{grounding_prompt(materials or [])}"
                ),
            },
        ],
    )
    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no validated story ideas")
    return [{"id": f"idea_{index}", **idea.model_dump()} for index, idea in enumerate(parsed.ideas, start=1)]

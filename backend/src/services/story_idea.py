"""Generate story ideas for the active chapter-start route."""

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.1")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
    print("[WARN] OPENAI_API_KEY not set; OpenAI calls will fail until you configure it.")


def _classroom_context_dict(
    classroom: Dict[str, Any],
    students: List[Dict[str, Any]],
    teacher_outline: str,
) -> Dict[str, Any]:
    """Compact JSON context that we send to OpenAI."""
    return {
        "classroom": {
            "id": classroom["id"],
            "name": classroom["name"],
            "subject": classroom["subject"],
            "grade_level": classroom["grade_level"],
            "story_theme": classroom["story_theme"],
            "design_style": classroom["design_style"],
            "duration": classroom["duration"],
        },
        "students": [
            {
                "name": s["name"],
                "interests": s.get("interests", ""),
                "avatar_url": s.get("avatar_url"),
            }
            for s in students
        ],
        "teacher_outline": teacher_outline,
    }


def generate_story_ideas(
    classroom: Dict[str, Any],
    students: List[Dict[str, Any]],
    teacher_outline: str,
) -> List[Dict[str, Any]]:
    """
    Ask OpenAI for 3 story ideas for this classroom + outline.

    Returns:
      [
        {"id": "idea_1", "title": "...", "summary": "..."},
        {"id": "idea_2", ...},
        {"id": "idea_3", ...}
      ]
    """
    payload = _classroom_context_dict(classroom, students, teacher_outline)

    system_prompt = (
        "You create fun, age-appropriate ideas for short educational comic chapters "
        "for kids roughly between 6 and 16 years old. Always respond with a single JSON object."
    )

    user_prompt = (
        "You are given classroom and student info plus a short outline from the teacher.\n"
        "Propose exactly 3 different comic chapter ideas that match the outline and help "
        "students learn the subject.\n\n"
        "IMPORTANT: Each idea should feature different students or combinations of students from the class. "
        "Use their names and interests to make the stories personal and engaging. "
        "Vary which students are featured across the 3 ideas.\n\n"
        "Return ONLY a JSON object with this structure (no extra text):\n"
        "{\n"
        '  "ideas": [\n'
        '    { "title": "string", "summary": "2–3 sentence description" },\n'
        "    ... (3 items total)\n"
        "  ]\n"
        "}\n\n"
        f"INPUT:\n{json.dumps(payload, ensure_ascii=False)}"
    )

    resp = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = resp.choices[0].message.content
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"OpenAI returned invalid JSON for story ideas: {e}\nRaw: {raw}")

    ideas_raw = data.get("ideas", [])
    ideas: List[Dict[str, Any]] = []
    for idx, idea in enumerate(ideas_raw, start=1):
        ideas.append(
            {
                "id": f"idea_{idx}",
                "title": idea.get("title", f"Idea {idx}"),
                "summary": idea.get("summary", ""),
            }
        )
    # Ensure exactly 3 items by trimming or padding
    if len(ideas) > 3:
        ideas = ideas[:3]
    while len(ideas) < 3:
        i = len(ideas) + 1
        ideas.append({"id": f"idea_{i}", "title": f"Idea {i}", "summary": ""})

    return ideas

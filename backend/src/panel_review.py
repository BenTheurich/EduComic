"""Structured, opt-in multimodal review for one generated comic panel."""

import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from provider_clients import LazyClient
from provider_config import DEFAULT_OPENAI_MODEL, SUPPORTED_OPENAI_MODELS, require_supported_model
from story_contracts import PanelReview


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
openai_client = LazyClient(lambda: OpenAI(api_key=OPENAI_API_KEY))


def _expected_text_from_panel(panel: Dict[str, Any]) -> List[Dict[str, str]]:
    expected = []
    narration = (panel.get("narration") or "").strip()
    if narration:
        expected.append({"type": "narration", "text": narration})
    for line in panel.get("dialogue") or []:
        text = (line.get("text") or "").strip()
        if text:
            expected.append({"type": "dialogue", "speaker": (line.get("speaker") or "").strip(), "text": text})
    return expected


def review_requires_retry(review: Dict[str, Any]) -> bool:
    """Retry only when a validated, concrete review check says the panel missed."""
    dimensions = PanelReview.model_validate(review).dimensions
    return (
        not dimensions.exact_visible_text
        or dimensions.unexpected_visible_text
        or not dimensions.bubble_ownership
        or not dimensions.reference_identity_continuity
        or not dimensions.requested_action
        or not dimensions.layout_readability
    )


def review_panel_image(
    image_url: str,
    panel: Dict[str, Any],
    classroom: Dict[str, Any],
    students: List[Dict[str, Any]],
    *,
    model: str = DEFAULT_OPENAI_MODEL,
    reference_images: List[Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    """Review a rendered panel against its script and role-labeled references."""
    del classroom, students  # The panel and references are the minimal review context.
    if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE":
        raise RuntimeError("OPENAI_API_KEY not set; cannot run panel review")

    references = reference_images or []
    review_payload = {
        "panel_index": panel.get("index"),
        "expected_setting": (panel.get("setting") or "").strip(),
        "expected_visual_description": (panel.get("description") or "").strip(),
        "expected_text": _expected_text_from_panel(panel),
        "expected_featured_students": panel.get("featured_students") or [],
        "reference_images": [{"role": item["role"]} for item in references],
    }
    system_prompt = (
        "Review one kid-friendly educational comic panel against its script and role-labeled references. "
        "Judge exact expected lettering, unexpected lettering, speech-bubble owner and tail, identity and continuity, "
        "requested action, and readable layout independently. A spelling difference, missing or added word, or wrong "
        "bubble owner fails its check. Use score 0-5 when text or bubble checks fail; otherwise use 0-10. "
        "Give a short, concrete regeneration fix only when needed."
    )
    content = [
        {"type": "text", "text": f"PANEL SPEC:\n{json.dumps(review_payload, ensure_ascii=False)}"},
        {"type": "image_url", "image_url": {"url": image_url}},
    ]
    for reference in references:
        content.extend(
            [
                {"type": "text", "text": f"Reference: {reference['role']}"},
                {"type": "image_url", "image_url": {"url": reference["url"]}},
            ]
        )

    try:
        response = openai_client.chat.completions.parse(
            model=require_supported_model(model, SUPPORTED_OPENAI_MODELS, "OpenAI"),
            response_format=PanelReview,
            max_completion_tokens=2048,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": content}],
        )
    except Exception:
        raise RuntimeError("Panel review request failed") from None

    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("Panel review returned invalid response")
    return parsed.model_dump()

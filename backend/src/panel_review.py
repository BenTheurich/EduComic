"""Structured, opt-in multimodal review for one generated comic panel."""

import base64
import json
import os
from collections import Counter
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from local_runtime import resolve_local_paths
from local_storage import LocalStorage
from provider_clients import LazyClient
from provider_config import DEFAULT_OPENAI_MODEL, SUPPORTED_OPENAI_MODELS, require_supported_model
from story_contracts import PanelReview


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
MAX_REVIEW_REFERENCE_BYTES = 20 * 1024 * 1024
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


def _visible_text_matches(review: PanelReview, panel: Dict[str, Any]) -> bool:
    expected = Counter(item["text"] for item in _expected_text_from_panel(panel))
    observed = Counter(item.text for item in review.visible_text)
    return expected == observed


def _inline_local_reference(url: str) -> str:
    storage = LocalStorage(resolve_local_paths().root)
    try:
        object_path = storage.object_path_from_url(url)
        content_type = storage.content_type(object_path)
        if not content_type.startswith("image/"):
            raise ValueError("reference is not an image")
        image = storage.read_bytes(object_path, max_bytes=MAX_REVIEW_REFERENCE_BYTES)
    except ValueError:
        raise ValueError("Panel review reference must be a validated local image") from None
    encoded = base64.b64encode(image).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def review_requires_retry(review: Dict[str, Any], panel: Dict[str, Any]) -> bool:
    """Retry only when a validated, concrete review check says the panel missed."""
    validated = PanelReview.model_validate(review)
    dimensions = validated.dimensions
    return (
        not _visible_text_matches(validated, panel)
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

    references = [
        {"role": item["role"], "url": _inline_local_reference(item["url"])}
        for item in (reference_images or [])
    ]
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
        "Transcribe every visible text span exactly as rendered before judging anything else, including misspellings "
        "and invented or background lettering. Then judge speech-bubble owner and tail separately from the transcript, "
        "plus identity and continuity, requested action, and readable layout. Use score 0-5 when exact text or bubble "
        "ownership fails; otherwise use 0-10. "
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
    result = parsed.model_dump()
    if (not _visible_text_matches(parsed, panel) or not parsed.dimensions.bubble_ownership) and result["score"] > 5:
        result["score"] = 5
    return result

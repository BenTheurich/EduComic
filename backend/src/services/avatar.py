"""
Avatar generation service using Black Forest Labs API.
"""

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import httpx

from database.database import (
    begin_avatar_work,
    finish_avatar_work,
    finish_superseded_avatar_cleanup,
    get_classrooms_by_student,
    replace_student_avatar,
)
from local_runtime import resolve_local_paths
from local_storage import LocalStorage, media_url
from provider_config import SUPPORTED_BFL_MODELS, require_supported_model


logger = logging.getLogger("educomic.avatar")


class ProviderConfigurationError(RuntimeError):
    """A requested provider capability is not configured locally."""


async def generate_avatar(student_id: str) -> Dict[str, Any]:
    """
    Generate an avatar for a student using Black Forest Labs API.

    Args:
        student_id: The UUID of the student

    Returns:
        Dict containing the student data with updated avatar_url

    Raises:
        ValueError: If the student is not found
        ProviderConfigurationError: If BFL is not configured
        httpx.HTTPError: If API request fails
    """
    api_key = os.getenv("BFL_API_KEY")
    if not api_key or api_key == "YOUR_BFL_API_KEY_HERE":
        raise ProviderConfigurationError("BFL_API_KEY is not configured")
    student, model = begin_avatar_work(student_id)
    try:
        classrooms = get_classrooms_by_student(student_id)
        classroom = classrooms[0] if classrooms else None
        prompt = _build_avatar_prompt(student, classroom)
        bfl_avatar_url = await _call_black_forest_api(prompt, api_key, model=model)
        avatar_url = await _upload_avatar_to_storage(bfl_avatar_url, student_id)
        try:
            updated_student, previous_path = replace_student_avatar(student_id, avatar_url)
        except Exception:
            _delete_media_url(avatar_url, context="avatar update compensation")
            raise
        if updated_student is None:
            _delete_media_url(avatar_url, context="missing student compensation")
            raise ValueError("Student not found")
        if previous_path and _delete_object_path(previous_path, context="superseded avatar cleanup"):
            finish_superseded_avatar_cleanup(student_id, previous_path)
        return updated_student
    finally:
        finish_avatar_work(student_id)


def _delete_media_url(url: str, *, context: str) -> bool:
    try:
        storage = LocalStorage(resolve_local_paths().root)
        storage.delete(storage.object_path_from_url(url))
        return True
    except Exception:
        logger.error("Local media deletion failed context=%s", context)
        return False


def _delete_object_path(object_path: str, *, context: str) -> bool:
    try:
        LocalStorage(resolve_local_paths().root).delete(object_path)
        return True
    except Exception:
        logger.error("Local media deletion failed context=%s", context)
        return False


def _build_avatar_prompt(student: Dict[str, Any], classroom: Optional[Dict[str, Any]] = None) -> str:
    """
    Build a prompt for avatar generation based on student data.

    Args:
        student: Student data dictionary
        classroom: Classroom data dictionary (optional)

    Returns:
        Prompt string for image generation
    """
    interests = student.get("interests", "")

    # Get comic style from classroom, default to manga
    comic_style = classroom.get("design_style", "manga") if classroom else "manga"

    prompt = (
        f"Full-body avatar of a child standing in a relaxed, front-facing pose, "
        f"centered in the frame, single character only. In the style of a {comic_style} classroom comic strip: "
        f"clean line art, flat colors, friendly and age-appropriate. "
        f"Outfit and accessories reflect the child's interests: {interests}. "
        f"Plain white background, simple studio look, soft even lighting."
    )

    return prompt


async def _call_black_forest_api(prompt: str, api_key: str, *, model: str = "flux-2-pro") -> str:
    """
    Call Black Forest Labs API to generate an image.

    Args:
        prompt: Text prompt for image generation
        api_key: Black Forest Labs API key
    Returns:
        URL of the generated image

    Raises:
        httpx.HTTPError: If API request fails
    """
    model = require_supported_model(model, SUPPORTED_BFL_MODELS, "BFL")
    url = f"https://api.bfl.ai/v1/{model}"

    headers = {"accept": "application/json", "x-key": api_key, "Content-Type": "application/json"}

    payload = {"prompt": prompt}

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Submit generation request
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()
        request_id = result.get("id")
        polling_url = result.get("polling_url")

        if not request_id or not polling_url:
            raise ValueError("No request ID or polling URL returned from Black Forest Labs API")

        # Poll for result using the polling URL

        max_attempts = 60

        for attempt in range(max_attempts):
            await asyncio.sleep(2)  # Wait 2 seconds between polls

            result_response = await client.get(polling_url, headers=headers)
            result_response.raise_for_status()

            result_data = result_response.json()
            status = result_data.get("status")

            if status == "Ready":
                generated_image_url = result_data.get("result", {}).get("sample")
                if generated_image_url:
                    return generated_image_url
                raise ValueError("No image URL in completed result")

            elif status == "Error":
                raise ValueError("Image generation failed")

            elif status in ["Pending", "Request Moderated"]:
                # Continue polling
                continue

        raise TimeoutError("Image generation timed out after 120 seconds")


async def _upload_avatar_to_storage(image_url: str, student_id: str) -> str:
    """Download a provider result and atomically persist it as local media."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
        suffixes = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        suffix = suffixes.get(content_type)
        if suffix is None:
            raise ValueError("unsupported avatar media type")
        storage = LocalStorage(resolve_local_paths().root)
        staged = storage.stage_bytes(response.content, suffix, max_bytes=10 * 1024 * 1024)
        object_path = storage.new_object_path("avatars", student_id, suffix)
        storage.finalize(staged, object_path)
        return media_url(object_path)
    except Exception:
        raise RuntimeError("Avatar upload failed") from None

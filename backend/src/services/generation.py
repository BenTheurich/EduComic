"""One-machine durable story generation coordinator."""

import base64
import logging
import os
import struct
import time
import zlib
from uuid import uuid4

import requests

from database import database
from local_runtime import resolve_local_paths
from local_storage import LocalStorage, media_url
from services import comic_creation


logger = logging.getLogger("educomic.generation")
MAX_IMAGE_BYTES = 20 * 1024 * 1024


def _bfl_headers() -> dict[str, str]:
    key = os.getenv("BFL_API_KEY", "").strip()
    if not key or key.startswith("YOUR_"):
        raise RuntimeError("BFL generation is not configured")
    return {"accept": "application/json", "x-key": key}


def submit_bfl_generation(
    prompt: str, aspect_ratio: str = "3:2", reference_images: list[str] | None = None
) -> str:
    width, height = comic_creation._dims_from_aspect(aspect_ratio)
    body = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "output_format": "png",
        "safety_tolerance": 4,
    }
    storage = LocalStorage(resolve_local_paths().root)
    for index, reference in enumerate((reference_images or [])[:8]):
        object_path = storage.object_path_from_url(reference)
        if not storage.content_type(object_path).startswith("image/"):
            raise ValueError("BFL reference must be an image")
        key = "input_image" if index == 0 else f"input_image_{index + 1}"
        body[key] = base64.b64encode(storage.read_bytes(object_path, max_bytes=MAX_IMAGE_BYTES)).decode()

    headers = {**_bfl_headers(), "Content-Type": "application/json"}
    endpoint = os.getenv("BFL_MODEL_ENDPOINT", "flux-2-pro")
    response = requests.post(
        f"https://api.bfl.ai/v1/{endpoint}", headers=headers, json=body, timeout=30
    )
    response.raise_for_status()
    polling_url = response.json().get("polling_url")
    if not polling_url:
        raise RuntimeError("BFL submit response was incomplete")
    return polling_url


def poll_bfl_generation(
    polling_url: str, *, poll_interval: float = 0.75, timeout_seconds: float = 60
) -> str:
    started = time.monotonic()
    while time.monotonic() - started <= timeout_seconds:
        time.sleep(poll_interval)
        response = requests.get(polling_url, headers=_bfl_headers(), timeout=30)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") == "Ready":
            delivery_url = (payload.get("result") or {}).get("sample")
            if not delivery_url:
                raise RuntimeError("BFL result was incomplete")
            return delivery_url
        if payload.get("status") in {"Error", "Failed"}:
            raise RuntimeError("BFL generation failed")
    raise TimeoutError("BFL generation timed out")


def download_bfl_image(delivery_url: str) -> bytes:
    response = requests.get(delivery_url, timeout=30)
    response.raise_for_status()
    content = response.content
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise ValueError("BFL image size is invalid")
    return content


def validate_image_bytes(content: bytes) -> None:
    """Validate and decompress the PNG payload emitted by the current BFL request."""
    if len(content) < 45 or content[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Generated image is not a PNG")
    offset = 8
    image_data = bytearray()
    width = height = None
    saw_end = False
    while offset + 12 <= len(content):
        length = struct.unpack(">I", content[offset : offset + 4])[0]
        chunk_type = content[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(content):
            raise ValueError("Generated PNG is truncated")
        data = content[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", content[offset + 8 + length : end])[0]
        if zlib.crc32(chunk_type + data) & 0xFFFFFFFF != expected_crc:
            raise ValueError("Generated PNG checksum is invalid")
        if chunk_type == b"IHDR":
            if length != 13:
                raise ValueError("Generated PNG header is invalid")
            width, height = struct.unpack(">II", data[:8])
        elif chunk_type == b"IDAT":
            image_data.extend(data)
        elif chunk_type == b"IEND":
            saw_end = True
            break
        offset = end
    if not width or not height or not image_data or not saw_end:
        raise ValueError("Generated PNG structure is incomplete")
    try:
        zlib.decompress(image_data)
    except zlib.error as exc:
        raise ValueError("Generated PNG pixels cannot be decoded") from exc


def _delete_artifacts(storage: LocalStorage, paths: list[str]) -> None:
    for path in dict.fromkeys(paths):
        try:
            if path.startswith("staging/"):
                storage.discard_staged(path)
            else:
                storage.delete(path)
        except Exception:
            logger.error("Generation artifact cleanup failed")


def run_generation(run_id: str) -> None:
    run = database.start_generation_run(run_id)
    if run is None:
        return
    storage = LocalStorage(resolve_local_paths().root)
    artifacts: list[str] = []
    stage = "script"
    try:
        chapter = database.get_chapter(run["chapter_id"])
        if chapter is None:
            raise ValueError("Chapter not found")
        classroom = database.get_classroom(chapter["classroom_id"])
        if classroom is None:
            raise ValueError("Classroom not found")
        ideas = {idea.get("id"): idea for idea in chapter.get("story_ideas") or []}
        chosen = ideas.get(run["selected_idea_id"])
        if chosen is None or chapter.get("chosen_idea_id") != run["selected_idea_id"]:
            raise ValueError("Chosen idea is invalid")
        students = database.get_students_by_classroom(chapter["classroom_id"])
        script = comic_creation.generate_full_script_and_panels(
            classroom=classroom,
            students=students,
            teacher_outline=chapter["original_prompt"],
            chosen_idea=chosen,
        )
        prompts = comic_creation.build_flux_prompts_from_script(classroom, students, script)
        panels_by_index = {panel["index"]: panel for panel in script["panels"]}
        if [prompt["index"] for prompt in prompts] != list(range(1, len(prompts) + 1)):
            raise ValueError("Comic prompt sequence is invalid")

        ready_panels = []
        previous_url = None
        for prompt in prompts:
            panel = panels_by_index[prompt["index"]]
            stage = "submit"
            database.set_generation_stage(run_id, "bfl_submit")
            polling_url = submit_bfl_generation(
                prompt["prompt"], prompt["aspect_ratio"], [previous_url] if previous_url else []
            )
            stage = "poll"
            database.set_generation_stage(run_id, "bfl_poll")
            delivery_url = poll_bfl_generation(polling_url)
            stage = "download"
            database.set_generation_stage(run_id, "bfl_download")
            image = download_bfl_image(delivery_url)
            stage = "validation"
            database.set_generation_stage(run_id, "image_validation")
            validate_image_bytes(image)
            stage = "finalization"
            database.set_generation_stage(run_id, "file_finalization")
            staged = storage.stage_bytes(image, ".png", max_bytes=MAX_IMAGE_BYTES)
            artifacts.append(staged)
            object_path = storage.new_object_path("story-images", chapter["id"], ".png")
            artifacts.append(object_path)
            database.record_generation_artifact(run_id, object_path)
            storage.finalize(staged, object_path)
            artifacts.remove(staged)
            previous_url = media_url(object_path)
            ready_panels.append(
                {
                    **panel,
                    "speakers": [line["speaker"] for line in panel.get("dialogue") or []],
                    "image_object_path": object_path,
                }
            )

        stage = "swap"
        database.set_generation_stage(run_id, "database_swap")
        old_paths = database.finalize_generation_run(run_id, script, ready_panels)
        _delete_artifacts(storage, old_paths)
    except Exception:
        error_codes = {
            "script": "script_invalid",
            "submit": "bfl_submit_failed",
            "poll": "bfl_poll_failed",
            "download": "bfl_download_failed",
            "validation": "image_invalid",
            "finalization": "finalization_failed",
            "swap": "database_swap_failed",
        }
        reference = uuid4().hex
        persisted = database.fail_generation_run(run_id, error_codes[stage], reference)
        _delete_artifacts(storage, [*artifacts, *persisted])
        logger.error(
            "Story generation failed run_id=%s code=%s reference=%s",
            run_id,
            error_codes[stage],
            reference,
        )

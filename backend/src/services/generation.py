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
from panel_review import review_panel_image, review_requires_retry
from provider_config import DEFAULT_BFL_MODEL, SUPPORTED_BFL_MODELS, require_supported_model
from services import comic_creation


logger = logging.getLogger("educomic.generation")
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_PNG_DIMENSION = 4096
MAX_PNG_PIXELS = 16 * 1024 * 1024
MAX_PNG_DECODED_BYTES = 64 * 1024 * 1024


def ordered_panel_references(
    previous_url: str | None, panel: dict, students: list[dict]
) -> list[dict[str, str]]:
    """Keep BFL and reviewer references coherent and deterministic."""
    references = []
    if previous_url:
        references.append({"role": "previous successful panel", "url": previous_url})
    students_by_name = {student.get("name"): student for student in students}
    for name in panel.get("featured_students") or []:
        avatar_url = (students_by_name.get(name) or {}).get("avatar_url")
        if avatar_url and all(item["url"] != avatar_url for item in references):
            references.append({"role": f"current avatar for {name}", "url": avatar_url})
    return references[:8]


def _reference_instructions(references: list[dict[str, str]]) -> str:
    if not references:
        return ""
    return " Reference image order: " + "; ".join(
        f"{index}: {reference['role']}" for index, reference in enumerate(references, 1)
    ) + "."


def build_panel_attempt_prompt(
    base_prompt: str,
    references: list[dict[str, str]],
    correction: str = "",
) -> str:
    prompt = base_prompt + _reference_instructions(references)
    if correction.strip():
        prompt += f" Correction: {correction.strip()}"
    return prompt


def _bfl_headers() -> dict[str, str]:
    key = os.getenv("BFL_API_KEY", "").strip()
    if not key or key.startswith("YOUR_"):
        raise RuntimeError("BFL generation is not configured")
    return {"accept": "application/json", "x-key": key}


def submit_bfl_generation(
    prompt: str,
    aspect_ratio: str = "3:2",
    reference_images: list[str] | None = None,
    *,
    model: str = DEFAULT_BFL_MODEL,
) -> str:
    model = require_supported_model(model, SUPPORTED_BFL_MODELS, "BFL")
    width, height = comic_creation._dims_from_aspect(aspect_ratio)
    body = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "output_format": "png",
        "safety_tolerance": 2,
    }
    storage = LocalStorage(resolve_local_paths().root)
    for index, reference in enumerate((reference_images or [])[:8]):
        object_path = storage.object_path_from_url(reference)
        if not storage.content_type(object_path).startswith("image/"):
            raise ValueError("BFL reference must be an image")
        key = "input_image" if index == 0 else f"input_image_{index + 1}"
        body[key] = base64.b64encode(storage.read_bytes(object_path, max_bytes=MAX_IMAGE_BYTES)).decode()

    headers = {**_bfl_headers(), "Content-Type": "application/json"}
    response = requests.post(
        f"https://api.bfl.ai/v1/{model}", headers=headers, json=body, timeout=30
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
    response = requests.get(delivery_url, timeout=30, stream=True)
    content = bytearray()
    try:
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            remaining = MAX_IMAGE_BYTES + 1 - len(content)
            content.extend(chunk[:remaining])
            if len(content) > MAX_IMAGE_BYTES:
                raise ValueError("BFL image size is invalid")
        if not content:
            raise ValueError("BFL image size is invalid")
        return bytes(content)
    finally:
        response.close()


def validate_image_bytes(content: bytes) -> None:
    """Validate and decompress the PNG payload emitted by the current BFL request."""
    if len(content) < 45 or len(content) > MAX_IMAGE_BYTES or content[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Generated image is not a PNG")
    offset = 8
    decoded = bytearray()
    decompressor = None
    expected_decoded = row_bytes = height = None
    saw_header = saw_data = False
    data_ended = False
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
            if saw_header or offset != 8 or length != 13:
                raise ValueError("Generated PNG header is invalid")
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", data
            )
            channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color_type)
            if (
                not width
                or not height
                or width > MAX_PNG_DIMENSION
                or height > MAX_PNG_DIMENSION
                or width * height > MAX_PNG_PIXELS
                or bit_depth != 8
                or channels is None
                or compression != 0
                or filtering != 0
                or interlace != 0
            ):
                raise ValueError("Generated PNG header is unsupported")
            row_bytes = width * channels
            expected_decoded = height * (row_bytes + 1)
            if expected_decoded > MAX_PNG_DECODED_BYTES:
                raise ValueError("Generated PNG decoded size is too large")
            decompressor = zlib.decompressobj()
            saw_header = True
        elif chunk_type == b"IDAT":
            if not saw_header or data_ended or decompressor is None or expected_decoded is None:
                raise ValueError("Generated PNG chunk order is invalid")
            saw_data = True
            try:
                decoded.extend(
                    decompressor.decompress(data, expected_decoded + 1 - len(decoded))
                )
            except zlib.error as exc:
                raise ValueError("Generated PNG pixels cannot be decoded") from exc
            if len(decoded) > expected_decoded or decompressor.unconsumed_tail:
                raise ValueError("Generated PNG decoded size is invalid")
        elif chunk_type == b"IEND":
            if length != 0 or not saw_data:
                raise ValueError("Generated PNG end chunk is invalid")
            saw_end = True
            offset = end
            break
        elif chunk_type[:1].isupper():
            raise ValueError("Generated PNG contains an unsupported critical chunk")
        elif saw_data:
            data_ended = True
        offset = end
    if (
        not saw_header
        or not saw_end
        or offset != len(content)
        or decompressor is None
        or expected_decoded is None
        or row_bytes is None
        or height is None
    ):
        raise ValueError("Generated PNG structure is incomplete")
    try:
        decoded.extend(decompressor.decompress(b"", expected_decoded + 1 - len(decoded)))
    except zlib.error as exc:
        raise ValueError("Generated PNG pixels cannot be decoded") from exc
    if (
        len(decoded) != expected_decoded
        or not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
    ):
        raise ValueError("Generated PNG decoded size is invalid")
    if any(decoded[row * (row_bytes + 1)] > 4 for row in range(height)):
        raise ValueError("Generated PNG contains an invalid row filter")


def _delete_artifacts(storage: LocalStorage, paths: list[str]) -> list[str]:
    remaining = []
    for path in dict.fromkeys(paths):
        try:
            if path.startswith("staging/"):
                storage.discard_staged(path)
            else:
                storage.delete(path)
        except Exception:
            remaining.append(path)
            logger.error("Generation artifact cleanup failed")
    return remaining


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
        students = database.get_students_by_ids(run["settings_snapshot"]["student_ids"])
        script_args = {
            "classroom": classroom,
            "students": students,
            "teacher_outline": chapter["original_prompt"],
            "chosen_idea": chosen,
            "panel_count": run["settings_snapshot"]["story_length"],
            "model": run["settings_snapshot"]["openai_model"],
        }
        if chapter.get("grounded_sources"):
            script_args["materials"] = chapter["grounded_sources"]
        script = comic_creation.generate_full_script_and_panels(**script_args)
        expected_count = run["settings_snapshot"]["story_length"]
        if len(script["panels"]) != expected_count:
            raise ValueError("Comic script panel count is invalid")
        prompts = comic_creation.build_flux_prompts_from_script(classroom, students, script)
        panels_by_index = {panel["index"]: panel for panel in script["panels"]}
        if [prompt["index"] for prompt in prompts] != list(range(1, len(prompts) + 1)):
            raise ValueError("Comic prompt sequence is invalid")
        if len(prompts) != expected_count:
            raise ValueError("Comic prompt count is invalid")

        ready_panels = []
        previous_url = None
        for prompt in prompts:
            panel = panels_by_index[prompt["index"]]
            references = ordered_panel_references(previous_url, panel, students)
            review_enabled = run["settings_snapshot"]["automatic_panel_review"]
            attempts = run["settings_snapshot"]["panel_review_attempt_cap"] if review_enabled else 1
            candidate_prompt = build_panel_attempt_prompt(prompt["prompt"], references)
            for attempt in range(attempts):
                stage = "submit"
                database.set_generation_stage(run_id, "bfl_submit")
                polling_url = submit_bfl_generation(
                    candidate_prompt,
                    prompt["aspect_ratio"],
                    [reference["url"] for reference in references],
                    model=run["settings_snapshot"]["bfl_model"],
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
                if not review_enabled:
                    break
                review = review_panel_image(
                    delivery_url,
                    panel,
                    classroom,
                    students,
                    model=run["settings_snapshot"]["openai_model"],
                    reference_images=references,
                )
                if not review_requires_retry(review, panel) or attempt == attempts - 1:
                    break
                candidate_prompt = build_panel_attempt_prompt(
                    prompt["prompt"], references, review.get("suggested_fix_prompt", "")
                )
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
        remaining = _delete_artifacts(storage, old_paths)
        database.replace_generation_artifacts(run_id, remaining)
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
        remaining = _delete_artifacts(storage, [*artifacts, *persisted])
        database.replace_generation_artifacts(
            run_id, [path for path in remaining if not path.startswith("staging/")]
        )
        logger.error(
            "Story generation failed run_id=%s code=%s reference=%s",
            run_id,
            error_codes[stage],
            reference,
        )

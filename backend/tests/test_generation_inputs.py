"""Bounded BFL download and strict PNG validation."""

import struct
import zlib

import pytest


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _png(
    width: int = 2,
    height: int = 2,
    *,
    bit_depth: int = 8,
    color_type: int = 6,
    interlace: int = 0,
    filters: list[int] | None = None,
    pixels: bytes | None = None,
    trailing: bytes = b"",
) -> bytes:
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color_type, 4)
    row_bytes = width * channels
    filters = filters or [0] * height
    pixels = pixels if pixels is not None else b"\x00" * (row_bytes * height)
    rows = b"".join(
        bytes([filters[row]]) + pixels[row * row_bytes : (row + 1) * row_bytes]
        for row in range(height)
    )
    ihdr = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, interlace)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(rows))
        + _chunk(b"IEND", b"")
        + trailing
    )


def test_download_stops_after_limit_and_closes_stream(monkeypatch):
    """Catches response buffering or consuming an oversized delivery stream to exhaustion."""
    generation = __import__("services.generation", fromlist=["generation"])

    class FakeResponse:
        closed = False
        produced = 0

        @property
        def content(self):
            raise AssertionError("response.content buffered the delivery")

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            assert chunk_size <= 64 * 1024
            for _ in range(100):
                self.produced += 1
                yield b"x" * (1024 * 1024)

        def close(self):
            self.closed = True

    response = FakeResponse()
    monkeypatch.setattr(
        generation.requests,
        "get",
        lambda _url, **kwargs: response if kwargs.get("stream") is True else pytest.fail("streaming disabled"),
    )

    with pytest.raises(ValueError, match="size is invalid"):
        generation.download_bfl_image("https://delivery.invalid/image.png")

    assert response.produced == 21
    assert response.closed is True


def test_polling_waits_longer_than_one_minute_for_a_queued_bfl_job(monkeypatch):
    """Catches a healthy slow FLUX job being abandoned before it becomes ready."""
    generation = __import__("services.generation", fromlist=["generation"])
    clock = iter(range(200))
    polls = 0

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            nonlocal polls
            polls += 1
            if polls == 81:
                return {"status": "Ready", "result": {"sample": "https://delivery.invalid/panel.png"}}
            return {"status": "Pending"}

    monkeypatch.setattr(generation.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(generation.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(generation.requests, "get", lambda *_args, **_kwargs: FakeResponse())
    monkeypatch.setattr(generation, "_bfl_headers", lambda: {"x-key": "test"})

    assert generation.poll_bfl_generation("https://poll.invalid/job") == "https://delivery.invalid/panel.png"
    assert polls == 81


def test_valid_png_subset_is_fully_decoded():
    generation = __import__("services.generation", fromlist=["generation"])

    generation.validate_image_bytes(_png(filters=[0, 4]))


@pytest.mark.parametrize(
    "content",
    [
        _png(width=100_000, height=1, pixels=b""),
        _png(bit_depth=16),
        _png(color_type=3),
        _png(interlace=1),
        _png(filters=[0, 5]),
        _png(pixels=b"\x00"),
        _png(trailing=b"hidden"),
    ],
)
def test_malformed_or_bomb_png_is_rejected(content):
    """Catches oversized dimensions, unsupported decoding modes, bad rows, and trailing data."""
    generation = __import__("services.generation", fromlist=["generation"])

    with pytest.raises(ValueError, match="Generated PNG"):
        generation.validate_image_bytes(content)

"""Supported localhost-only backend launcher."""

import argparse
import logging
from pathlib import Path

import uvicorn


def validate_bind(host: str, *, allow_unsupported_exposure: bool) -> str:
    if host == "127.0.0.1":
        return host
    if not allow_unsupported_exposure:
        raise ValueError(
            "Non-local bind is unsupported because this private application has no authentication. "
            "Use --allow-unsupported-exposure only if you accept exposing local classroom data."
        )
    logging.warning(
        "UNSUPPORTED EXPOSURE: binding EduComic to %s without authentication",
        host,
    )
    return host


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local/private EduComic backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--allow-unsupported-exposure", action="store_true")
    args = parser.parse_args()
    try:
        host = validate_bind(args.host, allow_unsupported_exposure=args.allow_unsupported_exposure)
    except ValueError as exc:
        parser.error(str(exc))
    uvicorn.run(
        "main:app",
        app_dir=str(Path(__file__).resolve().parent),
        host=host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

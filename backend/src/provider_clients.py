"""Lazy provider clients so offline startup never opens provider transports."""

from collections.abc import Callable
from typing import Any


class LazyClient:
    def __init__(self, factory: Callable[[], Any]):
        self._factory = factory
        self._client: Any | None = None

    def _get(self) -> Any:
        if self._client is None:
            self._client = self._factory()
        return self._client

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)

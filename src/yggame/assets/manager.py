# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Asset caching and development-time hot reload."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar, cast

from yggame.core.errors import AssetError

T = TypeVar("T")


@dataclass(slots=True)
class _Entry(Generic[T]):
    value: T
    modified_ns: int


class AssetManager:
    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], _Entry[Any]] = {}

    def load(self, path: str | Path, loader: Callable[[Path], T], *, kind: str = "default") -> T:
        source = Path(path)
        key = (kind, str(source.resolve()))
        try:
            modified = source.stat().st_mtime_ns
        except OSError as exc:
            raise AssetError(f"asset does not exist or is inaccessible: {source}") from exc
        entry = self._cache.get(key)
        if entry and entry.modified_ns == modified:
            return cast(T, entry.value)
        try:
            value = loader(source)
        except Exception as exc:
            raise AssetError(f"failed to load {source}: {exc}") from exc
        self._cache[key] = _Entry(value, modified)
        return value

    def invalidate(self, path: str | Path | None = None) -> None:
        if path is None:
            self._cache.clear()
            return
        normalized = str(Path(path).resolve())
        for key in [key for key in self._cache if key[1] == normalized]:
            self._cache.pop(key, None)

    def cached(self) -> tuple[str, ...]:
        return tuple(key[1] for key in self._cache)

    def load_text(self, path: str | Path, *, encoding: str = "utf-8") -> str:
        return self.load(path, lambda source: source.read_text(encoding=encoding), kind="text")

    def load_bytes(self, path: str | Path) -> bytes:
        return self.load(path, lambda source: source.read_bytes(), kind="bytes")

    def load_pygame_image(self, path: str | Path, *, convert_alpha: bool = True) -> Any:
        try:
            import pygame  # type: ignore[import-not-found]
        except ImportError as exc:
            raise AssetError("Pygame image loading requires `pip install yggame[pygame]`") from exc

        def loader(source: Path) -> Any:
            image = pygame.image.load(str(source))
            return image.convert_alpha() if convert_alpha else image.convert()

        return self.load(path, loader, kind="pygame.image")


class HotReload:
    def __init__(self, assets: AssetManager) -> None:
        self.assets = assets
        self._known: dict[str, int] = {}

    def watch(self, path: str | Path) -> None:
        source = Path(path).resolve()
        self._known[str(source)] = source.stat().st_mtime_ns

    def poll(self) -> list[str]:
        changed: list[str] = []
        for filename, previous in tuple(self._known.items()):
            source = Path(filename)
            try:
                current = source.stat().st_mtime_ns
            except OSError:
                continue
            if current != previous:
                self._known[filename] = current
                self.assets.invalidate(source)
                changed.append(filename)
        return changed

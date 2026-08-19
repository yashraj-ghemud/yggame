# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Optional Pygame audio services with deterministic bus state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yggame.core.geometry import clamp


@dataclass(slots=True)
class AudioBus:
    name: str
    volume: float = 1.0
    muted: bool = False

    @property
    def effective_volume(self) -> float:
        return 0.0 if self.muted else self.volume

    def set_volume(self, value: float) -> None:
        self.volume = clamp(value, 0.0, 1.0)


class AudioManager:
    """Centralized audio buses; Pygame is loaded only when playback is requested."""

    def __init__(self) -> None:
        self.buses = {name: AudioBus(name) for name in ("master", "music", "sfx", "voice")}
        self._pygame: Any = None
        self._music_track: str | None = None
        self._music_target_volume = 1.0

    def set_volume(self, bus: str, value: float) -> None:
        self.buses[bus].set_volume(value)
        self._apply_music_volume()

    def _require_pygame(self) -> Any:
        if self._pygame is not None:
            return self._pygame
        try:
            import pygame  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("audio requires `pip install yggame[pygame]`") from exc
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        self._pygame = pygame
        return pygame

    def play_music(self, path: str | Path, *, loops: int = -1, fade_ms: int = 0) -> None:
        pygame = self._require_pygame()
        if fade_ms < 0:
            raise ValueError("fade_ms cannot be negative")
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(self._music_volume())
        pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
        self._music_track = str(path)

    def stop_music(self, *, fade_ms: int = 0) -> None:
        if self._pygame:
            self._pygame.mixer.music.fadeout(
                fade_ms
            ) if fade_ms else self._pygame.mixer.music.stop()
        self._music_track = None

    def play_sound(self, sound: Any, *, bus: str = "sfx", volume: float = 1.0) -> Any:
        self._require_pygame()
        if bus not in self.buses:
            raise KeyError(f"unknown audio bus: {bus}")
        channel = sound.play()
        if channel:
            channel.set_volume(
                clamp(volume, 0.0, 1.0)
                * self.buses[bus].effective_volume
                * self.buses["master"].effective_volume
            )
        return channel

    def _music_volume(self) -> float:
        return (
            self.buses["master"].effective_volume
            * self.buses["music"].effective_volume
            * self._music_target_volume
        )

    def _apply_music_volume(self) -> None:
        if self._pygame:
            self._pygame.mixer.music.set_volume(self._music_volume())

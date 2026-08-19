# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Higher-level audio state systems built on AudioManager."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from yggame.core.geometry import Vec2

from .manager import AudioManager


@dataclass(slots=True)
class SoundPool:
    sound: Any
    maximum_instances: int = 8
    active: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.maximum_instances <= 0:
            raise ValueError("sound pool maximum must be positive")

    def play(self, audio: AudioManager, *, bus: str = "sfx", volume: float = 1.0) -> Any:
        self.active[:] = [channel for channel in self.active if channel and channel.get_busy()]
        if len(self.active) >= self.maximum_instances:
            channel = self.active.pop(0)
            if channel:
                channel.stop()
        channel = audio.play_sound(self.sound, bus=bus, volume=volume)
        if channel:
            self.active.append(channel)
        return channel

    def stop_all(self) -> None:
        for channel in self.active:
            if channel:
                channel.stop()
        self.active.clear()


@dataclass(frozen=True, slots=True)
class PlaylistTrack:
    path: str
    weight: float = 1.0
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError("playlist track weight must be positive")


class MusicPlaylist:
    def __init__(self, tracks: Iterable[PlaylistTrack], *, seed: int = 0) -> None:
        self.tracks = tuple(tracks)
        if not self.tracks:
            raise ValueError("music playlist requires tracks")
        self.rng = random.Random(seed)
        self.current: PlaylistTrack | None = None
        self.history: list[str] = []

    def choose(self, *, tags: set[str] | frozenset[str] = frozenset()) -> PlaylistTrack:
        options = [
            track for track in self.tracks if not tags or tags.intersection(track.tags)
        ] or list(self.tracks)
        if len(options) > 1 and self.current:
            options = [track for track in options if track.path != self.current.path] or options
        self.current = self.rng.choices(options, weights=[track.weight for track in options], k=1)[
            0
        ]
        self.history.append(self.current.path)
        self.history = self.history[-16:]
        return self.current

    def play_next(
        self,
        audio: AudioManager,
        *,
        tags: set[str] | frozenset[str] = frozenset(),
        fade_ms: int = 250,
    ) -> PlaylistTrack:
        track = self.choose(tags=tags)
        audio.play_music(track.path, fade_ms=fade_ms)
        return track


@dataclass(frozen=True, slots=True)
class SpatialSound:
    position: Vec2
    sound: Any
    maximum_distance: float = 500.0
    minimum_distance: float = 32.0
    bus: str = "sfx"

    def volume_for(self, listener: Vec2) -> float:
        distance = self.position.distance_to(listener)
        if distance <= self.minimum_distance:
            return 1.0
        if distance >= self.maximum_distance:
            return 0.0
        return 1.0 - (distance - self.minimum_distance) / (
            self.maximum_distance - self.minimum_distance
        )

    def play(self, audio: AudioManager, listener: Vec2) -> Any:
        return audio.play_sound(self.sound, bus=self.bus, volume=self.volume_for(listener))


@dataclass(frozen=True, slots=True)
class AudioSnapshot:
    volumes: dict[str, float]
    muted: frozenset[str]


class AudioState:
    def __init__(self, audio: AudioManager) -> None:
        self.audio = audio

    def capture(self) -> AudioSnapshot:
        return AudioSnapshot(
            {name: bus.volume for name, bus in self.audio.buses.items()},
            frozenset(name for name, bus in self.audio.buses.items() if bus.muted),
        )

    def restore(self, snapshot: AudioSnapshot) -> None:
        for name, value in snapshot.volumes.items():
            if name in self.audio.buses:
                self.audio.set_volume(name, value)
                self.audio.buses[name].muted = name in snapshot.muted

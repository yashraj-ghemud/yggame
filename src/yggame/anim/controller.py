# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Frame animation state machine independent of Pygame surfaces."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AnimationFrame:
    value: Any
    duration: float
    event: str | None = None


@dataclass(slots=True)
class AnimationClip:
    name: str
    frames: tuple[AnimationFrame, ...]
    loop: bool = True

    def __post_init__(self) -> None:
        if not self.frames or any(frame.duration <= 0 for frame in self.frames):
            raise ValueError("animation clips require frames with positive durations")


@dataclass(frozen=True, slots=True)
class TransitionRule:
    source: str
    target: str
    condition: Callable[[dict[str, Any]], bool]


class AnimationController:
    """Stateful animation playback with explicit parameters and callbacks."""

    def __init__(self) -> None:
        self.clips: dict[str, AnimationClip] = {}
        self.transitions: list[TransitionRule] = []
        self.parameters: dict[str, Any] = {}
        self.current: str | None = None
        self.frame_index = 0
        self.frame_elapsed = 0.0
        self._callbacks: list[Callable[[str, Any], None]] = []

    def add_clip(self, clip: AnimationClip) -> None:
        if clip.name in self.clips:
            raise ValueError(f"duplicate animation clip: {clip.name}")
        self.clips[clip.name] = clip
        self.current = self.current or clip.name

    def add_transition(
        self, source: str, target: str, condition: Callable[[dict[str, Any]], bool]
    ) -> None:
        if source not in self.clips or target not in self.clips:
            raise KeyError("animation transition references an unknown clip")
        self.transitions.append(TransitionRule(source, target, condition))

    def on_event(self, callback: Callable[[str, Any], None]) -> None:
        self._callbacks.append(callback)

    @property
    def frame(self) -> AnimationFrame:
        if self.current is None:
            raise RuntimeError("animation controller has no clips")
        return self.clips[self.current].frames[self.frame_index]

    def play(self, name: str, *, restart: bool = False) -> None:
        if name not in self.clips:
            raise KeyError(f"unknown animation clip: {name}")
        if restart or self.current != name:
            self.current = name
            self.frame_index = 0
            self.frame_elapsed = 0.0

    def update(self, delta: float) -> None:
        if self.current is None:
            return
        for rule in self.transitions:
            if rule.source == self.current and rule.condition(self.parameters):
                self.play(rule.target)
                break
        remaining = max(0.0, delta)
        while remaining > 0 and self.current is not None:
            current_frame = self.frame
            until_next = current_frame.duration - self.frame_elapsed
            consumed = min(remaining, until_next)
            self.frame_elapsed += consumed
            remaining -= consumed
            if self.frame_elapsed + 1e-12 < current_frame.duration:
                continue
            if current_frame.event:
                for callback in tuple(self._callbacks):
                    callback(current_frame.event, current_frame.value)
            clip = self.clips[self.current]
            if self.frame_index + 1 < len(clip.frames):
                self.frame_index += 1
                self.frame_elapsed = 0.0
            elif clip.loop:
                self.frame_index = 0
                self.frame_elapsed = 0.0
            else:
                self.frame_elapsed = clip.frames[-1].duration
                remaining = 0.0


__all__ = ["AnimationClip", "AnimationController", "AnimationFrame", "TransitionRule"]

# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Sprite-sheet and atlas data utilities independent of Pygame surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from yggame.assets.pipeline import Atlas
from yggame.core.geometry import Rect, Vec2


@dataclass(frozen=True, slots=True)
class SpriteFrame:
    region: str
    duration: float = 0.1
    pivot: Vec2 = field(default_factory=lambda: Vec2(0.5, 0.5))
    event: str | None = None

    def __post_init__(self) -> None:
        if self.duration <= 0:
            raise ValueError("sprite frame duration must be positive")


@dataclass(frozen=True, slots=True)
class SpriteAnimation:
    name: str
    frames: tuple[SpriteFrame, ...]
    loop: bool = True

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError("sprite animation requires frames")


class SpriteSheet:
    def __init__(self, image: Any, *, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("sprite-sheet dimensions must be positive")
        self.image = image
        self.width, self.height = width, height
        self.regions: dict[str, Rect] = {}

    def slice_grid(self, columns: int, rows: int, *, prefix: str = "frame") -> dict[str, Rect]:
        if columns <= 0 or rows <= 0:
            raise ValueError("sprite-sheet grid dimensions must be positive")
        cell_width, cell_height = self.width / columns, self.height / rows
        for row in range(rows):
            for column in range(columns):
                name = f"{prefix}_{row * columns + column}"
                self.regions[name] = Rect(
                    column * cell_width, row * cell_height, cell_width, cell_height
                )
        return dict(self.regions)

    def add_region(self, name: str, rect: Rect) -> None:
        if name in self.regions:
            raise ValueError(f"duplicate sprite region: {name}")
        if rect.x < 0 or rect.y < 0 or rect.right > self.width or rect.bottom > self.height:
            raise ValueError(f"sprite region outside sheet bounds: {name}")
        self.regions[name] = rect

    def get(self, name: str) -> Rect:
        return self.regions[name]

    @classmethod
    def from_atlas(cls, image: Any, atlas: Atlas, *, width: int, height: int) -> SpriteSheet:
        sheet = cls(image, width=width, height=height)
        for name, region in atlas.regions.items():
            sheet.add_region(name, Rect(region.x, region.y, region.width, region.height))
        return sheet


class AnimationLibrary:
    def __init__(self, sheet: SpriteSheet) -> None:
        self.sheet = sheet
        self.animations: dict[str, SpriteAnimation] = {}

    def add(self, animation: SpriteAnimation) -> None:
        if animation.name in self.animations:
            raise ValueError(f"duplicate sprite animation: {animation.name}")
        for frame in animation.frames:
            if frame.region not in self.sheet.regions:
                raise KeyError(f"animation references unknown sprite region: {frame.region}")
        self.animations[animation.name] = animation

    def get(self, name: str) -> SpriteAnimation:
        return self.animations[name]


class SpriteAnimator:
    def __init__(self, library: AnimationLibrary) -> None:
        self.library = library
        self.current: SpriteAnimation | None = None
        self.index = 0
        self.elapsed = 0.0
        self.events: list[str] = []

    def play(self, name: str, *, restart: bool = False) -> None:
        animation = self.library.get(name)
        if restart or self.current is None or self.current.name != name:
            self.current = animation
            self.index = 0
            self.elapsed = 0.0
            self.events.clear()

    @property
    def frame(self) -> SpriteFrame:
        if self.current is None:
            raise RuntimeError("sprite animator has no current animation")
        return self.current.frames[self.index]

    def update(self, delta: float) -> None:
        if self.current is None:
            return
        self.elapsed += max(0.0, delta)
        while self.elapsed >= self.frame.duration:
            self.elapsed -= self.frame.duration
            if self.frame.event:
                self.events.append(self.frame.event)
            if self.index + 1 < len(self.current.frames):
                self.index += 1
            elif self.current.loop:
                self.index = 0
            else:
                self.elapsed = 0.0
                break

    def consume_events(self) -> tuple[str, ...]:
        events = tuple(self.events)
        self.events.clear()
        return events

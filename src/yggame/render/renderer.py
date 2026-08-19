# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Rendering contracts and a small layered renderer.

Pygame is imported only when a draw operation is requested, allowing render queues
to be built and tested on CI without a display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from yggame.core.geometry import Rect, Vec2


class Renderable(Protocol):
    def draw(self, target: Any, *, interpolation: float = 0.0) -> None: ...


@dataclass(slots=True)
class DrawCommand:
    layer: int
    order: int
    drawable: Renderable
    visible: bool = True
    camera_space: bool = False


class LayeredRenderer:
    """Stable layer/order draw queue with explicit frame boundaries."""

    def __init__(self) -> None:
        self._commands: list[DrawCommand] = []
        self._order = 0

    def begin(self) -> None:
        self._commands.clear()
        self._order = 0

    def submit(
        self,
        drawable: Renderable,
        *,
        layer: int = 0,
        visible: bool = True,
        camera_space: bool = False,
    ) -> DrawCommand:
        command = DrawCommand(layer, self._order, drawable, visible, camera_space)
        self._order += 1
        self._commands.append(command)
        return command

    def draw(self, target: Any, *, interpolation: float = 0.0) -> int:
        count = 0
        for command in sorted(self._commands, key=lambda item: (item.layer, item.order)):
            if command.visible:
                command.drawable.draw(target, interpolation=interpolation)
                count += 1
        return count

    @property
    def commands(self) -> tuple[DrawCommand, ...]:
        return tuple(self._commands)


@dataclass(slots=True)
class Viewport:
    """Maps world coordinates to a target viewport, with optional pixel snapping."""

    rect: Rect
    offset: Vec2 = field(default_factory=Vec2)
    zoom: float = 1.0
    pixel_snap: bool = False

    def __post_init__(self) -> None:
        if self.zoom <= 0:
            raise ValueError("zoom must be positive")

    def world_to_screen(self, point: Vec2) -> Vec2:
        result = Vec2(
            (point.x - self.offset.x) * self.zoom + self.rect.x,
            (point.y - self.offset.y) * self.zoom + self.rect.y,
        )
        return Vec2(round(result.x), round(result.y)) if self.pixel_snap else result

    def screen_to_world(self, point: Vec2) -> Vec2:
        return Vec2(
            (point.x - self.rect.x) / self.zoom + self.offset.x,
            (point.y - self.rect.y) / self.zoom + self.offset.y,
        )

    def world_rect(self) -> Rect:
        return Rect(
            self.offset.x, self.offset.y, self.rect.width / self.zoom, self.rect.height / self.zoom
        )


def require_pygame() -> Any:
    try:
        import pygame  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("Pygame rendering requires `pip install yggame[pygame]`") from exc
    return pygame

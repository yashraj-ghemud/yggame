# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Advanced camera composition helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from math import cos, pi

from yggame.core.geometry import Rect, Vec2, clamp, lerp_vec
from yggame.render.renderer import Viewport


@dataclass(frozen=True, slots=True)
class Deadzone:
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("deadzone dimensions cannot be negative")


class FollowTarget:
    def __init__(self, position: Vec2, *, deadzone: Deadzone | None = None) -> None:
        self.position = position
        self.deadzone = deadzone or Deadzone(0, 0)

    def desired(self, camera_position: Vec2) -> Vec2:
        dx, dy = self.position.x - camera_position.x, self.position.y - camera_position.y
        if abs(dx) <= self.deadzone.width / 2:
            dx = 0
        if abs(dy) <= self.deadzone.height / 2:
            dy = 0
        return camera_position + Vec2(dx, dy)


@dataclass(frozen=True, slots=True)
class Waypoint:
    position: Vec2
    duration: float
    zoom: float | None = None
    hold: float = 0.0

    def __post_init__(self) -> None:
        if self.duration <= 0 or self.hold < 0:
            raise ValueError("waypoint duration must be positive and hold cannot be negative")
        if self.zoom is not None and self.zoom <= 0:
            raise ValueError("waypoint zoom must be positive")


class CutsceneCamera:
    """Interpolates a sequence of waypoints and reports completion once."""

    def __init__(
        self, waypoints: Iterable[Waypoint], *, easing: Callable[[float], float] | None = None
    ) -> None:
        self.waypoints = tuple(waypoints)
        if not self.waypoints:
            raise ValueError("cutscene camera requires at least one waypoint")
        self.easing = easing or ease_in_out
        self.index = 0
        self.elapsed = 0.0
        self.position = self.waypoints[0].position.copy()
        self.zoom = self.waypoints[0].zoom or 1.0
        self.finished = False

    @property
    def current(self) -> Waypoint:
        return self.waypoints[self.index]

    def reset(self) -> None:
        self.index = 0
        self.elapsed = 0.0
        self.position = self.waypoints[0].position.copy()
        self.zoom = self.waypoints[0].zoom or 1.0
        self.finished = False

    def update(self, delta: float) -> bool:
        if self.finished:
            return True
        remaining = max(0.0, delta)
        while remaining > 0 and not self.finished:
            current = self.waypoints[self.index]
            if self.index == 0:
                start_position, start_zoom = current.position, current.zoom or self.zoom
            else:
                previous = self.waypoints[self.index - 1]
                start_position, start_zoom = previous.position, previous.zoom or self.zoom
            total = current.duration + current.hold
            before = self.elapsed
            self.elapsed += remaining
            consumed = min(remaining, total - before)
            remaining -= consumed
            if self.elapsed <= current.duration:
                amount = self.easing(clamp(self.elapsed / current.duration, 0, 1))
                self.position = lerp_vec(start_position, current.position, amount)
                self.zoom = start_zoom + ((current.zoom or start_zoom) - start_zoom) * amount
            else:
                self.position = current.position.copy()
                self.zoom = current.zoom or self.zoom
            if self.elapsed >= total:
                if self.index + 1 >= len(self.waypoints):
                    self.finished = True
                else:
                    self.index += 1
                    self.elapsed = 0.0
        return self.finished


@dataclass(slots=True)
class SplitViewport:
    viewport: Viewport
    player_id: str


class SplitScreen:
    """Computes horizontal or vertical local-multiplayer viewports."""

    def __init__(self, bounds: Rect, *, orientation: str = "horizontal", gap: float = 0.0) -> None:
        if orientation not in {"horizontal", "vertical"}:
            raise ValueError("split orientation must be horizontal or vertical")
        self.bounds = bounds
        self.orientation = orientation
        self.gap = max(0.0, gap)
        self.views: list[SplitViewport] = []

    def configure(self, player_ids: Iterable[str]) -> tuple[SplitViewport, ...]:
        ids = tuple(player_ids)
        if not ids:
            raise ValueError("split screen requires at least one player")
        count = len(ids)
        if self.orientation == "horizontal":
            size = max(0.0, (self.bounds.height - self.gap * (count - 1)) / count)
            rects = [
                Rect(
                    self.bounds.x,
                    self.bounds.y + index * (size + self.gap),
                    self.bounds.width,
                    size,
                )
                for index in range(count)
            ]
        else:
            size = max(0.0, (self.bounds.width - self.gap * (count - 1)) / count)
            rects = [
                Rect(
                    self.bounds.x + index * (size + self.gap),
                    self.bounds.y,
                    size,
                    self.bounds.height,
                )
                for index in range(count)
            ]
        self.views = [
            SplitViewport(Viewport(rect), player_id)
            for rect, player_id in zip(rects, ids, strict=True)
        ]
        return tuple(self.views)


def ease_in_out(value: float) -> float:
    value = clamp(value, 0.0, 1.0)
    return (1 - cos(pi * value)) / 2

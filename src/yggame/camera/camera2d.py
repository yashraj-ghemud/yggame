# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""2D camera primitives independent of a particular renderer."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from yggame.core.geometry import Rect, Vec2, clamp, lerp_vec
from yggame.render.renderer import Viewport


@dataclass(slots=True)
class ScreenShake:
    trauma: float = 0.0
    decay: float = 1.5
    maximum: float = 12.0
    frequency: float = 35.0
    seed: int = 0

    def add(self, amount: float) -> None:
        self.trauma = clamp(self.trauma + max(0.0, amount), 0.0, 1.0)

    def update(self, delta: float) -> None:
        self.trauma = max(0.0, self.trauma - max(0.0, delta) * self.decay)

    def offset(self, time: float) -> Vec2:
        strength = self.maximum * self.trauma * self.trauma
        rng = random.Random(self.seed + int(time * self.frequency))
        return Vec2(rng.uniform(-strength, strength), rng.uniform(-strength, strength))


class Camera2D:
    """Smooth world camera with target following and rectangular world bounds."""

    def __init__(
        self,
        viewport: Rect,
        *,
        position: Vec2 | None = None,
        zoom: float = 1.0,
        smoothing: float = 10.0,
        bounds: Rect | None = None,
    ) -> None:
        self.viewport = Viewport(viewport, position.copy() if position else Vec2(), zoom)
        self.position = position.copy() if position else Vec2()
        self.target: Vec2 | None = None
        self.smoothing = max(0.0, smoothing)
        self.bounds = bounds
        self.shake = ScreenShake()

    @property
    def zoom(self) -> float:
        return self.viewport.zoom

    def set_zoom(self, zoom: float) -> None:
        if zoom <= 0:
            raise ValueError("zoom must be positive")
        self.viewport.zoom = zoom
        self._clamp_position()

    def follow(self, target: Vec2 | None) -> None:
        self.target = target

    def resize(self, viewport: Rect) -> None:
        self.viewport.rect = viewport
        self._clamp_position()

    def update(self, delta: float) -> None:
        if self.target is not None:
            amount = 1.0 if self.smoothing == 0 else 1.0 - math.exp(-self.smoothing * max(0, delta))
            self.position = lerp_vec(self.position, self.target, amount)
        self.shake.update(delta)
        self._clamp_position()
        self.viewport.offset = self.position + self.shake.offset(self.position.x + self.position.y)

    def world_to_screen(self, point: Vec2) -> Vec2:
        return self.viewport.world_to_screen(point)

    def screen_to_world(self, point: Vec2) -> Vec2:
        return self.viewport.screen_to_world(point)

    def _clamp_position(self) -> None:
        if not self.bounds:
            return
        visible = self.viewport.world_rect()
        half_width, half_height = visible.width / 2, visible.height / 2
        min_x = self.bounds.left + half_width
        max_x = self.bounds.right - half_width
        min_y = self.bounds.top + half_height
        max_y = self.bounds.bottom - half_height
        self.position.x = (
            clamp(self.position.x, min_x, max_x) if min_x <= max_x else self.bounds.center.x
        )
        self.position.y = (
            clamp(self.position.y, min_y, max_y) if min_y <= max_y else self.bounds.center.y
        )

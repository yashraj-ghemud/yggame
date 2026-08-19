# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Lightweight deterministic collision helpers for arcade-style games."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from math import floor
from typing import Any

from yggame.core.geometry import Rect, Vec2, clamp, move_toward


@dataclass(slots=True)
class Collider:
    bounds: Rect
    layer: int = 1
    mask: int = -1
    payload: Any = None
    solid: bool = True

    def can_collide_with(self, other: Collider) -> bool:
        return bool(self.mask & other.layer and other.mask & self.layer)


class SpatialHash:
    """Uniform-grid broad phase with duplicate-free query results."""

    def __init__(self, cell_size: float = 64.0) -> None:
        if cell_size <= 0:
            raise ValueError("cell_size must be positive")
        self.cell_size = cell_size
        self._cells: dict[tuple[int, int], set[int]] = {}
        self._items: dict[int, Collider] = {}
        self._keys: dict[int, set[tuple[int, int]]] = {}

    def _cells_for(self, rect: Rect) -> set[tuple[int, int]]:
        left, top = floor(rect.left / self.cell_size), floor(rect.top / self.cell_size)
        right, bottom = (
            floor((rect.right - 1e-9) / self.cell_size),
            floor((rect.bottom - 1e-9) / self.cell_size),
        )
        return {(x, y) for x in range(left, right + 1) for y in range(top, bottom + 1)}

    def insert(self, collider: Collider) -> None:
        key = id(collider)
        self.remove(collider)
        cells = self._cells_for(collider.bounds)
        self._items[key] = collider
        self._keys[key] = cells
        for cell in cells:
            self._cells.setdefault(cell, set()).add(key)

    def remove(self, collider: Collider) -> None:
        key = id(collider)
        for cell in self._keys.pop(key, set()):
            bucket = self._cells.get(cell)
            if bucket:
                bucket.discard(key)
                if not bucket:
                    self._cells.pop(cell, None)
        self._items.pop(key, None)

    def query(self, rect: Rect, *, mask: int = -1) -> list[Collider]:
        keys: set[int] = set()
        for cell in self._cells_for(rect):
            keys.update(self._cells.get(cell, ()))
        return [
            item
            for key in keys
            if (item := self._items[key]).bounds.intersects(rect) and item.layer & mask
        ]

    def clear(self) -> None:
        self._cells.clear()
        self._items.clear()
        self._keys.clear()


@dataclass(frozen=True, slots=True)
class RayHit:
    point: Vec2
    normal: Vec2
    distance: float
    collider: Collider


def raycast(
    origin: Vec2, direction: Vec2, distance: float, colliders: Iterable[Collider]
) -> RayHit | None:
    """Ray-vs-AABB intersection using the slab method."""
    if distance < 0:
        raise ValueError("distance cannot be negative")
    direction = direction.normalized()
    best: RayHit | None = None
    for collider in colliders:
        if not collider.solid:
            continue
        t_min, t_max = 0.0, distance
        normal = Vec2()
        for axis, origin_axis, direction_axis, low, high in (
            ("x", origin.x, direction.x, collider.bounds.left, collider.bounds.right),
            ("y", origin.y, direction.y, collider.bounds.top, collider.bounds.bottom),
        ):
            if abs(direction_axis) < 1e-12:
                if origin_axis < low or origin_axis > high:
                    break
                continue
            near = (low - origin_axis) / direction_axis
            far = (high - origin_axis) / direction_axis
            near_normal = Vec2(-1 if axis == "x" else 0, -1 if axis == "y" else 0)
            if near > far:
                near, far = far, near
                near_normal = -near_normal
            if near > t_min:
                t_min, normal = near, near_normal
            t_max = min(t_max, far)
            if t_min > t_max:
                break
        else:
            if t_min <= distance and (best is None or t_min < best.distance):
                best = RayHit(origin + direction * t_min, normal, t_min, collider)
    return best


class CollisionGrid:
    """Static tile-like collision grid with fast AABB blocking tests."""

    def __init__(self, width: int, height: int, tile_size: float = 32.0) -> None:
        if width <= 0 or height <= 0 or tile_size <= 0:
            raise ValueError("grid dimensions and tile_size must be positive")
        self.width, self.height, self.tile_size = width, height, tile_size
        self._solid = [[False] * width for _ in range(height)]

    def set_solid(self, x: int, y: int, solid: bool = True) -> None:
        self._validate(x, y)
        self._solid[y][x] = solid

    def is_solid(self, x: int, y: int) -> bool:
        return not (0 <= x < self.width and 0 <= y < self.height) or self._solid[y][x]

    def rect_for(self, x: int, y: int) -> Rect:
        self._validate(x, y)
        return Rect(x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size)

    def collides(self, rect: Rect) -> bool:
        left = floor(rect.left / self.tile_size)
        top = floor(rect.top / self.tile_size)
        right = floor((rect.right - 1e-9) / self.tile_size)
        bottom = floor((rect.bottom - 1e-9) / self.tile_size)
        return any(
            self.is_solid(x, y) for x in range(left, right + 1) for y in range(top, bottom + 1)
        )

    def _validate(self, x: int, y: int) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"grid coordinate outside bounds: {(x, y)}")


@dataclass(slots=True)
class PlatformerBody:
    bounds: Rect
    gravity: float = 1500.0
    jump_speed: float = 520.0
    max_fall_speed: float = 1000.0
    move_speed: float = 220.0
    acceleration: float = 1600.0
    friction: float = 1900.0
    coyote_time: float = 0.1
    jump_buffer: float = 0.1
    velocity: Vec2 = field(default_factory=Vec2)
    grounded: bool = False
    _coyote_remaining: float = 0.0
    _jump_buffer_remaining: float = 0.0

    def request_jump(self) -> None:
        self._jump_buffer_remaining = self.jump_buffer

    def update(self, delta: float, horizontal: float, grid: CollisionGrid) -> None:
        horizontal = clamp(horizontal, -1.0, 1.0)
        self._jump_buffer_remaining = max(0.0, self._jump_buffer_remaining - delta)
        self._coyote_remaining = (
            self.coyote_time if self.grounded else max(0.0, self._coyote_remaining - delta)
        )
        target = horizontal * self.move_speed
        rate = self.acceleration if abs(horizontal) > 1e-5 else self.friction
        self.velocity.x = move_toward(self.velocity.x, target, rate * delta)
        if self._jump_buffer_remaining > 0 and self._coyote_remaining > 0:
            self.velocity.y = -self.jump_speed
            self.grounded = False
            self._jump_buffer_remaining = 0.0
            self._coyote_remaining = 0.0
        self.velocity.y = min(self.max_fall_speed, self.velocity.y + self.gravity * delta)
        self._move_axis(delta, "x", grid)
        self.grounded = False
        self._move_axis(delta, "y", grid)

    def _move_axis(self, delta: float, axis: str, grid: CollisionGrid) -> None:
        amount = getattr(self.velocity, axis) * delta
        if not amount:
            return
        candidate = self.bounds.moved(Vec2(amount, 0) if axis == "x" else Vec2(0, amount))
        if not grid.collides(candidate):
            self.bounds = candidate
            return
        steps = max(1, int(abs(amount) / max(1.0, grid.tile_size / 4)))
        step = amount / steps
        for _ in range(steps):
            candidate = self.bounds.moved(Vec2(step, 0) if axis == "x" else Vec2(0, step))
            if grid.collides(candidate):
                if axis == "y" and step > 0:
                    self.grounded = True
                setattr(self.velocity, axis, 0.0)
                break
            self.bounds = candidate


@dataclass(slots=True)
class TopDownBody:
    bounds: Rect
    max_speed: float = 180.0
    acceleration: float = 1000.0
    friction: float = 1200.0
    velocity: Vec2 = field(default_factory=Vec2)

    def update(self, delta: float, input_vector: Vec2, grid: CollisionGrid | None = None) -> None:
        direction = input_vector.clamp_length(1.0)
        target = direction * self.max_speed
        rate = self.acceleration if direction.length_squared else self.friction
        self.velocity.x = move_toward(self.velocity.x, target.x, rate * delta)
        self.velocity.y = move_toward(self.velocity.y, target.y, rate * delta)
        for axis in ("x", "y"):
            amount = getattr(self.velocity, axis) * delta
            candidate = self.bounds.moved(Vec2(amount, 0) if axis == "x" else Vec2(0, amount))
            if grid is None or not grid.collides(candidate):
                self.bounds = candidate
            else:
                setattr(self.velocity, axis, 0.0)
